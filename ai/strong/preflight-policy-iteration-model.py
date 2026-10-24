"""Nontrained synthetic heads exercise both ensemble routes on real positions."""
import importlib.util
from pathlib import Path
import time
import torch
from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest
from model_policy_iteration import PolicyIterationPolicy
from policy_iteration_check import check


def main():
    torch.set_num_threads(1)
    pin = read(ROOT/'ai/strong/strategic-correction-design-v1.json')['parent']
    parent_path = hf_hub_download(pin['repo'], pin['path'], revision=pin['revision'])
    assert digest(parent_path) == pin['sha256']
    parent = torch.load(parent_path, map_location='cpu', weights_only=True)
    assert not parent.get('inference_only')
    spec = importlib.util.spec_from_file_location('new_export', Path(__file__).with_name('export-policy-iteration.py'))
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    out = ROOT/'ai/runs/policy-iteration-model-preflight-v2'
    out.mkdir(exist_ok=False)
    reports = {}
    started = time.monotonic()
    for head_type in ['frozen', 'public']:
        for penalty in [0., 1.]:
            key = head_type + '-' + str(int(penalty))
            torch.manual_seed(304)
            args = {'head_type': head_type, 'heads': 4, 'margin': .025,
                    'parent_margin': .025, 'disagreement_penalty': penalty}
            net = PolicyIterationPolicy(**args).eval()
            net.parent.load_state_dict(parent['state_dict'])
            with torch.no_grad():
                for head in net.heads:
                    head.score[-1].weight.normal_(0, 1.)
            path = out/(key + '.pt')
            torch.save({'architecture': 'policy_iteration_ensemble', 'model_args': args,
                        'feature_revision': '4.3-strategic-correction', 'state_dim': 1217, 'action_dim': 101,
                        'state_dict': net.state_dict(), 'synthetic_untrained': True, 'qualification_eligible': False}, path)
            exporter.export(path, out/key)
            report = check(out/key/'inference64.pt', out/key/'inference64.onnx', ROOT/'ai/runs/policy-iteration-features-v2')
            assert report['changed_eligible'] > 0 and report['cached_changed'] > 0
            report['trainable_parameters_per_head'] = sum(p.numel() for p in net.heads[0].parameters())
            write(out/(key + '-check.json'), report)
            reports[key] = report
            print({'case': key, 'changed': report['changed_eligible'], 'cached_changed': report['cached_changed'],
                   'seconds': time.monotonic() - started}, flush=True)
    result = {'complete': True, 'cases': reports, 'seconds': time.monotonic() - started,
              'gradients': False, 'synthetic_untrained': True, 'qualification_eligible': False,
              'code': {file: digest(ROOT/'ai/strong'/file) for file in ['model_policy_iteration.py',
                  'policy_iteration_check.py', 'export-policy-iteration.py', 'preflight-policy-iteration-model.py']}}
    write(ROOT/'ai/strong/policy-iteration-model-preflight-v2.json', result)


if __name__ == '__main__':
    main()
