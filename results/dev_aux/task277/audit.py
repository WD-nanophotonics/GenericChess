import json,time,hashlib,importlib.util
from fractions import Fraction
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task277';D=json.loads((R/'results/dev_aux/task276/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task276/result.json').read_bytes());assert X['complete'];start=time.monotonic();TAG='$dev_aux_constant_telemetry_v1'
def hook(d):
 if set(d)=={TAG}:z=d[TAG];assert type(z['count']) is int and z['count']>=16;return [z['value'] for _ in range(z['count'])]
 return d
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
rows=json.loads((R/'results/dev_aux/task276/result.json').read_bytes(),object_hook=hook)['calls'];journal=[json.loads(line,object_hook=hook) for line in (R/'results/dev_aux/task276/journal.jsonl').read_bytes().splitlines()];assert len(journal)==8
for i,z in enumerate(journal):assert i==z['sequence'] and hashlib.sha256(canonical(z['record'])).hexdigest()==z['sha256']
checks=0;leaves=0;cache={}
for row in rows:
 z=row['record'];f=D['roots'][z['root']];b=chess.Board(f['initial_fen'])
 for text in f['history']:b.push_uci(text)
 assert b.fen()==f['expected_fen'] and z['opening_history']==f['history'];si=0
 for ply,text in enumerate(z['actions']):
  if b.turn==z['color']:
   rr=z['search_records'][si];raw=rr['result'];assert rr['root_fen']==b.fen() and rr['full_history']==[m.uci() for m in b.move_stack];side=b.turn;key=tuple(rr['full_history'])
   if key not in cache:
    scores=[]
    def value(p):
     global leaves
     leaves+=1;out=b.outcome(claim_draw=False)
     if out:return 0 if out.winner is None else 100000000-p if out.winner==side else -100000000+p
     return 208*sum(len(b.pieces(t,side))-len(b.pieces(t,not side)) for t in range(1,6))
    for cand in sorted(b.legal_moves,key=lambda m:m.uci()):
     b.push(cand)
     if b.is_game_over(claim_draw=False):vv=[value(1)]
     else:
      vv=[]
      for reply in sorted(b.legal_moves,key=lambda m:m.uci()):b.push(reply);vv.append(value(2));b.pop()
     b.pop();scores.append((cand.uci(),min(vv)))
    best=max(v for m,v in scores);cache[key]=best,[m for m,v in scores if v==best]
   best,aa=cache[key];assert raw['completed_depth']==2 and raw['score']==best and text in aa and not raw['used_fallback'];assert raw['root_window_pruning']==False;checks+=1;si+=1
  m=chess.Move.from_uci(text);assert m in b.legal_moves;b.push(m)
 assert b.fen()==z['final_fen'];actor=z['color'];unit=sum(len(b.pieces(t,actor))-len(b.pieces(t,not actor)) for t in range(1,6));assert z['score']['quantity_difference']==unit
for triple in range(8):
 rr=[z['record'] for z in rows if z['triple']==triple]
 def strip(v):
  if isinstance(v,dict):return {k:strip(z) for k,z in v.items() if 'elapsed' not in k and k not in ('wall_seconds','seconds')}
  if isinstance(v,list):return [strip(z) for z in v]
  return v
 assert strip(rr[0])==strip(rr[1])==strip(rr[2])
out=dict(complete=True,actual_games_replayed=len(rows),all_native_go_score_argmax_complete_checks=checks,unique_history_oracles=len(cache),oracle_leaves=leaves,independent_decoder_journal_hashes=len(journal),all_non_time_equal_triples=8,seconds=time.monotonic()-start,scope='Secondobject_hookdecoder not253codec; every96actualgo score/argmax/complete/noFallback plus24legalgames and8triples. Cachedbaseimmutabilitywasliveproducerassert, notglobalcopyproof; physicalheapnotmeasured.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(out)
