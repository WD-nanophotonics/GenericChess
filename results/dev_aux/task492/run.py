import json,hashlib,time,sys,os,re,collections
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task492';assert not (O/'result.json').exists();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));sys.path.insert(0,str(R/'results/dev_aux/task381'));import adapter as A;import run as G;import audit as V
source=R/'results/dev_aux/task478/declaration.json';old=json.loads(source.read_text(encoding='utf-8'));exes={'baseHand':R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe','full':R/'.local_agent/yaneura30/yaneura-material1-full-capture-futility.exe','mode0':R/'.local_agent/yaneura31/yaneura-material1-first-futility.exe','mode1':R/'.local_agent/yaneura31/yaneura-material1-first-futility.exe'};d=dict(question='At firstaffectedbranch underactualsamecontext, does arithmetic intervention reach recursion, SEE orbestValue only?',source_inputs_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),roots=old['roots'],initial_profiles=old['initial_profiles'],node_budgets=old['node_budgets'],arms=list(exes),executable_hashes={k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in exes.items()},expected_go=128,cost='64mode0/1shortquerycontrol +64unchangedbinaryqualification, expected<20s/180totalfuse; no games/fit/extra worker orfee',scope='Samefrozen478fullroot/history inputs (exposed), node1024/8192, twoinitials/eightroots. Pairfirsteffect bycompleteSFEN including side/move/phase/depth/alpha/beta/ply and old/full/best, notloglineindex. Firststate-effect includesqaccumulator, mode1 samevalue intervention as482. Windowreturnbucket only, stoppedunknown neverexact proof. No任意internalstackrestore or alltree/harm proof.');(O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8');t0=time.perf_counter();qs={};acks=[];pv=0
for arm,exe in exes.items():
 A.EXE=exe;os.environ['DEV_AUX_CAPTURE_FUTILITY_MODE']='1' if arm=='mode1' else '0';out=[]
 with (O/(arm+'_queries.jsonl')).open('w',encoding='utf-8') as journal:
  for nodes in d['node_budgets']:
   for profile in d['initial_profiles']:
    for root in d['roots']:
     G.stop();assert time.perf_counter()-t0<180;e=A.Engine(profile['weights'],journal);acks.append(dict(arm=arm,weights=e.w,prices=e.prices,nodes=nodes,root_seed=root['seed']))
     try:q=e.search(root['initial_sfen'],root['history'],nodes);pv+=V.query(q);out.append(q)
     finally:e.close()
 qs[arm]=out
sem=lambda q:{k:([ ' '.join(re.sub(r'\b(?:time|nps) \d+','',l).split()) for l in v if not l.startswith('info string auxfirst ')] if k=='lines' else v) for k,v in q.items() if k!='seconds'}
mismatches=[]
for orig,mode in [('baseHand','mode0'),('full','mode1')]:
 for i,(a,b) in enumerate(zip(qs[orig],qs[mode])):
  if sem(a)!=sem(b):mismatches.append(dict(arm=orig,index=i,ordinary=a,instrumented=b))
pattern=re.compile(r'^info string auxfirst event phase (main|q) alpha (-?\d+) beta (-?\d+) old (-?\d+) full (-?\d+) best (-?\d+) mode ([01]) ply (\d+) depth (-?\d+) move (\S+) sfen (.+)$');retpat=re.compile(r'^info string auxfirst return value (-?\d+) alpha (-?\d+) beta (-?\d+) stopped ([01])$')
def first(q):
 events=[];outcomes=[];returns=[]
 for line in q['lines']:
  if line.startswith('info string auxfirst event '):
   m=pattern.fullmatch(line);assert m,line;phase,*v=m.groups();alpha,beta,oldval,fullval,best,mode,ply,depth=map(int,v[:8]);u,sfen=v[8:];events.append(dict(phase=phase,alpha=alpha,beta=beta,old=oldval,full=fullval,best=best,mode=mode,ply=ply,depth=depth,move=u,sfen=sfen,threshold_crossing=(oldval<=alpha)!=(fullval<=alpha),accumulator_only=(oldval<=alpha)==(fullval<=alpha),outcomes=outcomes,returns=returns))
  elif line.startswith('info string auxfirst outcome '):outcomes.append(line.rsplit(' ',1)[1])
  elif line.startswith('info string auxfirst return '):
   m=retpat.fullmatch(line);assert m;value,alpha,beta,stopped=map(int,m.groups());returns.append(dict(value=value,alpha=alpha,beta=beta,stopped=bool(stopped),window_bucket='UNKNOWN_STOPPED' if stopped else 'upper_fail_low' if value<=alpha else 'lower_fail_high' if value>=beta else 'inside_window_selective'))
 assert len(events)<=1
 return events[0] if events else None
pairs=[]
for i,(a,b) in enumerate(zip(qs['mode0'],qs['mode1'])):
 x,y=first(a),first(b);keys=['phase','alpha','beta','old','full','best','ply','depth','move','sfen'];matched=(x is None and y is None) or (x is not None and y is not None and all(x[k]==y[k] for k in keys));pairs.append(dict(index=i,nodes=a['nodes_limit'],weights=a['weights'],same_first_context=matched,base=x,full=y,scope='Onlymatchedfirstcontext localmechanism; latersearchdivergence notlinepaired'))
summary=dict(first_context_matches=sum(x['same_first_context'] for x in pairs),no_effect_pairs=sum(x['base'] is None and x['full'] is None for x in pairs),threshold_first_effect_pairs=sum(x['same_first_context'] and x['base'] is not None and x['base']['threshold_crossing'] for x in pairs),accumulator_only_first_pairs=sum(x['same_first_context'] and x['base'] is not None and x['base']['accumulator_only'] for x in pairs),full_recursion_pairs=sum(x['same_first_context'] and x['full'] is not None and 'recursive_enter' in x['full']['outcomes'] for x in pairs),full_SEE_prune_pairs=sum(x['same_first_context'] and x['full'] is not None and 'SEE_prune' in x['full']['outcomes'] for x in pairs),full_futility_prune_pairs=sum(x['same_first_context'] and x['full'] is not None and 'futility_prune' in x['full']['outcomes'] for x in pairs),unresolved_full_pairs=sum(x['full'] is not None and not x['full']['outcomes'] for x in pairs),changed_bestmoves=sum(a['bestmove']!=b['bestmove'] for a,b in zip(qs['baseHand'],qs['full'])))
out=dict(status='PASS_QUALIFIED_CONTROL' if not mismatches else 'FAIL_QUALIFICATION_SAVED',actual_go=sum(len(v) for v in qs.values()),PV_move_checks=pv,new_games=0,pairs=pairs,summary=summary,price_acks=acks,mismatches=mismatches,seconds=time.perf_counter()-t0,scope=d['scope']);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ['pairs','price_acks','mismatches']},ensure_ascii=True));assert not mismatches,'actualinstrumentationresponse mismatch saved'
