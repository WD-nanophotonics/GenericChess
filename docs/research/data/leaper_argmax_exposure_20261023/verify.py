"""Check the compact observer packet with public Core; no fitness or training.

This verifies saved arithmetic, selected complete-history finite searches and
all saved AND/OR mate certificates. It does not regenerate the capped graph
census or turn an observer prefix into representative population evidence.
"""
from __future__ import annotations
import gzip,hashlib,importlib.util,json,sys,time
from collections import Counter,defaultdict
from copy import deepcopy
from fractions import Fraction as F
from itertools import combinations,product
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from scripts.leaper_design import compile_rule,ruleset_from_dict,GameSession,state_sha
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.transition import legal_successors
from generic_chess.core.actions import action_to_dict
from generic_chess.ai.alphabeta.search import terminal_score
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model
from generic_chess.core.actions import action_from_dict
from math import isclose

def replay(c,record):
    return GameSession.replay(c,deserialize_game_record(json.dumps(record)))

def actionkey(a):
    return json.dumps(a,sort_keys=True,separators=(',',':'))

def verify_mate(c,state,proof,attacker):
    """A positive proof needs one attacker choice and EVERY defender choice."""
    if state.terminal_status.is_terminal:
        assert state.terminal_status.winner==attacker
        assert proof==dict(terminal=state.terminal_status.status.name,winner=attacker)
        return 0,1
    edges=proof['edges'];own=state.position.side_to_move==attacker
    assert proof['kind']==('OR'if own else'AND')
    legal={actionkey(action_to_dict(a)):s for a,s in legal_successors(state,c)}
    chosen={actionkey(e['action']):e for e in edges}
    assert len(chosen)==len(edges) and chosen
    assert set(chosen)<=set(legal)
    assert len(chosen)==1 if own else set(chosen)==set(legal)
    children=[verify_mate(c,legal[k],e['child'],attacker)for k,e in chosen.items()]
    distance=1+max(d for d,n in children)
    assert proof['distance']==distance
    return distance,1+sum(n for d,n in children)

def shortest_within(c,state,attacker,left):
    if state.terminal_status.is_terminal:
        return 0 if state.terminal_status.winner==attacker else None
    if not left:return None
    values=[shortest_within(c,ch,attacker,left-1)for a,ch in legal_successors(state,c)]
    assert values
    if state.position.side_to_move==attacker:
        good=[v for v in values if v is not None]
        return 1+min(good)if good else None
    return None if any(v is None for v in values)else 1+max(values)

def exact_scores(c,state,depth,prices,ply=0,guard=None):
    if guard is not None:guard()
    if state.terminal_status.is_terminal:
        v=terminal_score(state.terminal_status,state.position.side_to_move,ply)
        return (F(v),)*len(prices),1
    if not depth:
        sign=1 if state.position.side_to_move==0 else -1
        a=sum((1 if p.owner==0 else-1)for p in state.position.board if p and p.current_type_id=='A')
        b=sum((1 if p.owner==0 else-1)for p in state.position.board if p and p.current_type_id=='B')
        assert -1<=a<=1 and -1<=b<=1
        return tuple(sign*(a+b*r)for r in prices),1
    values=[];nodes=1
    for action,child in legal_successors(state,c):
        v,n=exact_scores(c,child,depth-1,prices,ply+1,guard);values.append(tuple(-x for x in v));nodes+=n
    assert values
    return tuple(max(v[j]for v in values)for j in range(len(prices))),nodes

def clock_value(c,state,cache):
    if state.terminal_status.is_terminal:
        w=state.terminal_status.winner
        return 0 if w is None else 1 if w==state.position.side_to_move else -1
    assert state.ply_count<128
    if state not in cache:
        cache[state]=max(-clock_value(c,ch,cache)for a,ch in legal_successors(state,c))
    return cache[state]

