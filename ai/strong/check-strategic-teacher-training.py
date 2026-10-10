"""Real-root grid/proposal checks for the first and last training-label chunks."""
from strategic_training_labels import ROOT,PROTOCOL,read,load_roots,get_model,Node,prepare

p=read(PROTOCOL);model=get_model(p);node=Node('strong/strategic-continuations.cjs');checked=0
try:
    for n,source,start,end in [(2,'economic',0,2),(2,'snapshot0',14,16),(6,'economic',0,2),(6,'snapshot0',14,16)]:
        rows=load_roots(p,n,source,start,end);assert len(rows)==24
        assert {r['decision'] for r in rows}=={'nomination','bid','building'}
        assert {(r['variant'],r['sealed']) for r in rows}=={(v,s) for v in ['original','recharged'] for s in [False,True]}
        for root in [rows[0],rows[-1]]:
            options=prepare(node,model,root);assert root['model_proposal'] in options;checked+=1
finally:node.close()
for start,end in [(-1,1),(0,0),(15,17)]:
    try:load_roots(p,2,'economic',start,end)
    except AssertionError:pass
    else:raise AssertionError('Invalid range accepted')
print({'first_and_last_chunk_grids_passed':True,'exact_proposals_checked':checked,
    'bad_ranges_rejected':True,'gradients':False,'qualification_eligible':False})
