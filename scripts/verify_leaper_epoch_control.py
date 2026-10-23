"""Replay a matched frozen-unit control without rerunning search or games."""
from copy import copy
from collections import Counter
import json,random,time
from generic_chess.core.actions import action_from_dict,action_to_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.learning.incremental import FixedScaleSessionEnv
from scripts.leaper_h6_later_records import ContextBinder
from scripts.leaper_explorer_truth import digest
from scripts.research_record import record_value


def verify(result,controls,training,directory):
    from scripts.verify_leaper_frozen_learning import replay_query
    tick=time.perf_counter();binder=ContextBinder(directory);counts=Counter();summary=[]
    if len(controls)!=256 or len(training)!=256:raise ValueError('complete matched256 support required')
    for row,tr in zip(controls,training,strict=True):
        if any(row[k]!=tr[k]for k in('family','source_index','source_state_sha')):raise ValueError('matched source/seed differs')
        f,c,d,positions,sources=binder.family(row['family'])
        if row['reused_training_trajectory']:
            if tr['before']!=[1.]*4 or row['source_episode_digest']!=digest(tr):raise ValueError('nonunit training trajectory cannot be reused')
            if any(row[k]!=tr[k]for k in('record','result','queries')):raise ValueError('reused source trajectory differs')
            counts['reused_trajectories']+=1;continue
        s=GameSession.replay(c,deserialize_game_record(json.dumps(tr['source_record'])));qrows={q['ply']:q for q in row['queries']};rng=random.Random(2026102402+row['source_index'])
        for ply,rawaction in enumerate(row['record']['actions']):
            if s.result.status.value!='ongoing':raise ValueError('control action after terminal')
            if s.state.position.side_to_move==1:
                env=FixedScaleSessionEnv(s,unit_type='A');aa=sorted(env.actions(),key=lambda a:json.dumps(record_value(a),sort_keys=True));expected=aa[rng.randrange(len(aa))]
                if action_to_dict(expected.action)!=rawaction:raise ValueError('control Uniform opponent seed differs')
            else:
                r=qrows.pop(ply)['receipt']
                if not r['complete']or r['completed_depth']!=1:raise ValueError('unit control incomplete query')
                counts['PV_Core_edges']+=replay_query(s,[1.]*4,r,rawaction);counts['new_queries']+=1;counts['new_nodes']+=r['nodes']
            s.submit(action_from_dict(rawaction));counts['trajectory_Core_edges']+=1
        if qrows or s.result.status.value=='ongoing':raise ValueError('control final record incomplete')
        outcome=0 if s.result.winner is None else 1 if s.result.winner==0 else-1
        if row['result']['outcome']!=outcome or row['result']['update']is not None:raise ValueError('unit control actual outcome/update differs')
    for family in(6,9):
        pairs=[(tr,r)for tr,r in zip(training,controls,strict=True)if tr['family']==family]
        summary.append(dict(family=family,episodes=len(pairs),different_complete_records=sum(t['record']!=r['record']for t,r in pairs),different_terminal_outcomes=sum(t['result']['outcome']!=r['result']['outcome']for t,r in pairs),terminal_U0_gain=sum(t['result']['outcome']-r['result']['outcome']for t,r in pairs)/len(pairs)))
    if summary!=result['summary']or any(counts[k]!=result[k]for k in('reused_trajectories','new_queries','new_nodes')):raise ValueError('matched outcome/cost summary differs')
    return dict(verified=True,summary=summary,counts=dict(counts),seconds=time.perf_counter()-tick,
        scope='254actualnewunitcontroltrajectories and2bytebound initial-unit trainingreuses. Matchedsource/opponentRNG/PVs/actualterminals checked. Finiteexposedoneepoch result,notindependentstrength.')
