from pathlib import Path
import json,time,datetime,importlib.util,hashlib,collections
R=Path.cwd();O=R/'results/dev_aux/task1613';O.mkdir(exist_ok=False);plan=json.loads((R/'results/dev_aux/task1612/study.json').read_bytes());start=time.monotonic();deadline=start+plan['seconds'];G=R/'results/dev_aux/task1583';states=list(map(tuple,json.loads((G/'states.json').read_bytes())));ix={s:i for i,s in enumerate(states)};oracle=json.loads((G/'values.json').read_bytes())['value'];sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1581/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T);sp=importlib.util.spec_from_file_location('P',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P);base=json.loads((R/'results/dev_aux/task1586/study.json').read_bytes());e=None;queries=0;error=None;exits=[];train=[];dev=[];selected=None
(O/'start.json').write_text(json.dumps({'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'session_id':json.loads((R/'.local_agent/session.json').read_bytes())['id'],'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'seconds_cap':240,'max_go':6144,'no_restart':True},indent=2))
def evaluate(price,phase):
 global queries
 rr,bb=price;e.send(f'devauxleafrnbp {rr} 720 {bb} 720');ack=e.ready();assert f'info string DEV_AUX leafRNBP {rr} 720 {bb} 720 nativeP 720 nativeR 720 nativeN 720 nativeB 720 captureP 720 captureR 720 captureN 720 captureB 720' in ack
 rows=[]
 with (O/f'R{rr}_B{bb}_{phase}_choices.jsonl').open('w') as f:
  for fam in plan['families']:
   if fam['phase']!=phase:continue
   for sid in fam['state_ids']:
    if P.stop():raise InterruptedError('userstop')
    assert time.monotonic()<deadline and queries<plan['max_go'];s=states[sid];ll=dict(T.moves(s));assert len(ll)>1;e.send('ucinewgame');e.ready();position='position fen '+T.fen(s);e.send(position)
    with (O/'go_journal.jsonl').open('a') as j:j.write(json.dumps({'R':rr,'B':bb,'phase':phase,'sid':sid,'event':'SEND_INTENT','elapsed':time.monotonic()-start})+'\n')
    e.send('go nodes 64');queries+=1
    with (O/'go_journal.jsonl').open('a') as j:j.write(json.dumps({'R':rr,'B':bb,'phase':phase,'sid':sid,'event':'SENT','elapsed':time.monotonic()-start})+'\n')
    raw=e.until(lambda z:z.startswith('bestmove '));move=raw[-1].split()[1];e.ready();child=ix[ll[move]]
    for line in raw[:-1]:
     ss=line.split()
     if 'pv' in ss:
      q=s
      for u in ss[ss.index('pv')+1:]:q=dict(T.moves(q))[u]
    x={'R':rr,'B':bb,'N':720,'phase':phase,'family':fam['family'],'sid':sid,'child':child,'move':move,'position':position,'command':'go nodes 64','uci_info':raw[:-1],'onechoice_perfect_future_WDL':-oracle[child]};f.write(json.dumps(x)+'\n');f.flush();rows.append([fam['family'],x['onechoice_perfect_future_WDL']])
 out={'R':rr,'B':bb,'phase':phase,'mean':sum(v for fam,v in rows)/len(rows),'root_values':rows,'WDL':dict(collections.Counter(v for fam,v in rows))};(O/f'R{rr}_B{bb}_{phase}_result.json').write_text(json.dumps(out,indent=2));return out
try:
 e=P.M.start(R/base['binary'],3,deadline,P.stop);assert hashlib.sha256((R/base['binary']).read_bytes()).hexdigest()==base['binary_sha256']
 for name,val in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(R/base['variant_ini'])),('UCI_Variant','aux_tiny')]:
  e.send(f'setoption name {name} value {val}');ack=e.ready()
  if name=='UCI_Variant':assert any(z.startswith('info string variant aux_tiny files 3 ranks 4 ') for z in ack)
 for phase in ['TRAIN1','TRAIN2','TRAIN3']:
  for rr in plan['R_grid']:
   for bb in plan['B_grid']:train.append(evaluate((rr,bb),phase))
 selected={}
 for phase in ['TRAIN1','TRAIN2','TRAIN3']:
  best=min([x for x in train if x['phase']==phase],key=lambda x:(-x['mean'],x['R'],x['B']));selected[phase]=[best['R'],best['B']]
 pooled={}
 for rr in plan['R_grid']:
  for bb in plan['B_grid']:pooled[rr,bb]=sum(x['mean'] for x in train if x['R']==rr and x['B']==bb)/3
 selected['POOLED']=list(min(pooled,key=lambda p:(-pooled[p],p)))
 (O/'selection.json').write_text(json.dumps({'TRAIN_selected':selected,'selector':plan['selector'],'pooled_TRAIN_means':{str(k):v for k,v in pooled.items()}},indent=2))
 for price in sorted({tuple(p) for p in selected.values()}|{(720,720)}):dev.append(evaluate(price,'DEV'))
except BaseException as ex:error=type(ex).__name__+':'+str(ex)
finally:
 if e is not None:e.close();exits.append(e.p.poll())
out={'status':'COMPLETE' if error is None else 'PARTIAL_OR_FAILURE_PRESERVED','error':error,'actual_go':queries,'seconds':time.monotonic()-start,'exit_codes':exits,'all_owned_engines_closed':bool(exits) and all(x==0 for x in exits),'TRAIN_profiles':len(train),'DEV_profiles':len(dev),'selected':selected,'DEV':dev,'scope':plan['objective']+'; threeTRAINsamples/POOLEDfixedselectors, commonDEV. Fullpolicyvalidationseparate; noDEVselection/humanfit.'};(O/'result.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='DEV'})