def verify_signed(packet,compiled):
    result=packet['signed'];truth=packet['old_five_truth'];roots={r['id']:r for r in truth}
    assert len(roots)==379 and len(result['rows'])==379
    cuts=sorted({F(c-a,b-d)for(a,b),(c,d)in combinations(product(range(-1,2),repeat=2),2)if b!=d})
    assert list(map(str,cuts))==packet['signed_analysis']['rational_cuts']
    shared=set(packet['shared_failure_ids']);literal=0;bound=0;errors=defaultdict(F)
    for row in result['rows']:
        r=roots[row['id']];c=compiled[r['record']['ruleset_fingerprint']]
        s=replay(c,r['record']).state;assert state_sha(s)==r['id'];bound+=1
        labels={actionkey(b['action']):b for b in r['branches']}
        assert r['WDL']==max(b['WDL']for b in r['branches'])
        legal={actionkey(action_to_dict(a)):ch for a,ch in legal_successors(s,c)}
        assert set(legal)==set(labels)
        for d in row['depths']:
            bs=d['branches'];assert {actionkey(b['action'])for b in bs}==set(legal)
            for b in bs:
                assert (b['WDL'],b['rank'])==(labels[actionkey(b['action'])]['WDL'],labels[actionkey(b['action'])]['rank'])
            for j,q in enumerate(d['conditions']):
                top=max(b['scores'][j]for b in bs);support=[i for i,b in enumerate(bs)if b['scores'][j]==top]
                assert q['support']==support and q['support_WDL']==[bs[i]['WDL']for i in support]
                mech='strict_bad_support'if max(q['support_WDL'])<r['WDL']else'mixed_WDL_tie'if min(q['support_WDL'])<r['WDL']else'all_optimal'
                assert q['mechanism']==mech
                errors[d['depth'],j]+=F(sum(v<r['WDL']for v in q['support_WDL']),len(support))
                if q['chosen']is not None:
                    assert q['chosen']in support and q['chosen_WDL']==bs[q['chosen']]['WDL']
            if r['id']in shared:
                prices=tuple(F(str(q['B']))for q in d['conditions'][:15])
                for b in bs:
                    v,n=exact_scores(c,legal[actionkey(b['action'])],d['depth']-1,prices,1)
                    assert [-float(vv)for vv in v]==b['scores'][:15];literal+=n
    for(depth,j),value in errors.items():
        assert str(value)==packet['signed_analysis']['tables'][f'D{depth}:condition{j}']['uniform_argmax_expected_errors']
    return bound,literal

