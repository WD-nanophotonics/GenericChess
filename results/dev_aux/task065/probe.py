"""Four actual compact payload/cache lineage calls, synthetic constant model."""
import copy,hashlib,json,sys
from pathlib import Path
ROOT=Path.cwd();E=ROOT/'.local_agent/pinned_bebe';sys.path.insert(0,str(E));B=Path(__file__).resolve().parent;D=json.loads((B/'DECLARATION.json').read_bytes())
from native_initial_fixture import _initial
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.native.compiler import build_semantic_compile_payload
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from scripts.research_record import record_value
c,n,packed=_initial();s=GameSession(c);state=s.state;w=tuple(s._search_witnesses);payload,report=build_semantic_compile_payload(c);dimension=2*len(n.type_ids)*payload['board_size']**2+2+5
for a in payload['aux_slots']:dimension+=(2 if a['value_kind']==0 else 6) if a['scope']==1 else (1 if a['value_kind']==0 else 3)
model={'input_mean':[0.]*dimension,'input_scale':[1.]*dimension,'hidden_weights':[[0.]*dimension for _ in range(16)],'hidden_bias':[0.]*16,'output_weights':[0.]*16,'output_bias':0.,'target_scale':1.,'width':16,'hand_type_indices':[0],'perspective':'owner0'}
zeros={t:0 for t in n.type_ids};p=SemanticSearchEngine(c,n,board_values=zeros,hand_values=zeros,compact_values=model,tt_megabytes=1,evaluator_scale=1);capsule=p._capsule;limits=SearchLimits(max_depth=2,max_nodes=4096,max_time_seconds=2,quiescence_max_depth=0);rows=[]
def run(name,engine):
 before=engine.tt_info();v=engine.search(s,limits);after=engine.tt_info();assert v.completed_depth==2 and v.termination_reason=='completed' and v.qnodes==0
 rows.append(dict(case=name,decision=record_value(v),tt_before=before,tt_after=after,values=copy.deepcopy(engine.native_evaluator_values)));return v
old=run(D['cases'][0],p);assert p.tt_info()['occupied_entries']>0
exposed=p.native_evaluator_values['compact_nonlinear'];assert exposed is p._compact_values;exposed['output_bias']=100.;assert p._capsule is capsule
warm=run(D['cases'][1],p);assert p._capsule is capsule
p.clear_tt();cleared=run(D['cases'][2],p)
fresh=SemanticSearchEngine(c,n,board_values=zeros,hand_values=zeros,compact_values=copy.deepcopy(exposed),tt_megabytes=0,evaluator_scale=1);reference=run(D['cases'][3],fresh)
assert s.state==state and tuple(s._search_witnesses)==w
out={'complete':True,'declaration':D,'feature_dimension':dimension,'aux_slots':payload['aux_slots'],'zero_model_sha256':hashlib.sha256(json.dumps(model,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'getter_is_live_dictionary':True,'same_capsule_before_after_getter_mutation':True,'rows':rows,'warm_disagrees_with_cleared':warm.score!=cleared.score,'cleared_matches_fresh':cleared.score==reference.score,'session_history_unchanged':True,'binary_sha256':hashlib.sha256((E/'generic_chess/_native_core.cp312-win_amd64.pyd').read_bytes()).hexdigest(),'source_hashes':{x:hashlib.sha256((E/x).read_bytes()).hexdigest() for x in ['generic_chess/native/semantic_engine.py','generic_chess/_native/native_module.c']}}
(B/'result.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps({'scores':[old.score,warm.score,cleared.score,reference.score],'dimension':dimension,'warm_disagrees':out['warm_disagrees_with_cleared'],'cleared_matches_fresh':out['cleared_matches_fresh']}))
