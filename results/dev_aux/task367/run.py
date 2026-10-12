import sys,json,time,re,hashlib
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));import adapter as A;import run as G
O=R/'results/dev_aux/task367';O.mkdir(exist_ok=True);d=json.loads((R/'results/dev_aux/task364/declaration.json').read_text(encoding='utf-8'));old=[json.loads(x) for x in (R/'results/dev_aux/task364/games.jsonl').read_text(encoding='utf-8').splitlines()];(O/'declaration.json').write_text(json.dumps({'source_cases':'all16task364games, exactprice/fullroot/color/goal, cap24/cold1024 fixedunit','difference':'disableisreadykeepaliveonly, old reset retained','match':'everyactualaction, fullPV/depth/nodes/cp&bounds normalizedtiming, eval/cache/history/legal/terminal/quantity/goal; no noise-free speedup claim','old_executable_sha256':d['executable_sha256'],'new_executable_sha256':hashlib.sha256(A.EXE.read_bytes()).hexdigest()},indent=2),encoding='utf-8')
def info(lines):return [re.sub(r' (nps|time) \d+','',l) for l in lines if l.startswith('info depth ') or l.startswith('bestmove ')]
rows=[];checks=[];t0=time.monotonic()
with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
 eu=A.Engine(d['profiles'][0]['weights'],qj)
 try:
  for p in d['profiles']:
   ec=A.Engine(p['weights'],qj)
   try:
    for g in old:
     if g['weights']!=p['weights']:continue
     n=G.game(ec,eu,p['weights'],g['root'],g['color'],gj,deadline=t0+600);rows.append(n)
     for k in ['weights','root','color','actions','termination','final_sfen','raw_quantity','goal']:assert n[k]==g[k],k
     assert len(n['queries'])==len(g['queries'])
     mismatches=[]
     for i,(a,b) in enumerate(zip(n['queries'],g['queries'])):
      assert a['state']==b['state'] and a['bestmove']==b['bestmove']
      if info(a['lines'])!=info(b['lines']):mismatches.append(i)
     assert not mismatches,(g['root']['index'],g['color'],mismatches)
     checks.append({'weights':p['weights'],'root_index':g['root']['index'],'color':g['color'],'old_seconds':g['seconds'],'new_seconds':n['seconds'],'query_count':len(n['queries']),'all_actions_eval_PV_depth_node_score_match':True});print(p['name'],g['root']['index'],g['color'],round(g['seconds'],3),round(n['seconds'],3),flush=True)
   finally:ec.close()
 finally:eu.close()
result={'status':'PASS','seconds':time.monotonic()-t0,'games':len(rows),'go':sum(len(g['queries']) for g in rows),'old_game_seconds':sum(g['seconds'] for g in old),'new_game_seconds':sum(g['seconds'] for g in rows),'checks':checks};(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print({k:v for k,v in result.items() if k!='checks'})