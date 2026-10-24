"""Launch one guarded, nontraining architecture benchmark on the user's target."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from strategic_collection import ROOT, read, write, digest


def main():
    prepared = ROOT/'ai/runs/policy-iteration-8840u-prepared-v2'
    manifest = read(prepared/'manifest.json')
    assert manifest['synthetic_untrained'] and not manifest['gradients'] and not manifest['qualification_eligible']
    guard_path = ROOT/'ai/strong/policy-iteration-8840u-launch-v2.json'
    assert not guard_path.exists(), 'Inspect the recorded process before retrying'
    for key, item in manifest['models'].items():
        assert digest(prepared/(key+'.tgz')) == item['package_sha256']
        package = prepared/('local-package-'+key)
        package.mkdir()
        with tarfile.open(prepared/(key+'.tgz')) as bundle:
            bundle.extractall(package, filter='data')
        with (prepared/(key+'-local-check.log')).open('w') as log:
            subprocess.run([sys.executable, str(ROOT/'ai/strong/verify-package.py'), str(package), str(prepared/'fixtures.jsonl'),
                            '--output', str(prepared/(key+'-local-check.json'))], cwd='/', stdout=log, stderr=subprocess.STDOUT, check=True)
        check = read(prepared/(key+'-local-check.json'))
        assert check['all_hashes_match'] and check['all_moves_legal'] and check['player_counts'] == [2,3,4,5,6]
    remote = '/home/coyotte508/powergrid-ai-policy-iteration-architecture-v2'
    record = {'host': 'minipc', 'directory': remote, 'stage': 'launch_intent',
              'created_at': datetime.now(timezone.utc).isoformat(), 'manifest_sha256': digest(prepared/'manifest.json'),
              'synthetic_untrained': True, 'gradients': False, 'qualification_eligible': False}
    with guard_path.open('x') as stream:
        json.dump(record, stream, indent=2)
    try:
        subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', 'minipc', 'mkdir '+remote], check=True)
        files = [prepared/'manifest.json', prepared/'probe-strategic-packages-8840u.py', prepared/'probe-search-transfer-8840u.py']
        files += [prepared/(key+'.tgz') for key in manifest['models']]
        subprocess.run(['scp', '-q', *map(str, files), 'minipc:'+remote+'/'], check=True)
        # Existing fixed fixtures are reused only after their bytes match the new manifest.
        script = f'''from pathlib import Path
import hashlib,shutil
source=Path('/home/coyotte508/powergrid-ai-strategic-packages-v1/fixtures.jsonl')
assert hashlib.sha256(source.read_bytes()).hexdigest()=={manifest['fixtures_sha256']!r}
shutil.copy2(source,Path({remote!r})/'fixtures.jsonl')
'''
        subprocess.run(['ssh', '-o', 'BatchMode=yes', 'minipc', 'python3 -'], input=script, text=True, check=True)
        record['stage'] = 'running'
        write(guard_path, record)
        command = f"cd {remote}\necho $$ > process.pid\nexec /home/coyotte508/powergrid-ai-baseline/.venv/bin/python -u probe-strategic-packages-8840u.py > run.log 2>&1"
        result = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'minipc', command])
        record.update(stage='completed' if result.returncode == 0 else 'observation_or_process_error', returncode=result.returncode)
        result.check_returncode()
    except BaseException as error:
        if record['stage'] != 'observation_or_process_error':
            record['stage'] = 'launch_or_observation_unknown'
        record['error'] = type(error).__name__+': '+str(error)
        raise
    finally:
        write(guard_path, record)
    print({'completed': True, 'host': 'minipc', 'synthetic_untrained': True, 'requests': 10212}, flush=True)


if __name__ == '__main__':
    main()
