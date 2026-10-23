"""Benchmark frozen standalone strategic workers on the target AMD CPU."""
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import time
import numpy as np
import onnxruntime as ort


def main():
    root = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location('probe_helpers', root/'probe-search-transfer-8840u.py')
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    manifest = helpers.read(root/'manifest.json')
    assert helpers.sha(Path(__file__)) == manifest['harness_sha256']
    assert helpers.sha(root/'probe-search-transfer-8840u.py') == manifest['helper_sha256']
    assert helpers.sha(root/'fixtures.jsonl') == manifest['fixtures_sha256']
    cpu = next(x.split(':', 1)[1].strip() for x in Path('/proc/cpuinfo').read_text().splitlines() if x.startswith('model name'))
    assert '8840U' in cpu
    identity = {'hostname': platform.node(), 'processor': cpu, 'python': sys.version,
        'numpy': np.__version__, 'onnxruntime': ort.__version__,
        'node': subprocess.check_output(['node', '--version'], text=True).strip(), 'load_before': os.getloadavg()}
    (root/'machine.json').write_text(json.dumps(identity, indent=2)+'\n')
    fixtures = [json.loads(line) for line in (root/'fixtures.jsonl').open()]
    assert len(fixtures) == 2553
    results = {}
    for key, item in manifest['models'].items():
        archive = root/(key+'.tgz')
        assert helpers.sha(archive) == item['package_sha256']
        package = root/('package-'+key)
        package.mkdir(exist_ok=False)
        with tarfile.open(archive) as bundle:
            bundle.extractall(package, filter='data')
        frozen = helpers.read(package/'manifest.json')
        assert helpers.sha(package/'manifest.json') == item['package_manifest_sha256']
        assert frozen['model_sha256'] == item['pin']['files']['inference64.onnx']
        assert frozen['model_repository_revision'] == item['pin']['revision']
        assert frozen['search_samples'] == 0 and not frozen['geographic_search']
        for name, digest in frozen['files'].items():
            assert helpers.sha(package/name) == digest
        rows = []
        with (root/(key+'.stderr')).open('x') as errors, (root/(key+'.jsonl')).open('x') as output:
            worker = subprocess.Popen([sys.executable, str(package/'serve.py')], cwd='/',
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True, bufsize=1)
            try:
                for index, fixture in enumerate(fixtures):
                    request = fixture['request']; game = request['state']
                    start = time.perf_counter()
                    worker.stdin.write(json.dumps(request)+'\n'); worker.stdin.flush()
                    response = json.loads(worker.stdout.readline())
                    elapsed = (time.perf_counter()-start)*1000
                    helpers.validate(fixture, response, item['pin'])
                    assert response['search'] is None
                    row = {'fixture_index':index, 'players':len(game['players']), 'phase':game['phase'],
                        'rule':game['options']['variant']+('/sealed' if game['options'].get('fastBid') else '/open'),
                        'roundtrip_ms':elapsed, 'response':response}
                    rows.append(row); output.write(json.dumps(row)+'\n')
            finally:
                worker.stdin.close(); worker.wait(timeout=10); worker.stdout.close()
            assert worker.returncode == 0
        results[key] = helpers.summarize(rows)
        print(key, json.dumps(results[key]), flush=True)
    report = {'machine':identity, 'models':results, 'load_after':os.getloadavg(),
        'qualification_eligible':False, 'scope':manifest['scope']}
    (root/'results.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
