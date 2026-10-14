from pathlib import Path
import json,time,os,hashlib,importlib.util,sys
R=Path.cwd();plan=json.loads((R/'results/dev_aux/task1535/study.json').read_bytes());phase=sys.argv[1];O=R/sys.argv[2];O.mkdir(exist_ok=False)
assert json.loads((R/'results/dev_aux/task1533/result.json').read_bytes())['status'].startswith('PASS') and json.loads((R/'results/dev_aux/task1534/result.json').read_bytes())['status']=='PASS_ALL_NATIVE_3X4_LEGAL'
sp=importlib.util.spec_from_file_location('T',R/plan['rules']);T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
sp=importlib.util.spec_from_file_location('P',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P)
G=R/plan['source_graph']
for name,digest in plan['input_hashes'].items():assert hashlib.sha256((G/name).read_bytes()).hexdigest()==digest
states=list(map(tuple,json.loads((G/'states.json').read_bytes())));values=json.loads((G/'values.json').read_bytes())['value'];edges={x['id']:dict(x['moves']) for x in map(json.loads,(G/'edges.jsonl').read_text().splitlines())}
families=[x for x in plan['families'] if x['phase']==phase]
assert phase=='TRANSFER';prices=plan['R_grid']
expected=len(families)*2*len(prices)*len(plan['nodes']);assert len(families)==64
start=time.monotonic();deadline=start+plan['max_seconds'];closed=0;error=None;exits=[];acks=[]
assert hashlib.sha256((R/plan['binary']).read_bytes()).hexdigest()==plan['binary_sha256'];ini=R/plan['variant_ini']
with (O/'choices.jsonl').open('x',encoding='utf8') as f:
 try:
  for budget in plan['nodes']:
   for price in prices:
    e=P.M.start(R/plan['binary'],3,deadline,P.stop)
    try:
     for name,val in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(ini)),('UCI_Variant','aux_tiny')]:
      e.send(f'setoption name {name} value {val}');rr=e.ready()
      if name=='UCI_Variant':assert any(l.startswith('info string variant aux_tiny files 3 ranks 4 ') for l in rr);acks.append(rr)
     e.send(f'devauxleafrnbp {price} 720 720 720');rr=e.ready();want=f'info string DEV_AUX leafRNBP {price} 720 720 720 nativeP 720 nativeR 720 nativeN 720 nativeB 720 captureP 720 captureR 720 captureN 720 captureB 720';assert want in rr;acks.append(rr)
     for family in families:
      for sid in family['state_ids']:
       if P.stop():raise InterruptedError('user stop')
       if time.monotonic()>deadline:raise TimeoutError('single declared fuse')
       e.send('ucinewgame');e.ready();position='position fen '+T.fen(states[sid]);e.send(position);command=f'go nodes {budget}';e.send(command);lines=e.until(lambda x:x.startswith('bestmove '));move=lines[-1].split()[1];e.ready();assert move in edges[sid];child=edges[sid][move];label=-values[child];optimal=values[sid];assert label<=optimal
       row={'phase':phase,'family':family['family'],'state_id':sid,'node_budget':budget,'leafR':price,'leafN':720,'nativeR':720,'move':move,'child_id':child,'root_WDL':optimal,'chosen_WDL':label,'regret':optimal-label,'position':position,'command':command,'uci_info':lines[:-1],'backend':e.backend};f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno());closed+=1
    finally:e.close();exits.append(e.p.poll())
    print('CLOSED_PROFILE',phase,budget,price,closed,flush=True)
 except BaseException as ex:error=type(ex).__name__+':'+str(ex)
out={'status':'COMPLETE' if error is None and closed==expected else 'PARTIAL_PRESERVED','error':error,'actual_go':closed,'expected_go':expected,'seconds':time.monotonic()-start,'exit_codes':exits,'all_owned_engines_closed':all(x==0 for x in exits),'acks':acks,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'study_sha256':hashlib.sha256((R/'results/dev_aux/task1535/study.json').read_bytes()).hexdigest(),'scope':plan['objective']};(O/'result.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='acks'})
