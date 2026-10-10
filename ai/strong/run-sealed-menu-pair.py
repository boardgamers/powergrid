"""Run both fixed conditions on the same HF CPU host, upload evidence on failure too."""
import json
from pathlib import Path
import subprocess
import sys
from huggingface_hub import HfApi
from five_plant_screen import ROOT, REPO, read, write, digest

out = ROOT / 'ai/runs/sealed-menu-pair-v1'
out.mkdir(parents=True, exist_ok=True)
protocol = read(ROOT / 'ai/strong/sealed-menu-protocol-v1.json')
report = {'status': 'running', 'protocol_sha256': digest(ROOT / 'ai/strong/sealed-menu-protocol-v1.json'),
          'qualification_eligible': False, 'trained': False, 'completed_conditions': []}
try:
    for key in protocol['execution']['conditions_order']:
        subprocess.run([sys.executable, '-u', 'ai/strong/sealed_menu_screen.py', key,
                        str(ROOT / 'ai/runs' / ('sealed-menu-screen-v1-' + key)), '--upload'], cwd=ROOT, check=True)
        report['completed_conditions'].append(key)
    subprocess.run([sys.executable, 'ai/strong/compare-sealed-menu-screens.py',
        str(ROOT / 'ai/runs/sealed-menu-screen-v1-control'), str(ROOT / 'ai/runs/sealed-menu-screen-v1-expanded'),
        '--output', str(out / 'comparison.json')], cwd=ROOT, check=True)
    report.update(status='complete', games=15040, exact_open_games=3760)
except BaseException as error:
    report.update(status='failed', error=type(error).__name__ + ': ' + str(error))
    raise
finally:
    report['artifact_sha256'] = {p.name: digest(p) for p in out.iterdir() if p.is_file() and p.name != 'pair-check.json'}
    write(out / 'pair-check.json', report)
    HfApi().upload_folder(repo_id=REPO, folder_path=out, path_in_repo='runs/sealed-menu-pair-v1')
    print(json.dumps(report), flush=True)
