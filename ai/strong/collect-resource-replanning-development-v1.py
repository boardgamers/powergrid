"""Audit/archive the complete resource experiment, preserving every adverse cell."""
import argparse
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np
from strategic_collection import ROOT,read,write,digest
from policy_iteration_evidence_archive import upload_evidence

STRONG=ROOT/'ai/strong'
spec=importlib.util.spec_from_file_location('resource_full_comparison',STRONG/'compare-resource-replanning-development-v1.py')
comparison=importlib.util.module_from_spec(spec);spec.loader.exec_module(comparison)
manager,launcher=comparison.manager,comparison.manager.launcher
COORDINATOR=ROOT/'ai/runs/resource-replanning-development-coordinator-v1'
OUT=ROOT/'ai/runs/resource-replanning-development-complete-evidence-v1'
DESCRIPTOR=STRONG/'resource-replanning-development-complete-evidence-v1.json'


def terminal_credit(terminal):
    assert terminal['truncated'] is False
    n=terminal['playerCount'];seat=terminal['seat']
    assert type(n) is int and n in range(2,7) and type(seat) is int and 0<=seat<n
    scores=[tuple(p[k] for k in ('powered','money','cities')) for p in terminal['final']['players']]
    assert len(scores)==n and all(type(v) is int and v>=0 for s in scores for v in s)
    assert all(s[0]<=s[2] for s in scores)
    best=max(scores)
    values=[Fraction(1,scores.count(best)) if score==best else Fraction(0) for score in scores]
    assert terminal['value']==[float(v) for v in values]
    assert abs(terminal['win']-float(values[seat]))<1e-12
    return values[seat]


def audit_equal_count(deal_differences, expected, protocol):
    """Rational deal means, independently reconstructed bootstrap multiplicities."""
    assert set(deal_differences)==set(range(2,7))
    ordered=[]
    for n in range(2,7):
        values=deal_differences[n]
        assert len(values)==4
        actual=expected['player_counts'][str(n)]
        assert actual['weight']==.2 and set(actual['deal_differences'])==set(values)
        for deal,value in values.items():
            assert abs(actual['deal_differences'][deal]-float(value))<1e-12
        assert abs(actual['win_share_difference']-float(sum(values.values())/4))<1e-12
        ordered.append([values[k] for k in sorted(values)])
    estimate=float(sum(sum(values) for values in ordered)/20)
    assert abs(estimate-expected['win_share_difference'])<1e-12
    rng=np.random.default_rng(protocol['bootstrap_seed'])
    bootstrap=np.zeros(protocol['bootstrap_replicates'])
    for values in ordered:
        draws=rng.integers(4,size=(protocol['bootstrap_replicates'],4))
        weights=np.array([np.bincount(draw,minlength=4) for draw in draws])
        bootstrap+=weights @ np.array([float(v) for v in values])/20
    interval=np.quantile(bootstrap,[.025,.975]).tolist()
    assert np.allclose(interval,expected['paired_deal_bootstrap_95_interval'],rtol=0,atol=1e-12)
    return {'win_share_difference':estimate,'paired_deal_bootstrap_95_interval':interval,
            'terminal_fraction_and_bootstrap_multiplicity_audit':True}


