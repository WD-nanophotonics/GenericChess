"""Whole-record paired divergence: fixed opponents cannot change first choice."""
from pathlib import Path
from collections import Counter
import json,sys
import chess

def compare(g,h):
 if g is None or h is None:return dict(kind='MISSING_PAIR')
 assert g['initial_record']==h['initial_record'];a=g['record']['moves'];b=h['record']['moves'];n=0
 while n<min(len(a),len(b))and a[n]==b[n]:n+=1
 if n==len(a)==len(b):return dict(kind='IDENTICAL_FULL_RECORD',reward_gain=None if g['reward']is None or h['reward']is None else g['reward']-h['reward'])
 if n==min(len(a),len(b)):return dict(kind='PREFIX_ONLY_END_OR_CENSOR',common_plies=n,reward_gain=None if g['reward']is None or h['reward']is None else g['reward']-h['reward'])
 board=chess.Board(g['record']['initial'])
 for u in a[:n]:board.push_uci(u)
 color=g['slot'][3];actor=0 if board.turn else 1;assert actor==color,'Fixedfoecannotmakefirstdifferentchoice atidenticalhistory!'
 x,y=chess.Move.from_uci(a[n]),chess.Move.from_uci(b[n]);assert x in board.legal_moves and y in board.legal_moves
 return dict(kind='CANDIDATE_FIRST_DIVERGENCE',common_plies=n,candidate=color,left=a[n],right=b[n],left_capture=board.is_capture(x),right_capture=board.is_capture(y),legal_choices=board.legal_moves.count(),reward_gain=None if g['reward']is None or h['reward']is None else g['reward']-h['reward'])

def run(directory):
 d=Path(directory);p=json.loads((d/'eval-plan.json').read_text());rr={tuple(g['slot']):g for g in map(json.loads,(d/'eval-games.jsonl').open())};context='task2572'in str(d);pairs=[]
 if context:
  for m in('initial','TD','TC','WDL'):pairs.append((m+'|q2',m+'|plain'))
 else:
  for m in('TD','TC','WDL'):
   for b in(250000,500000,750000,1000000):pairs.append((m if b==1000000 else m+'@'+str(b),'initial'))
 out={}
 for left,right in pairs:
  cells=[];counts=Counter()
  for seed,f,c,foe in sorted({(s[1],s[2],s[3],s[5])for s in p['slots']}):
   r=compare(rr.get((0,seed,f,c,left,foe)),rr.get((0,seed,f,c,right,foe)));r.update(seed=seed,family=f,color=c,foe=foe);cells.append(r);counts[r['kind']]+=1
   z=r.get('reward_gain');counts['outcome_improved']+=z is not None and z>0;counts['outcome_declined']+=z is not None and z<0;counts['outcome_same']+=z==0;counts['outcome_unresolved']+=z is None
  out[left+'-'+right]=dict(counts=dict(counts),cells=cells)
 result=dict(status='PASS_FIXED_FOE_FIRST_DIVERGENCE_INVARIANT',pairs=out,scope='Descriptivepairedfulltrajectorydiagnostic, no newsearch/causaleffectofindividualmove. Samefoe/ordering/history impliesfirstrealchoicechangeiscandidate; terminalorresourceprefixdifferences reportedseparately. Allnegative/zero outcomes kept.')
 (d/'trajectory-divergence.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v['counts']for k,v in out.items()}))
if __name__=='__main__':run(sys.argv[1])
