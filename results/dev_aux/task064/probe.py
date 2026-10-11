"""Rejected binding transaction observation on own ephemeral Native engine."""
import hashlib,json,sys,copy
from pathlib import Path
ROOT=Path.cwd();E=ROOT/'.local_agent/pinned_bebe';sys.path.insert(0,str(E));B=Path(__file__).resolve().parent;D=json.loads((B/'DECLARATION.json').read_bytes())
from native_initial_fixture import _initial
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.ai.limits import SearchLimits
from generic_chess.session.session import GameSession
from scripts.research_record import record_value
c,n,packed=_initial();s=GameSession(c);initial=s.state;w=tuple(s._search_witnesses);zeros={t:0 for t in n.type_ids};mapping={f'{owner}:{t}':(0,)*9 for owner in (0,1) for t in n.type_ids};mapping['0:P']=(-1,-1,-1,1,1,1,0,0,0)
engine=SemanticSearchEngine(c,n,board_values=zeros,hand_values=zeros,tt_megabytes=0);capsule=engine._capsule;before=copy.deepcopy(engine.native_evaluator_values);limits=SearchLimits(max_depth=1,max_nodes=1000,max_time_seconds=1,quiescence_max_depth=0)
old=engine.search(s,limits)
try:engine.bind_evaluator(zeros,zeros,spatial_occupancy_values=mapping,evaluator_scale=0);raise AssertionError('invalid scale unexpectedly accepted')
except ValueError as e:error={'type':type(e).__name__,'message':str(e)}
after=copy.deepcopy(engine.native_evaluator_values);assert engine._capsule is capsule;same=engine.search(s,limits)
fresh=SemanticSearchEngine(c,n,board_values=after['board'],hand_values=after['hand'],spatial_occupancy_values=after['spatial_occupancy'],evaluator_scale=after['scale'],tt_megabytes=0);ref=fresh.search(s,limits)
assert old.score==same.score and old.action==same.action and old.nodes==same.nodes
assert old.score!=ref.score and before['spatial_occupancy']!=after['spatial_occupancy']
assert s.state==initial and tuple(s._search_witnesses)==w
print(json.dumps([{'depth':v.completed_depth,'qnodes':v.qnodes,'reason':v.termination_reason,'score':v.score} for v in (old,same,ref)]))
for r in (old,same,ref):assert r.completed_depth==1 and r.qnodes==0
out={'complete':True,'declaration':D,'source_hashes':{p:hashlib.sha256((E/p).read_bytes()).hexdigest() for p in ['generic_chess/native/semantic_engine.py','generic_chess/native/semantic.py','generic_chess/_native/native_module.c']},'binary_sha256':hashlib.sha256((E/'generic_chess/_native_core.cp312-win_amd64.pyd').read_bytes()).hexdigest(),'before_values':before,'after_rejected_bind_values':after,'rejection':error,'capsule_identity_preserved':True,'rows':[{'case':name,'decision':record_value(r)} for name,r in [('old_zero_profile_D1',old),('same_capsule_after_invalid_scale_rebind_D1',same),('fresh_engine_from_reported_valid_profile_D1',ref)]],'session_and_history_unchanged':True,'scope':'D1/q0/TT0 initial Western state;metadata/capsule divergence after rejection, not corrupt binary or strength claim. Inputs all Agent constructed.'}
(B/'result.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps({'scores':[old.score,same.score,ref.score],'nodes':[old.nodes,same.nodes,ref.nodes],'rejection':error,'metadata_changed':True,'capsule_preserved':True}))
