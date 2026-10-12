"""Frozen exposed-root diagnostic; no learning and no engine-prior causal claim."""
import json,hashlib,time,sys,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task133';O.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def freeze():
 p=R/'results/dev_aux/task127/games.json';data=json.loads(p.read_bytes())['calls'];profiles=json.loads((R/'results/dev_aux/task127/declaration.json').read_bytes())['profiles'];roots=[]
 for op in (6,24):
  for oi in range(8):
   for color in (True,False):
    pair=[next(c for c in data if c['context']['name']==f'p{op}-a{arm}-o{oi}-c{int(color)}') for arm in ('unit','learned')]
    u,l=[c['result'] for c in pair];assert u['opening']==l['opening']
    d=next((i for i,(a,b) in enumerate(zip(u['actions'],l['actions'])) if a!=b),None)
    if d is None:continue
    b=chess.Board()
    for text in u['opening']+u['actions'][:d]:b.push_uci(text)
    assert b.turn==color and not b.is_game_over(claim_draw=False)
    roots.append(dict(id=f'p{op}-o{oi}-c{int(color)}',source_names=[c['context']['name'] for c in pair],first_divergence=d,history=[m.uci() for m in b.move_stack],fen=b.fen(),old_choices=[u['actions'][d],l['actions'][d]],agent_color=color))
    if len(roots)==8:break
   if len(roots)==8:break
  if len(roots)==8:break
 assert len(roots)==8
 declaration=dict(task_id='133',question='Do mature choices and shallow candidate-material/random-objective preferences disagree on exposed first-divergence roots?',source_sha256=sha(p),profiles=profiles,roots=roots,selection='first8 by existing regime/opening/color order; no result ranking; exposed diagnosis only',searches=16,search='fresh profile process; configure/reset everyroot; fullhistory go nodes1024; actualnodes recorded',exact='all legal root actions and all legal replies,2ply terminal priority ±1000000/draw0; unweighted random replies and worst replies; root side perspective',scope='Depth/horizon/opponent mismatch diagnosis only, NOT controlledSEE ablation, NOT fairsearchspeed or humanvaluelearning',deadline_seconds=300,cost='16 search plus complete2ply enumeration expected <30seconds, overhead reported',decision='Disagreement chooses targeted horizon/objective control before build; agreement does not exonerate priors')
 if (O/'declaration.json').exists():raise FileExistsError('frozen declaration')
 (O/'declaration.json').write_text(json.dumps(declaration,indent=2),encoding='utf-8')
 print(json.dumps(dict(frozen_roots=len(roots),history_lengths=[len(x['history']) for x in roots])))
def vector(b,color):return {chess.piece_symbol(t).upper():len(b.pieces(t,color))-len(b.pieces(t,not color)) for t in range(1,6)}
def leaf(b,color,w):
 result=b.outcome(claim_draw=False);v=vector(b,color)
 term=None if result is None else dict(kind=result.termination.name,winner=result.winner)
 raw=sum(w[k]*v[k] for k in v)
 value=raw if result is None else (0 if result.winner is None else (1000000 if result.winner==color else -1000000))
 return dict(vector=v,raw_material=raw,value=value,terminal=term)
def execute():
 sys.path.insert(0,str(R/'results/dev_aux/task109'));import adapter
 d=json.loads((O/'declaration.json').read_bytes());started=time.monotonic();deadline=started+d['deadline_seconds'];stop=lambda:adapter.stop_check(R);stop()
 binary,digest,_=adapter.validated_entry(R/'.local_agent/material-selfplay/fairy-material.exe',R/'results/dev_aux/task120/qualification.json')
 if (O/'result.json').exists():raise FileExistsError('frozen execution')
 output=[];counts=dict(searches=0,root_actions=0,replies=0);complete=False
 try:
  for arm,w in d['profiles'].items():
   e=adapter.UCI(binary,R,deadline,stop);e.backend='QUALIFIED_FAIRY_MATERIAL:'+digest
   try:
    for root in d['roots']:
     adapter.guard(deadline,stop);probes=adapter.configure(e,w,O/'variant.ini',deadline,stop)
     b=chess.Board()
     for m in root['history']:b.push_uci(m)
     assert b.fen()==root['fen'];color=b.turn
     mature,meta=adapter.search(e,b.copy(stack=True),deadline,stop);counts['searches']+=1
     rows=[]
     for move in sorted(b.legal_moves,key=lambda m:m.uci()):
      adapter.guard(deadline,stop);b.push(move);counts['root_actions']+=1
      replies=[]
      if b.is_game_over(claim_draw=False):replies=[dict(move=None,**leaf(b,color,w))]
      else:
       for reply in sorted(b.legal_moves,key=lambda m:m.uci()):
        b.push(reply);replies.append(dict(move=reply.uci(),**leaf(b,color,w)));b.pop();counts['replies']+=1
      rows.append(dict(move=move.uci(),replies=replies,worst=min(x['value'] for x in replies),mean=sum(x['value'] for x in replies)/len(replies),unit_mean=sum(sum(x['vector'].values()) if x['terminal'] is None else (0 if x['terminal']['winner'] is None else (1000000 if x['terminal']['winner']==color else -1000000)) for x in replies)/len(replies)))
      b.pop()
     assert b.fen()==root['fen']
     chosen=next(x for x in rows if x['move']==mature.uci())
     maxima={k:max(x[k] for x in rows) for k in ('worst','mean','unit_mean')}
     output.append(dict(arm=arm,root_id=root['id'],mature=mature.uci(),metadata=meta,probes=probes,root_material=leaf(b,color,w),actions=rows,best_sets={k:[x['move'] for x in rows if x[k]==v] for k,v in maxima.items()},chosen_shallow={k:chosen[k] for k in maxima},regret={k:maxima[k]-chosen[k] for k in maxima},old_choice=root['old_choices'][0 if arm=='unit' else 1]))
   finally:e.close()
  complete=True
 except BaseException as ex:error=type(ex).__name__+': '+str(ex)
 out=dict(complete=complete,counts=counts,wall_seconds=time.monotonic()-started,declaration_sha256=sha(O/'declaration.json'),binary_sha256=digest,rows=output)
 if not complete:out['error']=error
 adapter.atomic_json(O/'result.json',out)
 summary=dict(complete=complete,counts=counts,wall_seconds=out['wall_seconds'],rows=[{k:x[k] for k in ('arm','root_id','mature','old_choice','best_sets','regret')} for x in output])
 adapter.atomic_json(O/'summary.json',summary);print(json.dumps(summary,indent=2));return 0 if complete else 3
if __name__=='__main__':
 if sys.argv[1:]==['freeze']:freeze()
 else:sys.exit(execute())
