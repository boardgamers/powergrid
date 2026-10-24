"""Full fixed-grid comparison only; never choose from incomplete hybrid results."""
import argparse
import importlib.util
from pathlib import Path

from strategic_collection import ROOT,read,write,digest
from population_hybrid_development import PLAN,SOURCE,PROTOCOL,validate_plan,verify_job
from policy_iteration_development import summarize

spec=importlib.util.spec_from_file_location('hybrid_pairs',ROOT/'ai/strong/compare-population-screens.py')
pairs=importlib.util.module_from_spec(spec);spec.loader.exec_module(pairs)


def rule_views(rows):
    return {v+('/sealed' if s else '/open'):[r for r in rows if r['variant']==v and r['sealed']==s]
        for v in ['original','recharged'] for s in [False,True]}


def main(output):
    assert not output.exists()
    plan=read(PLAN);protocol=read(PROTOCOL);source=read(SOURCE);validate_plan(plan,protocol)
    assert plan['source']==source and plan['protocol_sha256']==digest(PROTOCOL)
    reports={arm:{} for arm in protocol['arms']};provenance={}
    for row in plan['shards']:
        case=row['case'];base=ROOT/'ai/runs/population-hybrid-development-collected-v1'/case
        checked=read(base/'verified.json');guard=read(ROOT/'ai/runs/population-hybrid-development-launches-v1'/(case+'.json'))
        assert checked['verified'] and checked['job_id']==guard['job_id'] and checked['row']==row
        assert checked['source']==source and checked['plan_sha256']==digest(PLAN)
        assert all(digest(ROOT/name)==sha for name,sha in checked['code_hashes'].items())
        artifacts=base/'artifacts';manifest=read(artifacts/'manifest.json')
        assert all(digest(artifacts/name)==sha for name,sha in manifest.items())
        assert verify_job(artifacts,row,source,protocol)==checked['summary']
        cell=row['opponent']+'/'+str(row['players'])+'p'
        reports[row['arm']].setdefault(cell,[]).extend(r['terminal'] for r in read(artifacts/'evaluation/evaluation.json')['results'])
        provenance[case]={'job_id':checked['job_id'],'verified_sha256':digest(base/'verified.json'),'evidence':checked['evidence']}
    assert all(len(cells)==27 and sum(len(rows) for rows in cells.values())==1680 for cells in reports.values())
    absolute={arm:{cell:{'overall':summarize(rows,protocol),
        'by_rules':{rule:summarize(selected,protocol) for rule,selected in rule_views(rows).items()}}
        for cell,rows in cells.items()} for arm,cells in reports.items()}
    comparisons={}
    for left,right in [('filter','model'),('auction','filter'),('building','filter'),('combined','filter'),('combined','auction'),('combined','building')]:
        result={}
        for cell,rows in reports[left].items():
            other=reports[right][cell];a,b=rule_views(rows),rule_views(other)
            def contrast(x,y):return pairs.paired_difference(x,y,repeats=protocol['bootstrap_replicates'],seed=protocol['bootstrap_seed'])
            result[cell]={'overall':contrast(rows,other),'by_rules':{rule:contrast(a[rule],b[rule]) for rule in a}}
        comparisons[left+'-minus-'+right]=result
    write(output,{'complete':True,'games':8400,'independent_deals_per_cell':4,'absolute':absolute,
        'comparisons':comparisons,'source':source,'protocol_sha256':digest(PROTOCOL),'plan_sha256':digest(PLAN),
        'provenance':provenance,'candidate_selected':False,'qualification_eligible':False,'reserved_final_seeds_used':False,
        'scope':'Initial four-deal development screen only, all five arms and all adverse count/rule/opponent cells. Whole-deal exploratory marginal intervals are coarse; requires separately frozen fresh confirmation before final selection.'})


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args().output.resolve())
