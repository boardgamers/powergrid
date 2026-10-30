"""Archive the three completed original mini-PC shards without rerunning games."""
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download
from policy_iteration_evidence_archive import upload_evidence
from run_nomination_minipc_v1 import read, save, digest, now

ROOT = Path(__file__).resolve().parents[2]
STRONG = ROOT/'ai/strong'
LOCAL = ROOT/'ai/runs/nomination-discount-minipc-batch-v1'
OUT = STRONG/'nomination-discount-minipc-batch-results-v1.json'
REPO = 'coyotte508/powergrid-ai-germany-v1'


def main():
    assert not OUT.exists(), 'Preserve completed aggregate'
    state = read(LOCAL/'last-status.json'); collection = read(LOCAL/'collection.json')
    assert state['stage'] == 'completed' and not state['supervisor_alive']
    assert collection['games'] == 96 and len(collection['audits']) == 3
    assert set(state['completed_shards']) == {r['name'] for r in collection['audits']}
    api = HfApi(); assert api.model_info(REPO).private
    records = []; ledger = LOCAL/'raw-archives'; ledger.mkdir(exist_ok=True)
    for item in collection['audits']:
        name = item['name']; raw = LOCAL/'collected'/name; audit_path = LOCAL/(name+'.audit.json')
        assert digest(audit_path) == item['audit_sha256']
        audit = read(audit_path)
        assert audit['independently_audited'] and audit['caps'] == 0 and audit['games'] == 32
        assert audit['auditor_sha256'] == digest(STRONG/'audit_nomination_development_v1.py')
        assert audit['raw_manifest_sha256'] == digest(raw/'manifest.json')
        descriptor = ledger/(name+'.json'); remote = 'archives/'+name+'.tgz'
        if descriptor.exists():
            result = read(descriptor)
            assert result['manifest_sha256'] == audit['raw_manifest_sha256'] and result['remote_archive_verified']
            assert digest(hf_hub_download(REPO, remote, revision=result['revision'])) == result['archive_sha256']
        else:
            assert not api.file_exists(REPO, remote), 'Inspect original remote upload outcome before retry'
            save(ledger/(name+'.intent.json'), {'created_at': now(), 'repo': REPO, 'archive': remote,
                'audit_sha256': digest(audit_path), 'raw_manifest_sha256': audit['raw_manifest_sha256']})
            result = upload_evidence(raw, REPO); save(descriptor, result)
        records.append({'name': name, 'games': 32, 'seconds': audit['seconds'],
            'audit_sha256': digest(audit_path), 'raw_manifest_sha256': audit['raw_manifest_sha256'], 'archive': result})
        print({'name': name, 'archived': True, 'revision': result['revision']}, flush=True)
    save(OUT, {'created_at': now(), 'complete': True, 'games': 96, 'independently_audited': True,
        'jobs': records, 'batch_seconds': state['seconds'], 'finished_at': state['finished_at'],
        'protocol_sha256': digest(STRONG/'nomination-discount-development-protocol-v1.json'),
        'comparison_sha256': digest(STRONG/'nomination-discount-two-player-results-v1.json'),
        'archiver_sha256': digest(__file__), 'qualified': False, 'reserved_final_seeds_used': False})


if __name__ == '__main__': main()
