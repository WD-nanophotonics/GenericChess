import json,time,sys,hashlib,os
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task593';D=O/'declaration.json';d=json.loads(D.read_bytes())
for n in [360,364,381,509,547]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
from warm_adapter import ControlledEngine
sys.path.insert(0,str(O));from controller_curriculum import native_game
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];t0=time.monotonic();deadline=t0+600;roots=[];missing=[];setuprows=[];setupacks=[];Q=R/'results/dev_aux/task594';Q.mkdir(exist_ok=True);assert not(Q/'games.jsonl').exists()
with (Q/'queries.jsonl').open('w') as qj,(Q/'games.jsonl').open('w') as gj:
 e=ControlledEngine(d['setup_weights'],qj,'warm_game');setupacks.append(dict(weights=e.w,prices=e.prices));(Q/'price_acks.json').write_text(json.dumps(setupacks,indent=2),encoding='utf-8')
 try:
  for fi,seed in enumerate(d['input_policy']['seeds']):
   for c in [0,1]:
    G.stop();b=A.shogi.Board();f=dict(seed=seed,index=fi,phase='setup',initial_sfen=b.sfen(),history=[],expected_sfen=b.sfen());e.begin_game();g=native_game(e,None,e.w,f,c,None,dict(cap=48,nodes=1024,seed_base=d['setup_seed_base']),deadline);g.update(stage='setup',source_family=seed,setup_color=c);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());line=len(setuprows)+1;setuprows.append(dict(family=seed,unit_color=c,termination=g['termination'],plies=len(g['actions']),go=len(g['queries']),source=dict(file='results/dev_aux/task594/games.jsonl',line=line)))
    if g['termination']['kind']!='checkmate':missing.append(dict(family=seed,unit_color=c,reason='no_mate_within48',termination=g['termination'],plies=len(g['actions'])));continue
    for offset in d['input_policy']['offsets']:
     n=len(g['actions'])-offset
     if n<0:missing.append(dict(family=seed,unit_color=c,offset=offset,reason='mate_before_offset'));continue
     hist=[a['move'] for a in g['actions'][:n]];expected=g['actions'][n-1]['after_sfen'] if n else f['initial_sfen'];root=dict(index=len(roots),seed=seed,phase='curriculum_probe',initial_sfen=f['initial_sfen'],history=hist,expected_sfen=expected,source_family=seed,setup_color=c,offset=offset,setup_source=dict(file='results/dev_aux/task594/games.jsonl',line=line),setup_mate_winner=g['termination']['winner']);pb,keys,checks,movers=G.full_root(root);assert pb.sfen()==expected and G.terminal(pb,keys,checks,movers) is None;roots.append(root)
    print('setup',seed,c,g['termination'],len(g['actions']),len(roots),round(time.monotonic()-t0,1),flush=True)
 finally:e.close()
(Q/'result.json').write_text(json.dumps(dict(status='COMPLETE',rows=setuprows,actual_games=len(setuprows),actual_go=sum(x['go'] for x in setuprows),price_acks=setupacks,seconds=time.monotonic()-t0,scope=d['scope']),indent=2),encoding='utf-8');freeze=dict(declaration_sha256=hashlib.sha256(D.read_bytes()).hexdigest(),before_any_price_probe=True,roots=roots,unavailable=missing,successful_setup_mates=sum(x['termination']['kind']=='checkmate' for x in setuprows),independent_families=len(d['input_policy']['seeds']),eligible_family_count=len({f['source_family'] for f in roots}),seconds=time.monotonic()-t0);(O/'roots_frozen.json').write_text(json.dumps(freeze,indent=2),encoding='utf-8')

print('ROOTS_ONLY_COMPLETE',len(setuprows),sum(x['go'] for x in setuprows),len(roots),round(time.monotonic()-t0,3),flush=True)
