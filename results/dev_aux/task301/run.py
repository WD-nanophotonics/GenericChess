import json,time,sys,hashlib,importlib.util
from pathlib import Path
R=Path.cwd();S=R/'.local_agent/pinned/f1ea1d38';sys.path.insert(0,str(S));sys.path.insert(1,str(R));O=R/'results/dev_aux/task301';O.mkdir(exist_ok=False)
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from scripts.audit_lichess_complete_children import uci
from scripts.research_record import record_value
import generic_chess._native_core as native
base=json.loads((R/'results/dev_aux/task281/result.json').read_bytes());roots=json.loads((R/'results/dev_aux/task258/declaration.json').read_bytes())['roots'];prof=json.loads((R/'results/dev_aux/task267/declaration.json').read_bytes())['profiles'];W={k:prof[k] for k in ('unit','semantic','s703-base','s704-base','s705-base')};build=json.loads((R/'results/dev_aux/task279/build.json').read_bytes());D=dict(task_id='301',question='Are selectedPVleafmaterialvectors validlocaloneunit score sensitivities for completeD3 aroundunit/semantic/oldrandomprices?',roots=roots,profiles=W,variants=['base']+[k+s for k in 'PNBRQ' for s in ('-','+')],depth=3,per_call_seconds=3,tt_megabytes=1,root_window_pruning=True,repetition_limit=100000,binary_sha256=build['binary_sha256'],source_commit=build['source_commit'],historical_base='16exactqualified281basequeries reusedwithsourceSHA;4semanticbase+200oneunitperturbations new=204 actualqueries. No games/training/humanchoice. Analytic302eps1/100sensitivities referfinite258tree only, not fractionalsupportedNative.',whole_fuse_seconds=300,scope='Localgradient/tiecondition audit before anyTDLeaf hypothesis; selectedPVleafcan be a branch slope atnondifferentiableminimax ties, not unconditionalsearch derivative. PurefixedD3/coldTT1 publicrebuild, no selectivePVgradient ordeployment.',source_hashes={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'results/dev_aux/task281/result.json',R/'results/dev_aux/task258/tree.json',R/'results/dev_aux/task267/declaration.json']})
(O/'declaration.json').write_text(json.dumps(D,indent=2),encoding='utf-8');assert Path(native.__file__).resolve().is_relative_to(S.resolve()) and hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest()==D['binary_sha256']
def load(name,path):
 sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
P=load('p',R/'results/dev_aux/task166/run.py');C=load('codec',R/'results/dev_aux/task253/codec.py');P.stop();start=time.monotonic();c=compile_semantic_ruleset(build_western_chess_ruleset());n=compile_native_semantic_rules(c);cases=[];out=dict(complete=False,cases=cases,actual_new_queries=0,historical_base_queries=0)
def save():out['seconds']=time.monotonic()-start;P.A.atomic_json(O/'result.json',out)
try:
 for f in roots:
  ss=GameSession(c)
  for t in f['history']:ss.submit(next(a for a in ss.legal_actions() if uci(a)==t))
  before=ss.state,ss.history,ss.result,ss._search_witnesses
  for name,w in W.items():
   recs={};case=dict(root=f['id'],profile=name,weights=w,variants=recs);cases.append(case)
   for var in D['variants']:
    ww=w.copy()
    if var!='base':ww[var[0]]+=1 if var[1]=='+' else -1
    prior=next((z for z in base['rows'] if z['root']==f['id'] and z['profile']==name),None) if var=='base' else None
    if prior is not None:
     recs[var]=dict(weights=ww,action=prior['action'],result=C.encode(prior['result']),historical=True,source='281');out['historical_base_queries']+=1
    else:
     P.A.guard(start+300,P.stop);e=SemanticSearchEngine(c,n,board_values=ww,hand_values={k:0 for k in n.type_ids},dynamic_values=None,tt_megabytes=1);ts=time.monotonic();v=e.search(ss,SearchLimits(max_depth=3,max_nodes=None,max_time_seconds=3,quiescence_max_depth=0),root_window_pruning=True);assert before==(ss.state,ss.history,ss.result,ss._search_witnesses);recs[var]=dict(weights=ww,action=uci(v.action),result=C.encode(record_value(v)),historical=False,wall_seconds=time.monotonic()-ts);out['actual_new_queries']+=1;save();assert v.completed_depth==3 and not v.used_fallback
   print(f['id'],name,out['actual_new_queries'],round(time.monotonic()-start,3),flush=True)
 out['complete']=True;save();print('COMPLETE',out['actual_new_queries'],out['historical_base_queries'],out['seconds'])
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise