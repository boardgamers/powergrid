"""Independent full-budget terminal audit and paired target diagnostics.

Auditing does not admit labels for training or choose a candidate policy.
"""
from fractions import Fraction
import hashlib
import json
import math
import re


def audit(root, result, protocol_sha, identity):
    assert result['protocol_sha256'] == protocol_sha and result['identity'] == identity
    assert result['training_ready'] is False and 'verification_error' not in result
    assert hashlib.sha256(json.dumps(root['request'],sort_keys=True).encode()).hexdigest() == root['public_root_sha256']
    assert root['split'] == ('validation' if root['deal'] in (0,4,8,12) else 'train')
    assert root['source_game_seed'].startswith('policy-iteration-training-v2-')
    c=result['continuations']; n=root['players']; seat=root['request']['player']; baseline=result['baseline']
    options=list(range(len(root['legal']))); samples=64
    assert len(root['request']['state']['players']) == n and 2 <= n <= 6 and 0 <= seat < n
    assert c['mode']=='neural_population' and c['options']==options and baseline in options
    assert set(result['current_shortlist']) <= set(options)
    assert c['samples']==c['count']==samples and c['begin']==0 and len(c['rows'])==samples*len(options)
    assert c['caps']==c['outer_caps']==c['nested_caps']==0 and c['usable'] is True
    assert c['qualification_eligible'] is False
    credits={a:[] for a in options};worlds={};neural=steps=0
    for i,row in enumerate(c['rows']):
        sample,a=divmod(i,len(options))
        assert (row['env'],row['sample'],row['actionIndex'])==(i,sample,a)
        assert row['truncated'] is False and 0<=row['steps']<=2400
        assert len(row['roles'])==n and row['roles'][seat]=='neural'
        assert set(row['roles'])<={'neural','economic','legacy','rush'}
        sha=row['diagnostic']['sampledWorldSha256'];assert re.fullmatch('[a-f0-9]{64}',sha)
        world=(sha,row['roles'],row['initialBelief'])
        assert worlds.setdefault(sample,world)==world, 'Unpaired sampled world, opponent roles or prior bids'
        for field in ('searchStats',): assert row[field]=={'decisions':0,'evaluations':0,'truncated':0}
        assert row['diagnostic']['priorSearchStats']=={'decisions':0,'evaluations':0,'truncated':0}
        terminal=row['diagnostic']['terminal'];assert len(terminal)==n
        scores=[tuple(p[k] for k in ('powered','money','cities')) for p in terminal]
        assert all(type(v) is int and v>=0 for score in scores for v in score)
        best=max(scores);value=Fraction(1,scores.count(best)) if scores[seat]==best else Fraction(0)
        assert type(row['value']) in (int,float) and row['value']==float(value)
        credits[a].append(value)
        assert all(type(v) is int and v>=0 for v in row['policyDecisions'].values())
        assert sum(row['policyDecisions'].values())==row['steps']
        neural+=row['policyDecisions']['neural'];steps+=row['steps']
    assert c['inference_decisions']=={'neural':neural,'surrogate':0}
    means={a:sum(v,Fraction(0))/samples for a,v in credits.items()}
    margins={a:means[a]-means[baseline] for a in options}
    eligible=[a for a in options if a==baseline or margins[a]>Fraction(1,8)]
    chosen=max(eligible,key=lambda a:(means[a],a==baseline,-a))
    e=result['exact_summary']
    assert e['baseline']==baseline and e['selected']==chosen and e['eligible']==eligible
    assert e['meanCredits']=={str(a):str(v) for a,v in means.items()}
    expected={str(a):str(v) for a,v in margins.items()}
    assert e['pairedMeanMargins']==expected and e['populationMeanMargins']=={'neural_population':expected}
    assert e['fallbackReason'] is None and e['truncated']==0 and e['minimumAdvantage']=='1/8'
    diagnostics={}
    for a in options:
        paired=[v-b for v,b in zip(credits[a],credits[baseline])];mean=margins[a]
        variance=sum(((v-mean)**2 for v in paired),Fraction(0))/(samples-1)
        diagnostics[str(a)]={'mean_credit':str(means[a]),'paired_mean_margin':str(mean),
            'paired_standard_error':math.sqrt(float(variance)/samples),
            'half_margins':[str(sum(paired[begin:end],Fraction(0))/(end-begin)) for begin,end in ((0,32),(32,64))]}
    halves=[{a:sum(v[begin:end],Fraction(0))/(end-begin) for a,v in credits.items()} for begin,end in ((0,32),(32,64))]
    best_sets=[[a for a in options if h[a]==max(h.values())] for h in halves]
    return {'rootId':root['rootId'],'split':root['split'],'players':n,'kind':root['kind'],
        'all_legal_options':len(options),'worlds':samples,'rollouts':len(c['rows']),'steps':steps,
        'neural_decisions':neural,'seconds':c['seconds'],'baseline':baseline,'actions':diagnostics,
        'half_best_action_sets':best_sets,'half_best_sets_overlap':bool(set(best_sets[0])&set(best_sets[1])),
        'independently_audited':True,'training_ready':False,'qualified':False}