def audit():
    state=read(COORDINATOR/'state.json')
    assert state['stage']=='comparison_complete', 'Wait for all 54 original resource batches and their comparison'
    assert state['jobs_submitted']==state['jobs_verified']==54 and not state['failed_jobs']
    assert all(digest(ROOT/name)==sha for name,sha in state['code_hashes'].items())
    result=read(comparison.OUTPUT)
    assert digest(comparison.OUTPUT)==state['comparison_sha256']
    assert result['complete'] and result['games']==3360
    for key in ('candidate_selected','qualification_eligible','reserved_final_seeds_used'):assert result[key] is False
    # Re-read every source/receipt and reproduce the full comparison, not only its hash.
    with tempfile.TemporaryDirectory() as temp:
        output=Path(temp)/'comparison.json'
        comparison.compare(output)
        assert read(output)==result
    plan,protocol=read(launcher.PLAN),read(launcher.PROTOCOL)
    credits={arm:{} for arm in protocol['arms']};games=0
    for shard in plan['shards']:
        folder=manager.COLLECTED/shard['case']
        provenance=result['provenance'][shard['case']]
        assert digest(folder/'verified.json')==provenance['verified_sha256']
        cell=(shard['players'],shard['opponent'])
        actual=credits[shard['arm']].setdefault(cell,{})
        for row in read(folder/'artifacts/evaluation/evaluation.json')['results']:
            t=row['terminal'];key=(t['gameSeed'],t['variant'],t['sealed'],t['seat'])
            assert key not in actual
            actual[key]=terminal_credit(t);games+=1
    assert games==3360
    paired_checks={}
    for opponent,summary in [('search_geo','primary_search_equal_count'),('economic','secondary_economic_equal_count')]:
        differences={}
        for n in range(2,7):
            left=credits['filter'][(n,opponent)];right=credits['resource-filter'][(n,opponent)]
            assert set(left)==set(right)
            differences[n]={}
            for deal in sorted({k[0] for k in left}):
                keys=[k for k in left if k[0]==deal]
                assert len(keys)==4*n
                differences[n][deal]=sum(right[k]-left[k] for k in keys)/len(keys)
        paired_checks[summary]=audit_equal_count(differences,result[summary],protocol)
    return {'complete':True,'jobs':54,'games':3360,'arms':list(protocol['arms']),'cells_per_arm':27,
            'independent_deals_per_cell':4,'all_terminal_credits_recomputed':True,
            'full_comparison_reproduced':True,'paired_summary_audits':paired_checks,'caps':0,
            'comparison_sha256':digest(comparison.OUTPUT),'plan_sha256':digest(launcher.PLAN),
            'protocol_sha256':digest(launcher.PROTOCOL),'source':plan['source'],
            'collector_sha256':digest(__file__),'comparison_code_hashes':result['code_hashes'],
            'costs':result['costs'],'new_hf_jobs':0,'gradients':False,'candidate_selected':False,
            'qualification_eligible':False,'reserved_final_seeds_used':False,
            'scope':result['scope']}


def main(archive=False):
    review=audit()
    if not archive:
        print(json.dumps(review,indent=2));return
    assert not any(p.exists() for p in (OUT,OUT.with_suffix('.tgz'),DESCRIPTOR)), 'Inspect earlier archive outcomes before retrying'
    files=[Path(__file__),comparison.OUTPUT,launcher.PLAN,launcher.PROTOCOL,launcher.SOURCE,
           STRONG/'resource-hf-calibration-evidence-v1.json',STRONG/'policy_iteration_evidence_archive.py',
           STRONG/'test_resource_development_archive_v1.py',STRONG/'test_resource_development_collection_v1.py']
    files += [ROOT/name for name in review['comparison_code_hashes']]
    files += [ROOT/name for name in read(COORDINATOR/'state.json')['code_hashes']]
    files += [p for p in manager.COLLECTED.rglob('*') if p.is_file()]
    files += list(launcher.GUARDS.glob('*.json'))
    files += [COORDINATOR/name for name in ('state.json','coordinator.log','latest-status.json')]
    files += [ROOT/'ai/runs/resource-development-archive-preflight-v1.json',
              ROOT/'ai/runs/resource-development-archive-tests-v1.log']
    OUT.mkdir()
    for path in sorted(set(files)):
        assert path.is_file() and not path.is_symlink()
        destination=OUT/path.relative_to(ROOT);destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,destination);assert digest(path)==digest(destination)
    write(OUT/'review.json',review)
    write(OUT/'manifest.json',{str(p.relative_to(OUT)):digest(p) for p in sorted(OUT.rglob('*')) if p.is_file()})
    write(DESCRIPTOR,{**review,**upload_evidence(OUT)})
    print({k:read(DESCRIPTOR)[k] for k in ('revision','archive_sha256','archived_files','remote_archive_verified')})


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--archive',action='store_true')
    main(p.parse_args().archive)
