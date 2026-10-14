from pathlib import Path
import json,importlib.util,time,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1515';O.mkdir(exist_ok=False);w=json.loads((R/'results/dev_aux/task1514/result.json').read_bytes());needed={(x['price'],x['candidatecolor'],i) for x in w['witnesses'] for i in x['cycle_state_ids'][:-1]};states=list(map(tuple,json.loads((R/'results/dev_aux/task1495/states.json').read_bytes())));expected={(x['leafR'],x['state_id']):x for x in w['cached_own_choice_rows']}
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1490/tiny_rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
sp=importlib.util.spec_from_file_location('P',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P);start=time.monotonic();e=P.M.start(R/'.local_agent/leaf-rnbp-46/fairy-leaf-rnb.exe',3,start+120,P.stop);rows=[]
try:
 for name,val in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(R/'results/dev_aux/task1497/variant.ini')),('UCI_Variant','aux_tiny')]:e.send(f'setoption name {name} value {val}');e.ready()
 for price,color,sid in sorted(needed):
  if states[sid][6]!=color:continue
  e.send(f'devauxleafrnbp {price} 720 720 720');ack=e.ready()
  for repeat in range(2):
   e.send('ucinewgame');e.ready();e.send('position fen '+T.fen(states[sid]));e.send('go nodes 16');raw=e.until(lambda l:l.startswith('bestmove '));e.ready();move=raw[-1].split()[1];assert move==expected[price,sid]['move'];rows.append({'price':price,'color':color,'state_id':sid,'repeat':repeat,'raw':raw,'move':move,'actual_cached_match':True})
finally:e.close()
out={'status':'PASS_ACTUAL_COLD_CYCLE_CHOICE_REPLAY','actual_go':len(rows),'rows':rows,'exit_code':e.p.poll(),'seconds':time.monotonic()-start,'scope':'Real samecold16node choices on each own cycle state, repeated twice; every repeat newucinewgame/ready. Not warmstatepolicy proof or cycles caused solely by prices.'};(O/'result.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='rows'})
