from pathlib import Path
import json,urllib.request,urllib.parse,time,chess,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1000';O.mkdir(exist_ok=False);w=json.loads((R/'results/dev_aux/task999/result.json').read_bytes())['witnesses'];rr={r['seed']:r for r in json.loads((R/'results/dev_aux/task991/roots.json').read_bytes())['roots']};cases=[]
for x in w:
 for a in x['arms']:
  key=(x['seed'],a['move'])
  if key not in [(r['seed'],r['move']) for r in cases]:cases.append(dict(seed=x['seed'],move=a['move'],expected_actor_wdl=a['label']))
assert len(cases)<=16;(O/'plan.json').write_text(json.dumps(dict(status='FROZEN_BEFORE_CHILD_API_READ',cases=cases,max_requests=len(cases),fuse_seconds=180,question='Independentchildquery validatesparentmove labelperspective and halfmovecounter',no_resend=True),indent=2),encoding='utf-8');start=time.monotonic();rows=[];values={'win':1,'loss':-1,'draw':0,'cursed-win':0,'blessed-loss':0}
with (O/'child_responses.jsonl').open('x',encoding='utf-8') as f:
 for c in cases:
  b=chess.Board(rr[c['seed']]['fen']);move=chess.Move.from_uci(c['move']);captured=b.piece_at(move.to_square);actor=b.turn;b.push(move);url='https://tablebase.lichess.ovh/standard?'+urllib.parse.urlencode({'fen':b.fen()})
  try:
   with urllib.request.urlopen(url,timeout=15) as response:raw=response.read(2000000);z=json.loads(raw)
   value=-values[z['category']];assert value==c['expected_actor_wdl'];assert sorted(m['uci'] for m in z['moves'])==sorted(m.uci() for m in b.legal_moves)
   row=dict(**c,child_fen=b.fen(),captured=captured.symbol() if captured else None,actor=actor,childcategory=z['category'],value=value,raw_utf8=raw.decode(),sha256=hashlib.sha256(raw).hexdigest(),pass_label=True)
  except Exception as ex:row=dict(**c,error=type(ex).__name__+': '+str(ex))
  f.write(json.dumps(row)+'\n');f.flush();rows.append({k:v for k,v in row.items() if k!='raw_utf8'});print(c['seed'],c['move'],row.get('childcategory'),row.get('error'),flush=True)
(O/'result.json').write_text(json.dumps(dict(status='ALL_CHILD_LABELS_PASS' if all(r.get('pass_label') for r in rows) else 'LABEL_CHECK_FAILED',rows=rows,seconds=time.monotonic()-start,actual_requests=len(rows),new_go=0,scope='DifferentAPIquerysameoracleprovider; notindependentretrograderebuild. Alloriginalrootmetadata/H50 conserved'),indent=2),encoding='utf-8')
