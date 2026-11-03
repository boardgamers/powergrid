"""Local real-service engineering smoke ONLY; never production stress roots.

Run after source/tests are final. Writes 240 smoke outcomes plus compact evidence
under a dedicated ignored ai/runs/multimap-* directory. It does not publish,
launch, train, select, or draw strength conclusions. Parent archives the evidence
and creates the launcher-gating stress-preflight-v1.json receipt separately.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import time

from data import ROOT, atomic_json, digest
from stress_study import run, read, identity, ARTIFACT, REFERENCE_PYTHON
from expert_ppo import config

TIMINGS={'featureMs','inferenceMs','referenceMs','seconds'}


def preflight(output):
    output=Path(output).resolve()
    if output.parent!=(ROOT/'ai/runs').resolve() or not output.name.startswith('multimap-'):
        raise ValueError('Use a dedicated ignored multimap run directory')
    if output.exists():raise ValueError('Preflight output already exists; inspect it, never overwrite')
    output.mkdir(parents=True)
    began=time.monotonic();matched=0;controllers=Counter();public=Counter();manifests={};identities={}
    frozen=config(False,workers=6)
    # Compiled engine files are separately pinned by config. Every Git-tracked
    # serving input must still equal the original expert-v2 source commit.
    import hashlib
    for name,sha in frozen['sourceFiles'].items():
        if name.startswith('engine/dist/'):continue
        old=subprocess.check_output(['git','show','db144fc87d6745fe595ec7e28afc68de496b7966:'+name],cwd=ROOT)
        if hashlib.sha256(old).hexdigest()!=sha:raise ValueError('Legacy serving source differs from frozen Git revision')
    for panel in ('strong','mixed'):
        before=identity(panel,True,6,ARTIFACT,REFERENCE_PYTHON)
        one=output/(panel+'-uninterrupted');two=output/(panel+'-resumed')
        first=run(one,panel,smoke=True)
        assert run(two,panel,smoke=True,stop_after_batches=2) is None
        committed={p.name:digest(p) for p in two.glob('batch-*.json')}
        # Simulate a kill in the next atomic write; it must never be read.
        (two/'batch-002.json.tmp').write_text('{uncommitted engineering scratch')
        second=run(two,panel,smoke=True)
        assert first==second and all(digest(two/n)==sha for n,sha in committed.items())
        assert read(one/'plan.json')==read(two/'plan.json')==before
        for a in sorted(one.glob('batch-*.json')):
            b=two/a.name
            left=read(a);right=read(b)
            assert {k:v for k,v in left.items() if k!='games'}=={k:v for k,v in right.items() if k!='games'}
            for x,y in zip(left['games'],right['games']):
                assert {k:v for k,v in x.items() if k not in TIMINGS}=={k:v for k,v in y.items() if k not in TIMINGS}
                matched+=1;controllers.update({k:sum(v.values()) for k,v in x['counts'].items()});public.update(x['publicChecks'])
        # Completed resume returns without even loading models or collecting.
        from unittest.mock import patch
        with patch('stress_study.load_models',side_effect=AssertionError('completed resume loaded models')), \
             patch('stress_study.collect',side_effect=AssertionError('completed resume repeated games')):
            assert run(two,panel,smoke=True)==second
        assert identity(panel,True,6,ARTIFACT,REFERENCE_PYTHON)==before
        identities[panel]=before
        for p in (one,two):
            manifests[p.name]={f.name:digest(f) for f in p.iterdir() if f.is_file()}
    assert matched==120 and all(controllers[k]>0 for k in ('expert24','ppo0','ppo1','ppo2','reference','teacherV2','fixedV1','fixedV2'))
    assert public['expertAtomicLegal']==0 and public['referenceAtomicLegal']>0
    report=dict(schema='multimap-stress-real-preflight-v1',allChecksPassed=True,smokeIdentities=identities,
        protocolSha256=digest(ROOT/'ai/multimap/stress-protocol-v1.json'),totalTerminalGames=240,
        exactTerminalAndCounterReplayMatches=120,failures=0,interruptedAfterBatches=2,
        completedBatchesPreserved=True,interruptedTemporaryBatchIgnored=True,completedResumePerformsNoCollection=True,
        bothPanels=True,allFourMaps=True,allFivePlayerCounts=True,allFourRules=True,
        controllersPerExecution=dict(controllers),publicChecksPerExecution=dict(public),
        legacyServingGit='db144fc87d6745fe595ec7e28afc68de496b7966',legacyServingGitHashesVerified=True,
        reusedReferenceArtifact=True,manifests=manifests,seconds=time.monotonic()-began,
        qualified=False,qualificationEligible=False,reservedFinalSeedsUsed=False,
        note='Real pinned policies/reference, but engineering smoke only. Repeated identical smoke roots deliberately test replay/resume, not independent observations or strength. No production stress tasks executed.')
    atomic_json(output/'report.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('smokeIdentities','manifests')},indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();preflight(a.output)
