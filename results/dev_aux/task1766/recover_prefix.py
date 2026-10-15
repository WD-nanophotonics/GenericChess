"""Recover the capped pilot's retained Native prefix without any engine rerun."""
import json
from pathlib import Path
from scripts.generic_proof_rnb_bridge import compile_rnb,from_actor,actor_state,uci
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
p=Path('results/dev_aux/task1766');plan=json.loads((p/'plan.json').read_text());rows=[json.loads(x) for x in (p/'run/games.jsonl').read_text().splitlines()];choices=[json.loads(x) for x in (p/'run/choices.jsonl').read_text().splitlines()]
order=[]
for f in plan['families']:
 cells=[(False,0),(True,0),(False,1),(True,1)]
 if f['family']%2:cells.reverse()
 for proof,index in cells:
  for color in (0,1):
   for op in plan['opponents']:order.append((f['family'],proof,index,color,op['id']))
assert [(r['family'],r['proof'],r['price_index'],r['color'],r['opponent']) for r in rows]==order[:len(rows)]
used=sum(z['decision']['source']=='EXTERNAL_SEARCH' for r in rows for z in r['trajectory']);remaining=choices[used:]
key=order[len(rows)];f=next(x for x in plan['families'] if x['family']==key[0]);c=compile_rnb();s=from_actor(c,f['roots'][key[3]]);path=[]
for index,receipt in enumerate(remaining):
 # The actual post-move board+turn is exactly the next recorded query input;
 # retain this native-observed contiguous prefix, never invent missing moves.
 assert actor_state(s)==tuple(receipt['state'])
 move=receipt['raw'][-1].split()[1];legal={uci(a):a for a in legal_actions(s,c)};assert move in legal
 path.append(dict(receipt_index=used+index,state=actor_state(s),move=move,reported_nodes=receipt['reported_nodes']))
 s=apply_action(s,legal[move],c)
out=dict(status='RECOVERED_CONTIGUOUS_NATIVE_OBSERVED_PREFIX',game_key=key,recorded_native_steps=len(path),trajectory=path,end=actor_state(s),terminal=s.terminal_status.status.value,winner=s.terminal_status.winner,
         payoff=None if not s.terminal_status.is_terminal else 0 if s.terminal_status.winner is None else 1 if s.terminal_status.winner==key[3] else -1,
         actual_new_native_go=0,scope='Does not change original750 completed-game record or128-family planned status. Prefix reconstructed only from retained receipts and public legal transitions; remaining unplayed tail UNKNOWN.')
(p/'recovered_partial.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='trajectory'})
