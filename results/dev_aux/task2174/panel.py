"""FullSession interface/cost panel, no training or mainline integration."""
from pathlib import Path
from dataclasses import replace,asdict
from copy import copy
from collections import Counter
import json,time,sys,importlib.util,hashlib
sys.path.insert(0,str(Path('tests').resolve()));sys.path.insert(0,str(Path('tests/development').resolve()))
from test_generic_session_win_proof import session,claim
from test_generic_session_proof_mechanisms import played,layout
from conftest import T,king_type,make_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.pieces import Piece
from generic_chess.core.movement import LeapAtom,RayAtom
from generic_chess.rules.schema import RuleConsecutiveActionAdjudication
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from generic_chess.rules.serialization import serialize_ruleset
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_fixtures import krk_ruleset
from scripts.generic_proof_player import ProofMaterialPlayer
from scripts.generic_session_win_proof import execute,SessionChoice
from scripts.generic_win_proof import _same_state
from results.dev_aux.task2148.normal import SessionCompleteMaterialSearch
from results.dev_aux.task2174.matched import MatchedCoreMaterialSearch
from results.dev_aux.task2142.test_semantics import capture_session
from results.dev_aux.task2139.receipt import choice_value
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2174')
def fixtures():
 out=[('winning_claim',session(claim(0,'WIN'))),('restart_claim',session(claim(0,'RESTART'),k=0,b=15,r=2))]
 rook=T('R',*(RayAtom(d)for d in((1,0),(-1,0),(0,1),(0,-1))));pawn=T('P',LeapAtom((0,1)),is_promotable=True,targets=('R',));rs=make_ruleset(4,[king_type(),rook,pawn],lines=['...k','P...','..K.','....'],auto_promotion=True);out.append(('forced_promotion',GameSession(compile_ruleset_for_execution(rs))))
 out.append(('capture_drop',capture_session()))
 rs=layout(krk_ruleset(4),[(1,Piece(0,'K','K')),(7,Piece(1,'K','K')),(12,Piece(0,'R','R'))]);rs=replace(rs,pass_enabled=True,consecutive_action_adjudications=(RuleConsecutiveActionAdjudication('pass',1,'DRAW'),));out.append(('pass_draw',played(rs,['a4a3'])))
 rs=layout(replace(krk_ruleset(4),repetition_policy='continuous_check_loss'),[(0,Piece(0,'K','K')),(15,Piece(1,'K','K')),(2,Piece(0,'R','R'))]);out.append(('played_perpetual',played(rs,['c1d1','d4c4','d1c1','c4d4','c1d1','d4c4','d1c1'])))
 spec=importlib.util.spec_from_file_location('auxfixture2168',Path('tests/product/test_runtime_aux_identity.py'));mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);out.append(('semantic_aux',GameSession(mod._compiled(initial=0,value=1))))
 return out

