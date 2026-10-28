"""Compare saved public decisions with a separately built current engine.

No mutation of research/runtime sources, no inference, new games or HF jobs.
Only the preselected archived 33-game request corpus and bounded setup fixtures.
"""
import argparse
import base64
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request

from public_policy_development_job_v1 import digest,read

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'ai/runs/current-engine-compatibility-v1'
COMMIT='3adad0cc0d1d31352aa7a9059bd15efa79647269'
TS_URL='https://registry.npmjs.org/typescript/-/typescript-4.3.5.tgz'
TS_INTEGRITY='DqQgihaQ9cUrskJo9kIyW/+g0Vxsk8cDtZ52a3NGh0YNTfpUSArXSohyUGnvbPazEPLu398C0UxmKSOrPumUzA=='
ARTIFACT=ROOT/'ai/runs/resource-turn-full-artifact-v4'
RECORDED=ROOT/'ai/runs/resource-turn-full-integration-v2'
RESULT=ROOT/'ai/strong/current-engine-compatibility-results-v1.json'


def save(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def prepare():
    assert not OUT.exists() and not RESULT.exists(),'Inspect previous compatibility work before retrying'
    evidence=read(ROOT/'ai/strong/resource-turn-full-integration-evidence-v2.json')
    previous=RECORDED/'assessment.json'
    assert digest(previous)==evidence['assessment_sha256'] and read(previous)['passed']
    prior=read(previous);requests=sorted(RECORDED.glob('model-turn-*/decisions-*.jsonl'))
    assert len(requests)==33
    input_pins={str(p.relative_to(ROOT)):digest(p) for p in requests}
    assert all(sha==prior['output_hashes'][str((ROOT/name).relative_to(RECORDED))] for name,sha in input_pins.items())
    manifest=read(ARTIFACT/'manifest.json')
    assert all(digest(ARTIFACT/n)==sha for n,sha in manifest.items())
    assert digest(ARTIFACT/'manifest.json')=='ce05c01a314305f5f0b3f7b55f6a8e13355ee0edb9bf5cae2c9688efd55cf795'
    commit=subprocess.check_output(['git','rev-parse',COMMIT+'^{commit}'],cwd=ROOT,text=True).strip()
    assert commit==COMMIT
    OUT.mkdir();source=OUT/'source';source.mkdir()
    raw=subprocess.check_output(['git','archive',COMMIT,'engine'],cwd=ROOT)
    (OUT/'engine-source.tar').write_bytes(raw)
    with tarfile.open(fileobj=io.BytesIO(raw)) as bundle:bundle.extractall(source,filter='data')
    assert read(source/'engine/package.json')['version']=='2.0.19'
    source_pins={str(p.relative_to(source)):digest(p) for p in source.rglob('*') if p.is_file()}
    # Pin the same TypeScript release as this repository's lockfile. No package
    # installation or code in the user's separate live checkout is used.
    raw=urllib.request.urlopen(TS_URL,timeout=60).read()
    assert base64.b64encode(hashlib.sha512(raw).digest()).decode()==TS_INTEGRITY
    (OUT/'typescript-4.3.5.tgz').write_bytes(raw)
    compiler=OUT/'compiler';compiler.mkdir()
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as bundle:bundle.extractall(compiler,filter='data')
    save(OUT/'design.json',{'created_at':datetime.now(timezone.utc).isoformat(),'current_engine_commit':COMMIT,
        'current_engine_version':'2.0.19','source_archive_sha256':digest(OUT/'engine-source.tar'),
        'source_files':source_pins,'typescript_url':TS_URL,'typescript_sha512':TS_INTEGRITY,
        'typescript_sha256':digest(OUT/'typescript-4.3.5.tgz'),'frozen_artifact_manifest_sha256':digest(ARTIFACT/'manifest.json'),
        'frozen_engine_sha256':digest(ARTIFACT/'runtime/engine/dist/src/engine.js'),
        'frozen_available_moves_sha256':digest(ARTIFACT/'runtime/engine/dist/src/available-moves.js'),
        'recorded_evidence':evidence['archive'],'recorded_assessment_sha256':digest(previous),'recorded_inputs':input_pins,
        'selection':'All 33 prior full-game integration replays: 2–6 players, all rules, economic opponents, plus 2/6-player legacy; unchanged predetermined corpus.',
        'python_checker_sha256':digest(__file__),'node_checker_sha256':digest(Path(__file__).with_suffix('.cjs')),
        'scope':'engine-compatibility-only','new_hf_jobs':0,'new_inference':0,'new_full_games':0,
        'qualification_eligible':False,'reserved_final_seeds_used':False})
    script=OUT/'compile.cjs'
    script.write_text("""const fs=require('node:fs'),path=require('node:path');
const root=process.argv[2],ts=require(path.join(root,'compiler/package/lib/typescript.js'));
if(ts.version!=='4.3.5')throw Error('Wrong compiler');
const source=path.join(root,'source/engine'),dist=path.join(source,'dist');
fs.mkdirSync(dist);
let compiled=0;
function walk(directory){for(const entry of fs.readdirSync(directory,{withFileTypes:true})){
 const file=path.join(directory,entry.name);if(entry.isDirectory()){if(entry.name!=='dist')walk(file);continue;}
 const relative=path.relative(source,file);if(!file.endsWith('.ts')||file.endsWith('.spec.ts'))continue;
 const result=ts.transpileModule(fs.readFileSync(file,'utf8'),{fileName:file,reportDiagnostics:true,
  compilerOptions:{target:ts.ScriptTarget.ES2018,module:ts.ModuleKind.CommonJS,esModuleInterop:true}});
 if(result.diagnostics.some(d=>d.category===ts.DiagnosticCategory.Error))throw Error(JSON.stringify(result.diagnostics));
 const target=path.join(dist,relative.replace(/\\.ts$/,'.js'));fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,result.outputText);compiled++;
}}
walk(source);console.log(JSON.stringify({compiler:ts.version,compiled,typecheck:false}));
""")
    with (OUT/'compile.log').open('x') as log:
        subprocess.run(['node',str(script),str(OUT)],cwd='/tmp',stdout=log,stderr=subprocess.STDOUT,check=True)
    # Exact, already frozen runtime dependencies. This symlink is not archived;
    # recovery resolves it through the separately pinned artifact manifest.
    (source/'engine/node_modules').symlink_to(ARTIFACT/'runtime/engine/node_modules',target_is_directory=True)
    save(OUT/'build.json',{'design_sha256':digest(OUT/'design.json'),'compile_script_sha256':digest(script),
        'node_version':subprocess.check_output(['node','--version'],text=True).strip(),
        'node_binary_sha256':digest(shutil.which('node')),
        'compiled_files':{str(p.relative_to(source/'engine')):digest(p)
            for p in (source/'engine/dist').rglob('*') if p.is_file()},'typecheck':False})
    print(json.dumps({'prepared':True,'current_engine_commit':COMMIT,'recorded_games':33}),flush=True)


def check():
    design=read(OUT/'design.json');build=read(OUT/'build.json')
    assert not (OUT/'check-intent.json').exists() and not RESULT.exists(),'Inspect previous diagnostic before retrying'
    assert digest(__file__)==design['python_checker_sha256']
    worker=Path(__file__).with_suffix('.cjs');assert digest(worker)==design['node_checker_sha256']
    assert digest(OUT/'design.json')==build['design_sha256']
    assert all(digest(ROOT/n)==sha for n,sha in design['recorded_inputs'].items())
    assert all(digest(OUT/'source'/n)==sha for n,sha in design['source_files'].items())
    assert all(digest(OUT/'source/engine'/n)==sha for n,sha in build['compiled_files'].items())
    save(OUT/'check-intent.json',{'started_at':datetime.now(timezone.utc).isoformat(),'design_sha256':digest(OUT/'design.json')})
    with (OUT/'check.log').open('x') as log:
        subprocess.run(['node',str(worker),str(ROOT),str(OUT),str(ARTIFACT)],cwd='/tmp',stdout=log,stderr=subprocess.STDOUT,check=True)
    report=read(OUT/'assessment.json');report.update(design_sha256=digest(OUT/'design.json'),build_sha256=digest(OUT/'build.json'),
        details_sha256=digest(OUT/'differences.jsonl'),new_hf_jobs=0,new_inference=0,new_full_games=0,
        qualification_eligible=False,reserved_final_seeds_used=False)
    save(RESULT,report);print(json.dumps(report),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('operation',choices=['prepare','check'])
    globals()[parser.parse_args().operation]()
