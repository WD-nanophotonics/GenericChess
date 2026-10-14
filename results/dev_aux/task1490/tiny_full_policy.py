from pathlib import Path
import json,time,os,hashlib,importlib.util,collections
R=Path.cwd();O=R/'results/dev_aux/task1507';O.mkdir(exist_ok=False);study=json.loads((R/'results/dev_aux/task1503/study.json').read_bytes());sel=json.loads((R/'results/dev_aux/task1505/selection.json').read_bytes());price=next(x['selected'] for x in sel['rows'] if x['budget']==16);prices=sorted({720,price})
G=R/study['source_graph'];states=list(map(tuple,json.loads((G/'states.json').read_bytes())));edges=[json.loads(x)['moves'] for x in (G/'edges.jsonl').read_text().splitlines()];n=sum(len(x)>1 for x in edges);expected=n*len(prices)
plan={'question':'Does single-choice exactWDL learning improve entire fixed mature policy against a perfect best response?','nodes':16,'prices':prices,'selected_from_TRAIN':price,'primary':'Selected1728 minusfixed720 under full-policy best-response WDL on frozen64DEV fullorbits; secondary TRAIN/descriptive allgraph. Never refit prices on this new objective.','policy':'Fresh cold single-state search, no history draws; sole legal action mechanical no query. For each candidatecolor fix own graph edges to cached mature choices; opponent retains ALL legal defenses. Exact retrograde WDL of resulting graph, cycles draw. Genuine complete-game policy result, no finite cap/material reward/perfect continuation assumption.','expected_go':expected,'expected_seconds':round(expected*26.5/3072),'max_seconds':3300,'state_count':len(states),'scope':'Small3x3 KRN only, not humanChess/Shogi; leaves/native and other heuristics unchanged. Bounded cached policy extraction avoids playing extremely long games; all partials retained.'};(O/'plan.json').write_text(json.dumps(plan,indent=2));print(plan,flush=True)
sp=importlib.util.spec_from_file_location('T',R/study['rules']);T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
sp=importlib.util.spec_from_file_location('P',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P);start=time.monotonic();deadline=start+plan['max_seconds'];closed=0;error=None;exits=[];acks=[]
with (O/'choices.jsonl').open('x',encoding='utf8') as f:
 try:
  for price in prices:
   e=P.M.start(R/study['binary'],3,deadline,P.stop)
   try:
    for name,val in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(R/study['variant_ini'])),('UCI_Variant','aux_tiny')]:
     e.send(f'setoption name {name} value {val}');rr=e.ready()
     if name=='UCI_Variant':assert any(x.startswith('info string variant aux_tiny files 3 ranks 3 ') for x in rr);acks.append(rr)
    e.send(f'devauxleafrnbp {price} 720 720 720');rr=e.ready();assert f'info string DEV_AUX leafRNBP {price} 720 720 720 nativeP 720 nativeR 720 nativeN 720 nativeB 720 captureP 720 captureR 720 captureN 720 captureB 720' in rr;acks.append(rr)
    for sid,ll in enumerate(edges):
     if P.stop():raise InterruptedError('actual user stop')
     if time.monotonic()>deadline:raise TimeoutError('single original3300second fuse')
     if len(ll)<=1:
      move,child=ll[0] if ll else (None,None);row={'state_id':sid,'leafR':price,'move':move,'child_id':child,'basis':'SOLE_LEGAL_ACTION' if ll else 'ACTUAL_TERMINAL','new_go':0}
     else:
      e.send('ucinewgame');e.ready();position='position fen '+T.fen(states[sid]);e.send(position);command='go nodes 16';e.send(command);lines=e.until(lambda x:x.startswith('bestmove '));move=lines[-1].split()[1];e.ready();child=dict(ll)[move];row={'state_id':sid,'leafR':price,'move':move,'child_id':child,'basis':'ACTUAL_COLD_MATURE_SEARCH','position':position,'command':command,'uci_info':lines[:-1],'backend':e.backend,'new_go':1};closed+=1
     f.write(json.dumps(row)+'\n');f.flush()
     if sid%1000==0:os.fsync(f.fileno());print('POLICY',price,sid,'go',closed,'secs',round(time.monotonic()-start,1),flush=True)
   finally:e.close();exits.append(e.p.poll())
 except BaseException as ex:error=type(ex).__name__+':'+str(ex)
 finally:f.flush();os.fsync(f.fileno())
out={'status':'COMPLETE' if error is None and closed==expected else 'PARTIAL_PRESERVED','error':error,'actual_go':closed,'expected_go':expected,'seconds':time.monotonic()-start,'exit_codes':exits,'all_owned_engines_closed':all(x==0 for x in exits),'acks':acks,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scope':plan['policy']};(O/'result.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='acks'})
