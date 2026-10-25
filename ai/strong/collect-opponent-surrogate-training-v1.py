"""Recover the original full HF training job and independently verify all seeds."""
import ast
from datetime import datetime, timezone
import fcntl
import importlib.util
import json
from pathlib import Path
import re

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from population_policy_verification import extract_verified
from opponent_surrogate_training_verification_v1 import verify

STRONG = ROOT/'ai/strong'
spec = importlib.util.spec_from_file_location('surrogate_training_launcher', STRONG/'launch-opponent-surrogate-training-v1.py')
launcher = importlib.util.module_from_spec(spec); spec.loader.exec_module(launcher)
OUT = ROOT/'ai/runs/opponent-surrogate-training-full-collected-v1'
RESULT = STRONG/'opponent-surrogate-training-results-v1.json'


def code_hashes(source):
    return {**source['files'], **{str(p.relative_to(ROOT)): digest(p) for p in
        [Path(__file__), STRONG/'opponent_surrogate_training_verification_v1.py', STRONG/'launch-opponent-surrogate-training-v1.py']}}


def save_result(result):
    # The verified receipt is the recovery point. An interrupted index write
    # must not force another audit with a different observation timestamp.
    for path in (OUT/'verified.json', RESULT):
        if path.exists(): assert read(path) == result
    for path in (OUT/'verified.json', RESULT):
        if not path.exists():
            temporary = path.with_suffix('.tmp.json')
            write(temporary, result)
            temporary.replace(path)


def main():
    source, pin, _ = launcher.prerequisites()
    guard_path = launcher.GUARDS/'full.json'; guard = read(guard_path)
    assert guard['stage'] == 'launched' and guard['mode'] == 'full'
    assert guard['source_sha256'] == digest(launcher.SOURCE) and guard['data_pin_sha256'] == digest(launcher.DATA_PIN)
    assert guard['launcher_sha256'] == digest(launcher.__file__)
    assert guard['calibration_verified_sha256'] == digest(launcher.CALIBRATION/'verified.json')
    assert re.fullmatch('[a-f0-9]{24}', guard['job_id'])
    hashes = code_hashes(source)
    api = HfApi(); stage = api.inspect_job(job_id=guard['job_id']).status.stage
    OUT.mkdir(parents=True, exist_ok=True)
    status = {'job_id': guard['job_id'], 'authoritative_status': stage, 'guard_sha256': digest(guard_path),
              'checked_at': datetime.now(timezone.utc).isoformat()}
    write(OUT/'status.json', status)
    if stage != 'COMPLETED': return status
    with (OUT/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (OUT/'verified.json').exists():
            previous = read(OUT/'verified.json')
            assert previous['verified'] and previous['job_id'] == guard['job_id']
            assert previous['guard_sha256'] == digest(guard_path) and previous['code_hashes'] == hashes
            assert previous['source'] == source and previous['data_pin'] == pin
            assert digest(OUT/'artifacts/manifest.json') == previous['evidence']['manifest_sha256']
            assert all(digest(OUT/'artifacts'/name) == sha for name, sha in read(OUT/'artifacts/manifest.json').items())
            assert all(digest(OUT/'local-export-checks'/seed/'parity.json') == r['local_parity_sha256'] for seed, r in previous['seeds'].items())
            save_result(previous)
            return {'job_id': guard['job_id'], 'verified': True, 'reused_existing_verification': True}
        log = '\n'.join(str(x) for x in api.fetch_job_logs(job_id=guard['job_id'], follow=False))
        (OUT/'job.log').write_text(log); receipts = []
        for line in log.splitlines():
            if not line.startswith('{'): continue
            try: row = ast.literal_eval(line)
            except (ValueError, SyntaxError): continue
            if (isinstance(row, dict) and isinstance(row.get('evidence'), dict)
                    and row['evidence'].get('archive_path') == 'archives/opponent-surrogate-training-full-v1.tgz'):
                receipts.append(row)
        assert len(receipts) == 1, 'Missing/ambiguous receipt: inspect the original job, never resubmit'
        receipt = receipts[0]; evidence = receipt['evidence']
        assert evidence['repo'] == 'coyotte508/powergrid-ai-germany-v1' and evidence['remote_archive_verified'] is True
        assert re.fullmatch('[a-f0-9]{40}', evidence['revision'])
        archive = Path(hf_hub_download(evidence['repo'], evidence['archive_path'], revision=evidence['revision']))
        assert digest(archive) == evidence['archive_sha256']
        artifacts = OUT/'artifacts'
        if not artifacts.exists(): extract_verified(archive, artifacts)
        assert digest(artifacts/'manifest.json') == evidence['manifest_sha256']
        assert read(artifacts/'job.json') == receipt['status']
        data_path = ROOT/'ai/runs/opponent-surrogate-training-data-v1'
        if not data_path.exists():
            data_archive = Path(hf_hub_download(pin['repo'], pin['archive_path'], revision=pin['revision']))
            assert digest(data_archive) == pin['archive_sha256']
            recovered = OUT/'recovered-data'
            if not recovered.exists(): extract_verified(data_archive, recovered)
            assert digest(recovered/'manifest.json') == pin['manifest_sha256']
            assert all(digest(recovered/name) == sha for name, sha in read(recovered/'manifest.json').items())
            data_path = recovered/'data'
        review = verify(artifacts, source, pin, data_path, OUT/'local-export-checks')
        assert hashes == code_hashes(source)
        result = {**status, **review, 'source': source, 'data_pin': pin, 'evidence': evidence, 'code_hashes': hashes}
        save_result(result)
        return {'job_id': guard['job_id'], 'verified': True, 'seeds': list(review['seeds']),
                'qualification_eligible': False, 'result_sha256': digest(RESULT)}


if __name__ == '__main__': print(json.dumps(main()))