def main():
    tick=time.perf_counter();base=Path(__file__).resolve().parent
    manifest=json.loads((base/'manifest.json').read_text());blob=(base/'evidence.json.gz').read_bytes()
    assert hashlib.sha256(blob).hexdigest()==manifest['sha256']
    p=json.loads(gzip.decompress(blob));compiled={fp:compile_rule(ruleset_from_dict(r))for fp,r in p['rules'].items()}
    assert all(c.ruleset_fingerprint==fp for fp,c in compiled.items())
    roots,literal=verify_signed(p,compiled)
    new_argmax_nodes=0
    for row in p.get('new_argmax',{}).get('rows',[]):
        r=p['query_truth'][row['id']];c=compiled[r['record']['ruleset_fingerprint']];s=replay(c,r['record']).state
        legal={actionkey(action_to_dict(a)):ch for a,ch in legal_successors(s,c)}
        assert {actionkey(b['action'])for b in row['branches']}==set(legal)
        for b in row['branches']:
            values,n=exact_scores(c,legal[actionkey(b['action'])],3,tuple(map(F,p['new_argmax']['prices'])),1)
            assert list(map(str,(-v for v in values)))==b['scores'];new_argmax_nodes+=n
    mate_nodes=0;mate_counts=Counter()
    for row in p['shallow_mate']['rows']:
        c=compiled[row['fingerprint']];s=replay(c,row['record']).state
        assert row['distance']==shortest_within(c,s,row['attacker'],3)
        if row['proof']is not None:
            d,n=verify_mate(c,s,row['proof'],row['attacker']);assert d==row['distance'];mate_nodes+=n
        mate_counts[f"{row['run']}:distance{row['distance']}"]+=1
    assert dict(mate_counts)==p['shallow_mate']['counts']
    negative=0
    for row in p['shallow_mate']['rows']:
        if row['distance']==3 and any(e['child'].get('kind')=='AND'and len(e['child']['edges'])>1 for e in row['proof']['edges']):
            broken=deepcopy(row['proof']);broken['edges'][0]['child']['edges'].pop()
            try:verify_mate(compiled[row['fingerprint']],replay(compiled[row['fingerprint']],row['record']).state,broken,row['attacker'])
            except AssertionError:negative+=1
            else:raise AssertionError('missing defender accepted')
            break
    spec=importlib.util.spec_from_file_location('savedproof',base.parent/'leaper_primary_AB_truth_20261022'/'verify.py')
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    proof_nodes=0
    for row in p['proofs']:
        if row['status']=='COMPLETE':proof_nodes+=verifier.verify_proof(compiled[row['record']['ruleset_fingerprint']],row)
    clock_roots=0
    for row in p.get('clock',{}).get('rows',[]):
        c=compiled[row['record']['ruleset_fingerprint']];s=replay(c,row['record']).state
        assert state_sha(s)==row['id'] and clock_value(c,s,{})==row['WDL'];clock_roots+=1
    query_nodes=0;query_bindings=0
    for hid,r in p.get('query_truth',{}).items():
        c=compiled[r['record']['ruleset_fingerprint']];s=replay(c,r['record']).state
        assert state_sha(s)==hid and r['WDL']==max(b['WDL']for b in r['branches'])
        assert {actionkey(action_to_dict(a))for a,ch in legal_successors(s,c)}=={actionkey(b['action'])for b in r['branches']}
        query_bindings+=1
    gridlookup={(q['id'],q['B'],q['requested']):q for q in p['queries']}
    datasets={'grid':dict(queries=p['queries'],summary=p['query_summary'])}|p.get('controls',{})
    dataset_costs={}
    for name,dataset in datasets.items():
        paid=newpaid=reused=0
        for row in dataset['queries']:
            r=p['query_truth'][row['id']];assert row['best_WDL']==r['WDL']
            if row['action']is not None:
                assert row['chosen_WDL']==next(b['WDL']for b in r['branches']if b['action']==row['action'])
            else:assert row['chosen_WDL']is None
            paid+=row['nodes'];newpaid+=row['nodes']if row['new_call']else 0
            if name in('mobility','static'):
                m=p['prior_metadata'][r['record']['ruleset_fingerprint']]
                expected=m['degree'][1]/m['degree'][0]if name=='mobility'else m['static']['B']/m['static']['A']
                assert row['B']==expected
            if not row['new_call']:
                old=gridlookup[row['id'],row['B'],row['requested']]
                assert old['usable']and old['completed']==old['requested'];reused+=1
                for field in('action','chosen_WDL','nodes','completed'):assert row[field]==old[field]
        ss=dataset['summary'];assert paid==ss['nodes']and newpaid==ss['new_nodes']and reused==ss['reused_queries']
        assert len(dataset['queries'])==ss['recorded']and ss['missing']==ss['planned']-ss['recorded']
        dataset_costs[name]=dict(attributed_nodes=paid,new_nodes=newpaid,reused_queries=reused,recorded=ss['recorded'],missing=ss['missing'])
        query_nodes+=newpaid
    pv_edges=0
    for q in p.get('pv_controls',[]):
        r=p['query_truth'][q['id']];c=compiled[r['record']['ruleset_fingerprint']]
        session=replay(c,r['record']);assert q['PV'] and q['PV'][0]==q['action']
        for raw in q['PV']:session.submit(action_from_dict(raw));pv_edges+=1
        env=FixedScaleSessionEnv(session,unit_type='A');actual=env.terminal()
        if q['pv_terminal']:
            from generic_chess.learning.incremental import MATE
            assert actual is not None and q['value']==MATE*actual
        else:
            assert actual is None and list(env.features())==q['pv_phi']
            model=Model([q['B']if name=='B'else 1. for kind,name in env.names])
            assert isclose(model.raw(env.features()),q['value'],rel_tol=1e-12,abs_tol=1e-10)
    assert negative==1
    episode_nodes=episode_plies=0
    if 'episode_cost'in p:
        e=p['episode_cost'];c=compiled[e['initial_record']['ruleset_fingerprint']];s=replay(c,e['initial_record'])
        assert e['models_before']==e['models_after']and e['result']['update']is None
        for q in e['queries']:
            assert state_sha(s.state)==q['state_sha256']and s.state.ply_count==q['root_ply']
            episode_nodes+=q['nodes']
            if q['usable']:
                assert q['action']is not None;s.submit(action_from_dict(q['action']));episode_plies+=1
        assert s.to_record()==deserialize_game_record(json.dumps(e['final_record']))
        assert FixedScaleSessionEnv(s,unit_type='A').terminal()==e['result']['outcome']
        assert episode_nodes==e['result']['nodes']and episode_plies==e['result']['plies']
    print(json.dumps(dict(status='PASS',old_five_full_bindings=roots,exact_signed_literal_visits=literal,new_argmax_literal_visits=new_argmax_nodes,shallow_roots=len(p['shallow_mate']['rows']),positive_mate_certificate_nodes=mate_nodes,missing_defender_rejected=negative,other_saved_proof_nodes=proof_nodes,clock_roots=clock_roots,new_query_full_bindings=query_bindings,new_query_nodes=query_nodes,dataset_costs=dataset_costs,selected_literal_PV_edges=pv_edges,zero_update_episode_nodes=episode_nodes,zero_update_episode_plies=episode_plies,seconds=time.perf_counter()-tick,scope='Core/selectedliteral/certificate/arithmetic verification;not independent engine or full cappedgraph-census regeneration.'),indent=2))

if __name__=='__main__':main()
