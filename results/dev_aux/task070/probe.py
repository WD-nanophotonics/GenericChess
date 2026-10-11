import copy,hashlib,json,sys
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'.local_agent/pinned_bebe'));B=Path(__file__).resolve().parent
from native_initial_fixture import _initial
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from scripts.research_record import record_value
c,n,_=_initial();s=GameSession(c);state=s.state;w=tuple(s._search_witnesses);zeros={t:0 for t in n.type_ids};model=json.loads((R/'results/dev_aux/task065/result.json').read_bytes())['rows'][0]['values']['compact_nonlinear'];feature=tuple(n.type_ids).index('P')*64+24
cp=LearnableMaterialCheckpoint(ruleset_fingerprint=c.ruleset_fingerprint,board_weights=zeros,hand_weights=zeros,compact_nonlinear=model);boundid=cp.checkpoint_id
p=SemanticSearchEngine(c,n,board_values=zeros,hand_values=zeros,ordering_checkpoint=cp,tt_megabytes=0,ordering_max_ply=0);old=p._capsule;limits=SearchLimits(max_depth=1,max_nodes=1000,max_time_seconds=2,quiescence_max_depth=0);rows=[]
def run(name,engine):
 v=engine.search(s,limits);assert v.completed_depth==1 and v.termination_reason=='completed' and v.learned_move_ordering
 rows.append({'case':name,'decision':record_value(v),'current_checkpoint_ID':cp.checkpoint_id,'bound_checkpoint_ID':engine.ordering_checkpoint_id,'same_capsule':engine._capsule is old,'parsed_hidden_weight':engine._ordering_compact_values['hidden_weights'][0][feature]});return v
v0=run('old_cached',p);assert v0.ordering_evaluations>0
cp.compact_nonlinear['hidden_weights'][0][feature]=1.;cp.compact_nonlinear['output_weights'][0]=1000.;assert p._ordering_compact_values['hidden_weights'][0][feature]==1. and cp.checkpoint_id!=boundid
v1=run('mutated_nested_warm',p);p.clear_tt();v2=run('mutated_nested_after_clear_tt',p)
fresh=SemanticSearchEngine(c,n,board_values=zeros,hand_values=zeros,ordering_checkpoint=cp,tt_megabytes=0,ordering_cache_enabled=False,ordering_max_ply=0);v3=run('fresh_mutated_cache_off',fresh)
assert s.state==state and tuple(s._search_witnesses)==w
out={'complete':True,'feature_index':feature,'rows':rows,'first_order_changed_after_fresh':v2.root_iteration_first_actions!=v3.root_iteration_first_actions,'warm_cachehits':v1.ordering_cache_hits,'clear_tt_cachehits':v2.ordering_cache_hits,'fresh_cachehits':v3.ordering_cache_hits,'history_unchanged':True,'binary_sha256':hashlib.sha256((R/'.local_agent/pinned_bebe/generic_chess/_native_core.cp312-win_amd64.pyd').read_bytes()).hexdigest(),'scope':'Actual D1 ordering and cache path;first traversal sequence, not worse leaf choice/strength. Public checkpoint content IDchanges on mutation,engine bound ID doesnot.'};(B/'result.json').write_bytes((json.dumps(out,separators=(',',':'))+'\n').encode());print(json.dumps({k:v for k,v in out.items() if k!='rows'}));print(json.dumps([{'case':r['case'],'first':r['decision']['root_iteration_first_actions'],'score':r['decision']['score'],'hits':r['decision']['ordering_cache_hits'],'evals':r['decision']['ordering_evaluations']} for r in rows]))
