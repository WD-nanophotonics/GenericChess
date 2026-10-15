from pathlib import Path
import importlib.util,json,itertools,collections,time,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1706';start=time.monotonic();deadline=start+600;results=[];error=None
sp=importlib.util.spec_from_file_location('STOP',R/'results/dev_aux/task166/run.py');STOP=importlib.util.module_from_spec(sp);sp.loader.exec_module(STOP)
(O/'plan.json').write_text(json.dumps({'status':'FROZEN_STREAM_RULE_NO_MATE_COST_PROOF','domains':[{'width':4,'model':'task1675/rules.py'},{'width':8,'model':'task1688/rules.py'}],'stocks':'BareKingKing orsinglecurrentN/B, noPawn/R/otheractors. EnumerateALLplacements ofwhiteN/B andbothturns, blackactorcovered byexplicitcolor exchange bijection fromnonpawnmovement law.','question':'CanlegitimateinfiniteWDLDraw be recognizedbefore futile engine continuation/cycle detection, includingpromotedactor whosecurrenttype isN/B?','labels':'ProofonlyifnoCHECKMATEseed incompleteclosedstockdomain; stalemate/loopsdraw; fullmodelcurrentPawn absent so nofuturepromotions/drops/origin/historysemantics. Nooldproofapplication toPawnapresent/duplicates/twoN/B.','seconds_cap':600,'expected_seconds':90,'actual_native_go':0,'memory':'Streamingallstates, boundedcounterexamples/witnesses; nofullgraph/predarrays.'},indent=2))
try:
 for width,model in [(4,'results/dev_aux/task1675/rules.py'),(8,'results/dev_aux/task1688/rules.py')]:
  sp=importlib.util.spec_from_file_location('T',R/model);T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T);area=width*width;counts=collections.Counter();mates=[];witnesses=[];h=hashlib.sha256();whitevalid={}
  for kind in ['KONLY','N','B']:
   n=0
   for wk,bk in itertools.permutations(range(area),2):
    extras=[None] if kind=='KONLY' else [z for z in range(area) if z not in(wk,bk)]
    for z in extras:
     for side in [0,1]:
      n+=1
      if n%4096==0:STOP.stop();assert time.monotonic()<deadline
      board=['.']*area;board[wk]='K';board[bk]='k'
      if z is not None:board[z]=kind
      s=tuple(board+[side])
      if not T.valid(s):continue
      counts[kind+'_valid']+=1;ll=T.moves(s);ch=T.attacked(s,T.king(s,side),1-side);h.update((''.join(board)+str(side)).encode());h.update(';'.join(u for u,t in ll).encode());counts[kind+'_moves']+=len(ll);counts[kind+'_checked']+=ch;counts[kind+'_stale']+=not ll and not ch
      if not ll and ch:
       counts[kind+'_CHECKMATE']+=1
       if len(mates)<16:mates.append({'state':s,'kind':kind,'fen':T.fen(s)})
      for u,t in ll:
       assert sum(p in('K','k') for p in t[:area])==2 and T.valid(t);pieces=[p for p in t[:area] if p not in('.','K','k')];assert pieces==([kind] if z is not None and kind in t else [])
       counts[kind+'_capture_to_bare']+=not pieces and z is not None
      if len(witnesses)<16 and ch:witnesses.append({'state':s,'kind':kind,'fen':T.fen(s),'moves':[u for u,t in ll]})
   print('COMPLETE_STOCK',width,kind,dict(counts),round(time.monotonic()-start,2),flush=True)
  assert not mates;result={'width':width,'model':model,'model_sha256':hashlib.sha256((R/model).read_bytes()).hexdigest(),'counts':dict(counts),'mate_seeds':mates,'frontier_digest':h.hexdigest(),'checked_witnesses':witnesses,'closure':'Allformalchildren preserve2kings andsamecurrentN/B actor orcapturetoKONLY; noPawn anywhere/nofuturepromotion. Blackactorbycolor-swap nonpawnmovement/attackbijection, sidechanges1-side.','status':'PROVED_NO_MATE_IN_COMPLETE_CLOSED_SINGLE_N_B_OR_BARE_STOCK','proof_scope':'CurrentstockatmostONEtotalN/B, nottwoN/B/duplicates/Pawnapresent/otherboards/droporigin/historyvariant.'};results.append(result);(O/f'proof{width}.json').write_text(json.dumps(result,indent=2))
except BaseException as ex:error=type(ex).__name__+':'+str(ex)
out={'status':'PASS_COMPLETE_BOTH_STOCK_PROOFS' if error is None else 'PARTIAL_PRESERVED','error':error,'actual_native_go':0,'seconds':time.monotonic()-start,'results':results};(O/'result.json').write_text(json.dumps(out,indent=2));print('FINAL_PROOF',out['status'],out['seconds'])