def material(pos,target):return float(sum((1 if p.owner==target else-1)for p in pos.board if p is not None and p.current_type_id!='K'))
def run():
 if(OUT/'started.json').exists():raise RuntimeError('one180cap neverrestart')
 p=json.loads((OUT/'plan.json').read_text(encoding='utf-8'));start=time.perf_counter();deadline=start+180;stop=EvidenceStopReader(Path.cwd());(OUT/'started.json').write_text(json.dumps(dict(source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cap=180)),encoding='utf-8');rows=[];status='COMPLETE';roots=fixtures()
 def cancel():stop();return time.perf_counter()>=deadline
 with(OUT/'queries.jsonl').open('x',encoding='utf-8')as f:
  for index,(name,s)in enumerate(roots):
   (OUT/(name+'-record.json')).write_text(serialize_game_record(s.to_record()),encoding='utf-8')
   # These existing fixtures keep compiled rules authoritative; frozen result fingerprint and complete root record bind each query.
   for depth in p['depths']:
    for nodes in p['node_caps']:
     off=(index+depth)%4;walls=p['wall_envelopes'][off:]+p['wall_envelopes'][:off]
     for wall in walls:
      arms=p['arms']if(index+depth+nodes)%2 else list(reversed(p['arms']))
      for arm in arms:
       if cancel():status='CAP_PARTIAL';break
       before=s.to_record();state=s.state;result=s.result;begin=time.perf_counter();kwargs=dict(max_nodes=nodes,seconds=1. if wall=='NODE_ONLY'else wall,cancel=cancel)
       if wall=='NODE_ONLY':kwargs['_clock']=lambda:0.
       if arm=='BOARD_CORE_NORMAL':
        d=ProofMaterialPlayer(s.compiled,material,proof_enabled=False,max_depth=depth).choose(s.state,**kwargs);choice=None if d.action is None else SessionChoice('ACTION',action=d.action);terminal_leaves=None;transitions=None
       else:
        d=(MatchedCoreMaterialSearch if arm=='MATCHED_CORE_NORMAL'else SessionCompleteMaterialSearch)(s.compiled,material,max_depth=depth).choose(s,**kwargs);choice=d.choice;terminal_leaves=d.terminal_leaves;transitions=d.session_transitions
       elapsed=time.perf_counter()-begin;assert _same_state(s.state,state)and _same_state(s.to_record(),before)and s.result==result
       actual=None
       if choice is not None:
        child=GameSession.replay(s.compiled,before);execute(child,choice);replayed=GameSession.replay(s.compiled,child.to_record());assert _same_state(replayed.state,child.state)and replayed.result==child.result
        actual=dict(status=child.result.status.value,winner=child.result.winner,declaration_outcome=child.result.declaration_outcome,record=json.loads(serialize_game_record(child.to_record())))
       row=dict(fixture=name,ruleset_fingerprint=s.compiled.ruleset_fingerprint,depth=depth,node_cap=nodes,wall=wall,arm=arm,choice=choice_value(choice),nodes=d.nodes,reported_seconds=d.seconds,measured_seconds=elapsed,completed_depth=d.completed_depth,exit_cause=d.exit_cause,source=d.source,score=getattr(d,'score',None),session_transitions=transitions,terminal_leaves=terminal_leaves,actual=actual);rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
      if status!='COMPLETE':break
     if status!='COMPLETE':break
    if status!='COMPLETE':break
   if status!='COMPLETE':break
   print(json.dumps(dict(fixture=name,queries=len(rows),seconds=time.perf_counter()-start)),flush=True)
 matched_checks=0
 for name,s in roots:
  if s.compiled.declarations:continue
  for depth in p['depths']:
   for nodes in p['node_caps']:
    pair=[r for r in rows if r['fixture']==name and r['depth']==depth and r['node_cap']==nodes and r['wall']=='NODE_ONLY'and r['arm']in('MATCHED_CORE_NORMAL','FULL_SESSION_NORMAL')]
    if len(pair)==2:
     a,b=pair;assert all(a[k]==b[k]for k in('choice','nodes','completed_depth','score','exit_cause'));matched_checks+=1
 groups={}
 for arm in p['arms']:
  for wall in p['wall_envelopes']:
   rr=[r for r in rows if r['arm']==arm and r['wall']==wall];groups[arm+'/'+str(wall)]=dict(queries=len(rr),completed=sum(r['completed_depth']==r['depth']for r in rr),nochoice=sum(r['choice']is None for r in rr),declarations=sum(r['choice']is not None and r['choice']['kind']=='DECLARATION'for r in rr),nodes=sum(r['nodes']for r in rr),measured_seconds=sum(r['measured_seconds']for r in rr),exit_causes=dict(Counter(r['exit_cause']for r in rr)))
 out=dict(matched_declfree_node_pairs=matched_checks,status=status,queries=len(rows),seconds=time.perf_counter()-start,groups=groups,scope=p['scope']);(OUT/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out),flush=True)
if __name__=='__main__':run()
