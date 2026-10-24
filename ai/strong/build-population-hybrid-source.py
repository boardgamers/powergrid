"""Pin tested research overlays on the unchanged development engine source."""
from pathlib import Path
import shutil
import subprocess
import sys
import os
import tarfile

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest


def main():
    protocol=read(ROOT/'ai/strong/population-hybrid-development-protocol-v1.json')
    preflight=ROOT/'ai/runs/population-policy-preflight-v1'
    admission=read(preflight/'admission.json')
    assert 'pass 4' in (preflight/'tests.log').read_text() and 'fail 0' in (preflight/'tests.log').read_text()
    controls=read(ROOT/'ai/runs/population-policy-arena-controls-v1/assessment.json')
    probe=read(ROOT/'ai/runs/population-policy-trained-probe-v1/assessment.json')
    assert controls['all_controls_identical'] and controls['games']==80 and controls['decisions']==10207
    assert probe['checks_complete'] and probe['positions']==2553 and probe['search_cases']==8 and probe['caps']==0
    assert probe['protocol_sha256']==digest(ROOT/'ai/strong/population-hybrid-development-protocol-v1.json')
    assert all(digest(ROOT/name)==sha for report in [controls,probe] for name,sha in report['code_hashes'].items())
    assert all(digest(ROOT/'ai/strong'/name)==sha for name,sha in admission['new_code_hashes'].items())
    assert digest(ROOT/'ai/strong/final-protocol-multiplayer.json')==protocol['final_protocol_sha256']
    base=protocol['base_source'];repo='coyotte508/powergrid-ai-training-v1'
    archive=Path(hf_hub_download(repo,base['archive'],repo_type='dataset',revision=base['revision']))
    assert digest(archive)==base['sha256']
    failures=read(ROOT/'ai/runs/population-hybrid-runtime-failures-v1/assessment.json')
    assert len(failures['jobs'])==2 and all(r['authoritative_status']=='ERROR' for r in failures['jobs'])
    out=ROOT/'ai/runs/population-hybrid-source-v2-layoutfix';out.mkdir(exist_ok=False)
    with tarfile.open(archive) as bundle:bundle.extractall(out,filter='data')
    before={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}
    assert all(digest(out/name)==sha for name,sha in admission['base_runtime_hashes'].items())
    names=['hybrid_search.py','hybrid-continuations.cjs','population-hybrid-continuations.cjs',
        'endgame-loss-filter.cjs','population-hybrid-policy.cjs','population_hybrid_policy.py',
        'public-arena-bridge.cjs','evaluate-population-policy.py','population-hybrid-runtime-job.py',
        'population-hybrid-development-protocol-v1.json','policy_iteration_evidence_archive.py',
        'test-population-hybrid-policy.cjs','probe-population-policy.py','build-population-hybrid-source.py']
    overlays={}
    for name in names:
        rel='ai/strong/'+name
        if rel in before:
            assert digest(ROOT/rel)==before[rel]
            continue
        shutil.copy2(ROOT/rel,out/rel);overlays[rel]=digest(out/rel)
    assert all(digest(out/name)==sha for name,sha in before.items())
    # Exercise job initialization from the clean package, stopping exactly at
    # the evaluation subprocess. Use the real cached trained model, then retain
    # the expected injected failure receipt; no games/jobs are started here.
    assert not (out/'ai/runs').exists()
    model=ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'
    code="""
import sys,importlib.util,os,json
from pathlib import Path
sys.path.insert(0,str(Path('ai/strong').resolve()))
spec=importlib.util.spec_from_file_location('runtime_job',Path('ai/strong/population-hybrid-runtime-job.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class ReachedEvaluation(Exception):pass
original_popen=module.subprocess.Popen
def stop(*a,**k):
    if a and 'ai/strong/evaluate-population-policy.py' in a[0]:
        raise ReachedEvaluation('intentional package-layout preflight stop')
    return original_popen(*a,**k)
module.subprocess.Popen=stop
module.hf_hub_download=lambda *a,**k:os.environ['PREFLIGHT_MODEL']
module.upload_evidence=lambda directory:{'preflight_only':True}
try:module.main(2)
except ReachedEvaluation:pass
else:raise AssertionError('Did not reach evaluation subprocess')
path=Path('ai/runs/population-hybrid-runtime-v2-2p')
status=json.loads((path/'runtime-check.json').read_text())
assert status['stage']=='failed' and status['error'].startswith('ReachedEvaluation:')
assert (path/'manifest.json').exists()
Path('runtime-layout-check.json').write_text(json.dumps({'clean_package_without_runs':True,'reached_evaluation_subprocess':True,'failure_receipt_written':True,'new_games':0,'new_jobs':0}))
"""
    env={**os.environ,'PREFLIGHT_MODEL':str(model),'PROTOCOL_SHA256':digest(ROOT/'ai/strong/population-hybrid-development-protocol-v1.json'),
         'SOURCE_REVISION':'package-layout-preflight','SOURCE_SHA256':base['sha256']}
    subprocess.run([sys.executable,'-c',code],cwd=out,env=env,check=True)
    layout=read(out/'runtime-layout-check.json');assert layout['reached_evaluation_subprocess']
    assert all(digest(out/name)==sha for name,sha in before.items())
    target=ROOT/'ai/runs/strong-source-population-hybrid-20261024-v2.tgz';assert not target.exists()
    with tarfile.open(target,'w:gz') as bundle:
        for name in sorted(set(before)|set(overlays)):bundle.add(out/name,arcname=name,recursive=False)
    commit=HfApi().upload_file(repo_id=repo,repo_type='dataset',path_or_fileobj=target,path_in_repo=target.name)
    assert digest(hf_hub_download(repo,target.name,repo_type='dataset',revision=commit.oid))==digest(target)
    source={'archive':target.name,'revision':commit.oid,'sha256':digest(target),'bytes':target.stat().st_size,
        'base':base,'unchanged_base_files':len(before),'overlays':overlays,
        'protocol_sha256':digest(ROOT/'ai/strong/population-hybrid-development-protocol-v1.json'),
        'controls_sha256':digest(ROOT/'ai/runs/population-policy-arena-controls-v1/assessment.json'),
        'probe_sha256':digest(ROOT/'ai/runs/population-policy-trained-probe-v1/assessment.json'),
        'preflight_sha256':digest(preflight/'admission.json'),'layout_check':layout,
        'layout_check_sha256':digest(out/'runtime-layout-check.json'),
        'prior_layout_harness_failure_sha256':digest(ROOT/'ai/runs/build-population-hybrid-source-v2.log'),
        'replaces_source':read(ROOT/'ai/strong/population-hybrid-source-v1.json'),
        'repair':'Create the absent ai/runs parent in a clean extracted job package; output receipt path uses v2. Policy, model, samples, seeds, engine and horizons unchanged.',
        'gradients':False,'qualification_eligible':False}
    write(ROOT/'ai/strong/population-hybrid-source-v2.json',source)
    print({k:source[k] for k in ['archive','revision','sha256','unchanged_base_files']},flush=True)


if __name__=='__main__':main()
