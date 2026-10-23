"""Reproduce a saved exposed TDLeaf epoch from real records and receipts.

No search/Player or new experimental training run. Full legal trajectories,
matched Uniform opponent RNG and exact library TDLeaf arithmetic are replayed.
"""
from collections import Counter
from copy import copy
from pathlib import Path
import argparse,json,random,time
from generic_chess.core.actions import action_from_dict,action_to_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,TDLeafEpisode,Receipt,MATE
from scripts.leaper_h6_initial_truth import admit
from scripts.leaper_explorer_truth import load,digest
from scripts.leaper_design import state_sha,match_action
from scripts.research_record import record_value


def verify(plan,result,episodes,directory):
    tick=time.perf_counter();directory=Path(directory);inputs=load(directory/'inputs.json.gz');adj=load(directory/'adjacent-pairs.json.gz');pair=adj['pairs'][0]
    if digest(inputs)!=plan['source_inputs_digest']or digest(adj)!=plan['source_adjacency_digest']:raise ValueError('original non-oracle source differs')
    source={r['state_sha256']:r for r in inputs['rows']};counts=Counter();summaries=[]
    for field,key in(('left_family','left_id'),('right_family','right_id')):
        family=next(f for f in inputs['families']if f['family']==pair[field]);selected=[r for r in episodes if r['family']==family['family']]
        if [r['source_index']for r in selected]!=plan['order']or len(selected)!=128:raise ValueError('unfiltered128start support/order differs')
        first=source[pair['rows'][0][key]];c=admit(family,first);names=FixedScaleSessionEnv(GameSession(c),unit_type='A').names;model=Model([1.]*len(names));outcomes=Counter();changed=0
        for row in selected:
            index=row['source_index'];sr=source[pair['rows'][index][key]]
            if sr['state_sha256']!=row['source_state_sha']or sr['full_record']!=row['source_record']or model.weights!=row['before']:raise ValueError('source start/model epoch differs')
            s=GameSession.replay(c,deserialize_game_record(json.dumps(row['source_record'])));qrows={q['ply']:q for q in row['queries']};rng=random.Random(2026102402+index);learner=TDLeafEpisode(.05,.95)
            actions=row['record']['actions'];initial=s.state.ply_count
            if initial!=0:raise ValueError('training start not original fresh record')
            for ply,rawaction in enumerate(actions):
                if s.result.status.value!='ongoing':raise ValueError('action after actual terminal')
                if s.state.position.side_to_move==1:
                    env=FixedScaleSessionEnv(s,unit_type='A');aa=sorted(env.actions(),key=lambda a:json.dumps(record_value(a),sort_keys=True));expected=aa[rng.randrange(len(aa))]
                    if action_to_dict(expected.action)!=rawaction:raise ValueError('matched Uniform opponent differs')
                else:
                    q=qrows.pop(ply);r=q['receipt']
                    if q['actor']!=0 or not r['complete']or r['completed_depth']!=1:raise ValueError('training search incomplete/depth differs')
                    if not r['pv_choices']or r['pv_choices'][0]!=r['action']:raise ValueError('training PV action differs')
                    ss=copy(s)
                    for k,choice in enumerate(r['pv_choices']):
                        if choice['kind']!='ACTION':raise ValueError('unsupported declaration')
                        aa=match_action(ss,choice['action'])
                        if k==0 and action_to_dict(aa)!=rawaction:raise ValueError('actual played candidate differs')
                        ss.submit(aa);counts['PV_Core_edges']+=1
                    env=FixedScaleSessionEnv(ss,unit_type='A');actual=env.terminal();phi=None if actual is not None else list(env.features())
                    if r['pv_terminal']!=(actual is not None)or r['pv_phi']!=phi:raise ValueError('training leaf/gradient differs')
                    v=MATE*actual if actual is not None else model.raw(phi)
                    if v!=r['value']:raise ValueError('training bootstrap value differs')
                    learner.observe(model,Receipt(**r));counts['queries']+=1;counts['nodes']+=r['nodes']
                s.submit(action_from_dict(rawaction));counts['trajectory_Core_edges']+=1
            if qrows or state_sha(s.state)!=row['final_state_sha']or s.result.status.value=='ongoing':raise ValueError('trajectory/final receipt differs')
            outcome=0 if s.result.winner is None else 1 if s.result.winner==0 else-1
            if row['result']['outcome']!=outcome or row['result']['ending']!='ACTUAL_TERMINAL':raise ValueError('actual terminal outcome differs')
            update=learner.finish(model,outcome)
            if update!=row['result']['update']or model.weights!=row['after']:raise ValueError('library frozenepisode TD update differs')
            if model.weights[0]!=1 or model.weights[2:]!=[1.,1.]:raise ValueError('fixed/unused channel changed')
            outcomes[outcome]+=1;changed+=bool(update['changed']);counts['episodes']+=1
        saved=next(m for m in result['models']if m['family']==family['family'])
        if saved['weights']!=model.weights or saved['names']!=[list(n)for n in names]:raise ValueError('final learned model differs')
        summaries.append(dict(family=family['family'],outcomes=dict(outcomes),changed_episodes=changed,weights=model.weights))
    if any(counts[k]!=result[k]for k in('episodes','queries','nodes')):raise ValueError('training paid cost differs')
    return dict(verified=True,counts=dict(counts),summaries=summaries,seconds=time.perf_counter()-tick,
        scope='Alloriginalstarts/opponentrandomchoices/actualrecords/searchPVs andexactTDarithmeticreproduced. NoPlayer,newtrainingexperiment,oracletrainingtargetsorheldoutclaim.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--result',type=Path,required=True);p.add_argument('--episodes',type=Path,required=True);p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=verify(json.loads(a.plan.read_bytes()),json.loads(a.result.read_bytes()),[json.loads(s)for s in a.episodes.read_text().splitlines()],a.directory);a.output.write_text(json.dumps(r,indent=2));print(r)
