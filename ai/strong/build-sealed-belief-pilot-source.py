"""Freeze the new belief teacher only after controls pass in the frozen runtime."""
import shutil,subprocess,sys,tarfile
from pathlib import Path
from huggingface_hub import HfApi,hf_hub_download
from strategic_collection import ROOT,read,write,digest

NAMES=['sealed-policy-beliefs.cjs','sealed-belief-continuations.cjs','sealed_belief_teacher.py',
    'sealed_belief_pilot.py','test-sealed-policy-beliefs.cjs','preflight-sealed-belief-teacher.py',
    'check-sealed-belief-reference.py','sealed-belief-pilot-protocol-v1.json']


def main():
    base=read(ROOT/'ai/strong/strategic-correction-source-v1.json')
    p=read(ROOT/'ai/strong/sealed-belief-pilot-protocol-v1.json')
    assert p['source_base']=={k:base[k] for k in ['archive','revision','sha256']}
    out=ROOT/'ai/runs/sealed-belief-source-v1';out.mkdir(exist_ok=False)
    archive=Path(hf_hub_download('coyotte508/powergrid-ai-training-v1',base['archive'],revision=base['revision'],repo_type='dataset'))
    assert digest(archive)==base['sha256']
    with tarfile.open(archive) as bundle:bundle.extractall(out,filter='data')
    before={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}
    overlays={}
    for name in NAMES:
        relative='ai/strong/'+name;assert relative not in before
        shutil.copy2(ROOT/relative,out/relative);overlays[relative]=digest(out/relative)
    logs=out/'ai/runs/source-checks';logs.mkdir(parents=True)
    commands=[['node','--test','ai/strong/test-sealed-policy-beliefs.cjs'],
        [sys.executable,'-u','ai/strong/preflight-sealed-belief-teacher.py'],
        [sys.executable,'ai/strong/check-sealed-belief-reference.py']]
    for i,command in enumerate(commands):
        print('Checking',command[1:],flush=True)
        with (logs/f'{i}.log').open('w') as f:subprocess.run(command,cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
    check=read(out/'ai/runs/sealed-belief-preflight-v1/preflight.json')
    reference=read(out/'ai/runs/sealed-belief-preflight-v1/reference-check.json')
    assert check['passed'] and check['rollouts']==192 and reference['passed']
    assert all(digest(out/name)==sha for name,sha in before.items())
    assert all(digest(out/name)==sha for name,sha in overlays.items())
    target=ROOT/'ai/runs/strong-source-sealed-belief-pilot-20261024-v1.tgz';assert not target.exists()
    with tarfile.open(target,'w:gz') as bundle:
        for name in sorted(set(before)|set(overlays)):bundle.add(out/name,arcname=name,recursive=False)
    commit=HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1',repo_type='dataset',path_or_fileobj=target,path_in_repo=target.name)
    source={'archive':target.name,'revision':commit.oid,'sha256':digest(target),'bytes':target.stat().st_size,
        'base':p['source_base'],'overlays':overlays,'unchanged_base_files':len(before),
        'protocol_sha256':digest(ROOT/'ai/strong/sealed-belief-pilot-protocol-v1.json'),'qualification_eligible':False}
    write(ROOT/'ai/strong/sealed-belief-pilot-source-v1.json',source)
    write(ROOT/'ai/strong/sealed-belief-pilot-preflight-v1.json',{'passed':True,'source':source,'controls':check,
        'archived_reference':reference,'logs':{str(p.relative_to(out)):digest(p) for p in logs.iterdir()},
        'gradients':False,'qualification_eligible':False})
    print({k:v for k,v in source.items() if k not in ['base','overlays']},flush=True)


if __name__=='__main__':main()
