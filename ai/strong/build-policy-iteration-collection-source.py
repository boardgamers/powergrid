"""Freeze new state collection without changing historical teacher or engine files."""
import shutil,subprocess,sys,tarfile
from pathlib import Path
from huggingface_hub import HfApi,hf_hub_download
from strategic_collection import ROOT,read,write,digest
NAMES=['capture-policy-iteration.cjs','policy-iteration-bridge.cjs','policy_iteration_collection.py',
    'policy-iteration-collection-protocol-v2.json','test-policy-iteration-capture.cjs','preflight-policy-iteration-collection.py']


def main():
    p=read(ROOT/'ai/strong/policy-iteration-collection-protocol-v2.json');base=p['base_source']
    archive=Path(hf_hub_download('coyotte508/powergrid-ai-training-v1',base['archive'],repo_type='dataset',revision=base['revision']))
    assert digest(archive)==base['sha256'];out=ROOT/'ai/runs/policy-iteration-collection-source-v2';out.mkdir(exist_ok=False)
    with tarfile.open(archive) as bundle:bundle.extractall(out,filter='data')
    before={str(f.relative_to(out)):digest(f) for f in out.rglob('*') if f.is_file()};overlays={}
    for name in NAMES:
        relative='ai/strong/'+name;assert relative not in before
        shutil.copy2(ROOT/relative,out/relative);overlays[relative]=digest(out/relative)
    logs=out/'ai/runs/source-checks';logs.mkdir(parents=True)
    for name,command in [('capture',['node','ai/strong/test-policy-iteration-capture.cjs']),
        ('games',[sys.executable,'-u','ai/strong/preflight-policy-iteration-collection.py'])]:
        print('Checking',name,flush=True)
        with (logs/(name+'.log')).open('w') as f:subprocess.run(command,cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
    capture=read(logs/'capture.log');games=read(out/'ai/runs/policy-iteration-preflight-v2/preflight.json')
    assert capture['passed'] and capture['checks']==5106 and games['passed'] and games['games']==192
    assert all(digest(out/name)==sha for name,sha in before.items())
    assert all(digest(out/name)==sha for name,sha in overlays.items())
    target=ROOT/'ai/runs/strong-source-policy-iteration-collection-20261024-v2.tgz';assert not target.exists()
    with tarfile.open(target,'w:gz') as bundle:
        for name in sorted(set(before)|set(overlays)):bundle.add(out/name,arcname=name,recursive=False)
    commit=HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1',repo_type='dataset',path_or_fileobj=target,path_in_repo=target.name)
    source={'archive':target.name,'revision':commit.oid,'sha256':digest(target),'bytes':target.stat().st_size,
        'base':base,'overlays':overlays,'unchanged_base_files':len(before),
        'protocol_sha256':digest(ROOT/'ai/strong/policy-iteration-collection-protocol-v2.json'),'qualification_eligible':False}
    write(ROOT/'ai/strong/policy-iteration-collection-source-v2.json',source)
    write(ROOT/'ai/strong/policy-iteration-collection-preflight-v2.json',{'passed':True,'source':source,'capture':capture,'games':games,
        'logs':{str(f.relative_to(out)):digest(f) for f in logs.iterdir()},'gradients':False,'qualification_eligible':False})
    print({k:v for k,v in source.items() if k not in ['overlays','base']},flush=True)


if __name__=='__main__':main()
