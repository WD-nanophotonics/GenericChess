from pathlib import Path
import json,importlib.util,time,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1511';O.mkdir(exist_ok=False);G=R/'results/dev_aux/task1495';states=list(map(tuple,json.loads((G/'states.json').read_bytes())));v=json.loads((G/'values.json').read_bytes())['value'];edges={x['id']:dict(x['moves']) for x in map(json.loads,(G/'edges.jsonl').read_text().splitlines())};old=[json.loads(x) for x in (R/'results/dev_aux/task1504/choices.jsonl').read_text().splitlines()];targets=[]
for x in old:
 if x['state_id'] in [46128,51320] and any('score mate -2 nodes 17' in l for l in x['uci_info']):targets.append(x)
assert len(targets)==2
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1490/tiny_rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
sp=importlib.util.spec_from_file_location('P',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P);rows=[];start=time.monotonic();e=P.M.start(R/'.local_agent/leaf-rnbp-46/fairy-leaf-rnb.exe',3,start+120,P.stop)
try:
 for name,val in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(R/'results/dev_aux/task1497/variant.ini')),('UCI_Variant','aux_tiny')]:e.send(f'setoption name {name} value {val}');e.ready()
 for x in targets:
  sid=x['state_id'];price=x['leafR'];e.send(f'devauxleafrnbp {price} 720 720 720');ack=e.ready();assert f'info string DEV_AUX leafRNBP {price} 720 720 720 nativeP 720 nativeR 720 nativeN 720 nativeB 720 captureP 720 captureR 720 captureN 720 captureB 720' in ack
  for command in ['go nodes 16','go nodes 64','go nodes 256','go nodes 4096','go depth 6']:
   e.send('ucinewgame');e.ready();e.send('position fen '+T.fen(states[sid]));e.send(command);raw=e.until(lambda l:l.startswith('bestmove '));e.ready();move=raw[-1].split()[1];assert move in edges[sid];row={'state_id':sid,'fen':T.fen(states[sid]),'leafR':price,'command':command,'raw':raw,'move':move,'exact_rootWDL':v[sid],'chosen_childWDL':-v[edges[sid][move]],'draw_preserving_choices':[u for u,j in edges[sid].items() if -v[j]==0],'source_row':x};rows.append(row)
finally:e.close()
out={'status':'OBSERVED_NEGATIVE_MATE_REPORT_VS_EXACT_DRAW_REPRO','rows':rows,'actual_go':len(rows),'exit_code':e.p.poll(),'seconds':time.monotonic()-start,'scope':'Native negative mate announcements at tiny budget are not oracle certificates; root true DRAW proven by complete graph. Distinguish reported score/bounds/interrupt from actual returned move. No engine/main product change or using PV as label.'};(O/'result.json').write_text(json.dumps(out,indent=2));print([{k:v for k,v in x.items() if k not in ['raw','source_row']}|{'scorelines':[l for l in x['raw'] if ' score ' in l][-1:]} for x in rows])
