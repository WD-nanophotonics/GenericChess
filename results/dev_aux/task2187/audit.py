"""Independent saved-frontier reconstruction; no new proving or gameplay."""
from pathlib import Path
from dataclasses import fields
from collections import Counter
import ast,json,hashlib,time
from generic_chess.core.position import Position,Hands
from generic_chess.core.pieces import Piece
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_proof_rnb_bridge import actor_state
from results.dev_aux.task2187.trace import root_session
from results.dev_aux.task2179.graph import canonical,position_token
from results.dev_aux.task2068.teacher import CanonicalTeacher
OUT=Path('results/dev_aux/task2188')

def decode(token):
 if token==('None',):return None
 if token[0]=='tuple'and len(token)==2:return tuple(decode(x)for x in token[1])
 primitive={'int':int,'bool':bool,'float':float,'str':str,'bytes':bytes}
 if len(token)==2 and token[0]in primitive:
  assert type(token[1])is primitive[token[0]];return token[1]
 registry={(cls.__module__,cls.__qualname__):cls for cls in(Position,Hands,Piece)}
 cls=registry[token[:2]];assert len(token)==3 and [k for k,_ in token[2]]==[f.name for f in fields(cls)]
 return cls(**{k:decode(v)for k,v in token[2]})

def run():
 began=time.perf_counter();teacher=CanonicalTeacher('results/dev_aux/task2171','results/dev_aux/task2172','results/dev_aux/task2176')
 roots={r['family']:r for r in json.loads(Path('results/dev_aux/task2177/inputs.json').read_text())['roots']}
 summaries=[];observations=[]
 for trace in json.loads(Path('results/dev_aux/task2187/traces.json').read_text()):
  root=roots[trace['family']];session=root_session(root);counts=Counter();positions=set();histories=set();maxply=0;maxrepeat=0;ranks=[]
  for n,event in enumerate(trace['events']):
   pos=decode(ast.literal_eval(event['position_token']));assert repr(pos)==event['position_repr']and repr(position_token(pos))==event['position_token']
   rec=deserialize_game_record(json.dumps(event['record']))
   s=GameSession.replay(session.compiled,rec)if trace['arm']=='PN'else GameSession.replay(canonical(pos,session.compiled).compiled,rec)
   assert repr(s.state)==event['state_repr']and hashlib.sha256(repr(s.state).encode()).hexdigest()==event['state_sha']and s.state.position==pos
   row=teacher.rows[teacher.key(actor_state(s.state))];absolute=None if row['label']=='DRAW'else pos.side_to_move if row['label']=='WIN'else 1-pos.side_to_move
   label='DRAW'if absolute is None else'TARGET_POSITION_WIN'if absolute==root['target']else'TARGET_POSITION_LOSS'
   counts[label]+=1;positions.add(event['position_token']);histories.add(event['state_sha']);maxply=max(maxply,s.state.ply_count);maxrepeat=max(maxrepeat,max(dict(s.state.repetition_counts).values()));ranks.append(row['rank'])
   observations.append(dict(family=trace['family'],arm=trace['arm'],event=n,position_label=label,position_rank=row['rank'],actual_ply=s.state.ply_count,fullstate_sha=event['state_sha'],scope='Positional posthoc annotation only; fullhistory reward not inferred.'))
  summaries.append(dict(family=trace['family'],arm=trace['arm'],events=len(trace['events']),unique_positions=len(positions),unique_fullstates=len(histories),duplicate_position_occurrences=len(trace['events'])-len(positions),labels=dict(counts),max_actual_ply=maxply,max_repetition_count=maxrepeat,rank_histogram=dict(Counter(str(r)for r in ranks))))
 result=dict(status='PASS_ALL_SAVED_FRONTIERS_FULL_PUBLIC_RECORD_RECONSTRUCTED',events=len(observations),summaries=summaries,seconds=time.perf_counter()-began,new_proof_queries=0,interpretation='Label access occurs strictly AFTER sealed query data. Canonical target-WIN occupancy is an exploration diagnostic; no arbitrary-history WDL, teacher-guided search or causal frontier superiority claim.')
 OUT.mkdir(exist_ok=False);(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');(OUT/'annotations.json').write_text(json.dumps(observations),encoding='utf-8');print(json.dumps(result),flush=True)
if __name__=='__main__':run()
