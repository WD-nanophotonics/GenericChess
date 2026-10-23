"""Exposed matched counterfactuals within PRIMARY's preexisting frozen families."""
from itertools import combinations
from copy import deepcopy
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
import json,time
from scripts.leaper_explorer_truth import load,save,digest
from scripts.leaper_h6_initial_truth import admit
from scripts.leaper_design import state_sha,physical_action_key
from scripts.leaper_h6_e0 import graph
from scripts.research_record import record_value
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_from_dict
from scripts.leaper_cooperative_truth import cooperative_distances


def physical_action(raw):
    return physical_action_key(action_from_dict(raw),{'K':'K','A':'A','B':'B'})


def analyze(directory):
    directory=Path(directory);inputs=load(directory/'inputs.json.gz');truth=load(directory/'truth.json.gz');rby={r['id']:r for r in truth['roots']};start=time.perf_counter();pairs=[]
    families=[f for f in inputs['families']if f['status']=='CLOSED']
    for left,right in combinations(families,2):
        delta=[a^b for a,b in zip(left['masks'],right['masks'],strict=True)]
        if sum(x.bit_count()for x in delta)!=1:continue
        changed_type='A'if delta[0]else'B'
        def dynamic(r):
            r=deepcopy(r);r.pop('initial_position');r.pop('initial_setup_options',None)
            for pc in r['piece_types']:
                if pc['type_id']==changed_type:pc['movement_atoms']=[]
            return r
        if dynamic(left['rule'])!=dynamic(right['rule']):raise ValueError('other dynamic rule field changed')
        li={tuple(r['placement']):r for r in inputs['rows']if r['family']==left['family']};ri={tuple(r['placement']):r for r in inputs['rows']if r['family']==right['family']}
        lc=admit(left,next(iter(li.values())));rc=admit(right,next(iter(ri.values())));rows=[];trans={k:Counter()for k in ('wdl','fork','cooperative')};action_trans=Counter()
        rightdomain=load(directory/f"domain{right['family']}.json.gz")
        from scripts.leaper_cooperative_certificate import decode_position
        rpositions=[decode_position(p,rc.initial_position)for p in rightdomain['positions']];rindices={p:i for i,p in enumerate(rpositions)}
        distances,_=cooperative_distances(rightdomain['edges'],{int(i)for i,w in rightdomain['terminals'].items()if w is not None})
        for placement in sorted(li.keys()&ri.keys()):
            l,r=li[placement],ri[placement];ls=GameSession.replay(lc,deserialize_game_record(json.dumps(l['full_record'])));rs=GameSession.replay(rc,deserialize_game_record(json.dumps(r['full_record'])))
            lp=record_value(ls.state.position);rp=record_value(rs.state.position);lp.pop('ruleset_fingerprint');rp.pop('ruleset_fingerprint')
            if lp!=rp or state_sha(ls.state)!=l['state_sha256']or state_sha(rs.state)!=r['state_sha256']or ls.state.ply_count or rs.state.ply_count:raise ValueError('not same legal fresh physical state')
            a,b=rby[l['state_sha256']],rby[r['state_sha256']]
            la={physical_action(x['action']):x['wdl_bounds'][0]for x in a['action_bounds']};ra={physical_action(x['action']):x['wdl_bounds'][0]for x in b['action_bounds']}
            oldbest={k for k,v in la.items()if v==a['wdl_bounds'][0]};newbest={k for k,v in ra.items()if v==b['wdl_bounds'][0]}
            unchanged=set(la)&set(ra)
            for action in unchanged:action_trans[str((la[action],ra[action]))]+=1
            trans['wdl'][str((a['wdl_bounds'][0],b['wdl_bounds'][0]))]+=1
            trans['fork'][str((a['wdl_fork'],b['wdl_fork']))]+=1
            trans['cooperative'][str((a['cooperative_decisive'],b['cooperative_decisive']))]+=1
            escapes=[]
            if a['wdl_bounds']!=b['wdl_bounds']:
                for rawaction in b['action_bounds']:
                    key=physical_action(rawaction['action'])
                    if key in newbest and key not in la:
                        child=GameSession.replay(rc,rs.to_record());child.submit(action_from_dict(rawaction['action']))
                        before=sum(pc is not None for pc in rs.state.position.board);after=sum(pc is not None for pc in child.state.position.board)
                        escapes.append(dict(action=rawaction['action'],child_record=record_value(child.to_record()),child_state_sha=state_sha(child.state),
                            captured=before-after,remaining_ordinary=[(pc.owner,pc.current_type_id)for pc in child.state.position.board if pc and pc.current_type_id!='K'],
                            closed_no_decisive_path=rindices[child.state.position]not in distances))
            rows.append(dict(placement=placement,left_id=a['id'],right_id=b['id'],left_record=l['full_record'],right_record=r['full_record'],
                left_WDL=a['wdl_bounds'][0],right_WDL=b['wdl_bounds'][0],left_fork=a['wdl_fork'],right_fork=b['wdl_fork'],
                left_cooperative=a['cooperative_decisive'],right_cooperative=b['cooperative_decisive'],
                common_actions=len(unchanged),added_actions=len(set(ra)-set(la)),removed_actions=len(set(la)-set(ra)),
                common_action_WDL_changes=sum(la[k]!=ra[k]for k in unchanged),best_set_changed=oldbest!=newbest,new_best_escapes=escapes))
        pairs.append(dict(left_family=left['family'],right_family=right['family'],left_masks=left['masks'],right_masks=right['masks'],
            left_fingerprint=left['fingerprint'],right_fingerprint=right['fingerprint'],
            delta_bits=delta,left_total=len(li),right_total=len(ri),common_roots=len(rows),
            left_only=[list(x)for x in sorted(li.keys()-ri.keys())],right_only=[list(x)for x in sorted(ri.keys()-li.keys())],
            common_mu_id=digest(sorted([list(x)for x in li.keys()&ri.keys()])),
            geometry_left=[graph(m)for m in left['masks']],geometry_right=[graph(m)for m in right['masks']],
            transitions={k:dict(v)for k,v in trans.items()},common_action_WDL_transitions=dict(action_trans),
            best_set_changed=sum(r['best_set_changed']for r in rows),rows=rows))
    return dict(format='leaper-H6-existing-adjacent-counterfactual-v1',truth_digest=digest(truth),pairs=pairs,seconds=time.perf_counter()-start,
        scope='All onebitadjacencies among already frozen ordered A/Bfamilies, not newrule/pair sampling or blindprediction. Uniform common admitted labelledfreshplacements. Fullfingerprints/records/setupkeys remain distinct; physicaltype/coordinates mapped explicitly. Not wholefamilyunequalmu or generic monotonicity/strength claim.')


if __name__=='__main__':
    import argparse
    cli=argparse.ArgumentParser();cli.add_argument('--directory',required=True);cli.add_argument('--output',required=True);a=cli.parse_args();r=analyze(a.directory);save(a.output,r)
    print(json.dumps({**r,'pairs':[{k:v for k,v in q.items()if k!='rows'}for q in r['pairs']]}))
