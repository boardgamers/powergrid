"""One bounded collection pass over original development jobs; never submits."""
import argparse
from datetime import datetime, timezone
import json
import subprocess
import sys
from huggingface_hub import HfApi
from checkpoint_bucket_archives_v3 import checked_receipt, download_archive
from current_auction_resource_job_v2 import tree
from prepare_nomination_development_v1 import ROOT, OUT as PREP, PROTOCOL
from prepare_auction_discount_teacher_v2 import read, save, digest

OUT = ROOT/'ai/runs/nomination-discount-development-collected-v1'
LAUNCH = ROOT/'ai/strong/nomination-discount-development-launch-v1.json'


def main():
    p = argparse.ArgumentParser(__doc__); p.add_argument('--collect', action='store_true'); a = p.parse_args()
    launch = read(LAUNCH); protocol = read(PROTOCOL); assert launch['protocol_sha256'] == digest(PROTOCOL)
    OUT.mkdir(exist_ok=True); api = HfApi(); statuses = []; audits = []
    for job in launch['jobs']:
        name = job['name']; folder = OUT/name; folder.mkdir(exist_ok=True)
        stage = api.inspect_job(job_id=job['job_id']).status.stage
        row = {'name': name, 'job_id': job['job_id'], 'stage': stage}; statuses.append(row)
        print(row, flush=True)
        if not a.collect or stage in ('SCHEDULING', 'STARTING', 'RUNNING', 'QUEUED'): continue
        final_log = folder/'final.log'
        log = final_log.read_text() if final_log.exists() else '\n'.join(api.fetch_job_logs(job_id=job['job_id'], follow=False))
        if not final_log.exists(): (folder/'observed.log').write_text(log)
        receipts = []
        for line in log.splitlines():
            try: value = json.loads(line)
            except json.JSONDecodeError: continue
            if isinstance(value, dict) and 'development_evidence' in value: receipts.append(value)
        if len(receipts) != 1 or receipts[0]['name'] != name:
            save(folder/'collection-failure.json', {'stage': stage, 'reason': 'Missing or ambiguous final receipt', 'job_id': job['job_id']})
            raise ValueError('Inspect original log/retained data; no automatic game retry: '+name)
        if not final_log.exists():
            with final_log.open('x') as f: f.write(log)
        receipt = receipts[0]['development_evidence']; checked_receipt(receipt, name)
        if (folder/'receipt.json').exists(): assert read(folder/'receipt.json') == receipt
        else: save(folder/'receipt.json', receipt)
        raw = folder/'raw'
        if raw.exists(): tree(raw, 'manifest.json', receipt['manifest_sha256'])
        else: download_archive(receipt, name, raw, api)
        assert stage == 'COMPLETED' and receipts[0]['returncode'] == 0, 'Failed original retained; inspect without rerun'
        report_path = folder/'audit.json'
        if not report_path.exists():
            subprocess.run([sys.executable, '-B', str(ROOT/'ai/strong/audit_nomination_development_v1.py'),
                '--artifact', str(PREP/'artifact'), '--bundle', str(PREP/'bundle'), '--raw', str(raw),
                '--name', name, '--output', str(report_path)], check=True)
        report = read(report_path)
        assert report['auditor_sha256'] == digest(ROOT/'ai/strong/audit_nomination_development_v1.py')
        assert report['raw_manifest_sha256'] == receipt['manifest_sha256'] and report['row'] == job['row']
        assert report['protocol_sha256'] == digest(PROTOCOL) and report['independently_audited'] and report['caps'] == 0
        audits.append({'name': name, 'job_id': job['job_id'], 'games': report['games'], 'audit_sha256': digest(report_path), 'receipt': receipt})
    state = {'checked_at': datetime.now(timezone.utc).isoformat(), 'protocol_sha256': digest(PROTOCOL),
             'jobs': statuses, 'audits': audits, 'independently_audited_games': sum(r['games'] for r in audits),
             'complete': len(audits) == protocol['jobs'], 'qualified': False, 'reserved_final_seeds_used': False}
    temp = OUT/'state.tmp'; temp.write_text(json.dumps(state, indent=2)+'\n'); temp.replace(OUT/'state.json')
    print({'audited_games': state['independently_audited_games'], 'complete': state['complete']}, flush=True)


if __name__ == '__main__': main()
