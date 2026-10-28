"""Real saved-game corruption and finite-strategy boundary controls, no Player."""
from copy import deepcopy
import gzip,json,hashlib
from pathlib import Path
import pytest
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from scripts.verify_published_new_family_games import verify_game
from scripts.leaper_truth_compatibility import bind_context,verify_bound_tree
from scripts.analyze_new_family_evidence import fold
FIX=Path(__file__).parents[1]/'fixtures'
@pytest.fixture(scope='module')
def packet():return json.loads(gzip.decompress((FIX/'new_family_saved_games.json.gz').read_bytes()))
def compiled(packet,g):return compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(packet['roots'][g['case_id']]['RuleSet']))
def rebind_raw(g,rs,index=0):
 q=g['queries'][index];d={k:v for k,v in q.items() if k not in ('pv_legal','root_unchanged','record_after_sha256')};text=json.dumps(d,indent=2)+'\n';rs[q['query_id']]={'original_utf8':text,'sha256':hashlib.sha256(text.encode()).hexdigest()}
@pytest.mark.parametrize('index',[0,1])
def test_real_terminal_games_replay(packet,index):
 g=packet['games'][index];r=verify_game(g,packet['roots'][g['case_id']],packet['returns'],compiled(packet,g));assert r['terminal']=={'status':'checkmate','winner':0}
 assert len(r['queries'])==(17 if index==0 else 1)
@pytest.mark.parametrize('mutation',['seat_bool','clock','before_history','winner_bool','winner_other','terminal_draw','nonfinite_wall','negative_cpu','overbudget_packing','policy','fallback','unbalanced','false_validation','extra_validation','raw_hash','wrong_pattern','PV_first','after_history'])
def test_corrupt_real_return_or_history_rejected(packet,mutation):
 g=deepcopy(packet['games'][0]);rs=deepcopy(packet['returns']);q=g['queries'][0];d=q['decision']
 if mutation=='seat_bool':q['seat']=bool(q['seat'])
 elif mutation=='clock':q['ply_before']+=1
 elif mutation=='before_history':q['record_before_sha256']='0'*64
 elif mutation=='winner_bool':g['Core_terminal']['winner']=False
 elif mutation=='winner_other':g['Core_terminal']['winner']=1
 elif mutation=='terminal_draw':g['Core_terminal']={'status':'max_ply','winner':None}
 elif mutation=='nonfinite_wall':q['service_wall_seconds']=float('nan')
 elif mutation=='negative_cpu':q['cpu_seconds']=-1
 elif mutation=='overbudget_packing':q['construction_packing_seconds']=2
 elif mutation=='policy':q['actual_tuning']['use_pvs']=not q['on']
 elif mutation=='fallback':d['native_legality_fallbacks']=1
 elif mutation=='unbalanced':d['runtime_depth_balanced']=False
 elif mutation=='false_validation':q['root_unchanged']=False
 elif mutation=='extra_validation':q['invented_validation']=True
 elif mutation=='wrong_pattern':d['action']['pattern_id']='not-a-rule-pattern'
 elif mutation=='PV_first':d['principal_variation'][0]['to_square']['file']=6
 elif mutation=='after_history':q['record_after_sha256']='f'*64
 rebind_raw(g,rs)
 if mutation=='extra_validation':
  # Extra postvalidation field, not a field historically returned by Player.
  raw=json.loads(rs[q['query_id']]['original_utf8']);raw.pop('invented_validation');text=json.dumps(raw);rs[q['query_id']]={'original_utf8':text,'sha256':hashlib.sha256(text.encode()).hexdigest()}
 if mutation=='raw_hash':rs[q['query_id']]['sha256']='0'*64
 with pytest.raises((AssertionError,ValueError,KeyError)):
  verify_game(g,packet['roots'][g['case_id']],rs,compiled(packet,g))
def test_empty_PV_is_not_falsely_required(packet):
 g=deepcopy(packet['games'][1]);rs=deepcopy(packet['returns']);g['queries'][0]['decision']['principal_variation']=[];rebind_raw(g,rs)
 r=verify_game(g,packet['roots'][g['case_id']],rs,compiled(packet,g));assert r['pv_plies']==0 and r['terminal']['winner']==0
@pytest.fixture(scope='module')
def certificate():return json.loads(gzip.decompress((FIX/'new_family_bound_certificate.json.gz').read_bytes()))
def test_real_nontrivial_strategy_verifies(certificate):
 e=certificate;c=bind_context(e['rule'],e['record']);r=verify_bound_tree(c,e['nodes'],e['bound'],direction=e['direction']);assert r['counts']['edges']>=3
@pytest.mark.parametrize('mutation',['missing_defense','unknown_leaf','wrong_leaf','wrong_action'])
def test_incomplete_or_wrong_proof_is_not_truth(certificate,mutation):
 e=deepcopy(certificate);c=bind_context(e['rule'],e['record']);nodes=e['nodes']
 if mutation=='missing_defense':
  node=next(n for n in nodes if n['children'] and (n['state']['position']['side_to_move']==0)!=(e['direction']=='lower'));node['children'].pop()
 elif mutation=='unknown_leaf':
  node=next(n for n in nodes if n['children']);node['children']=[]
 elif mutation=='wrong_leaf':
  node=next(n for n in nodes if not n['children']);node['state']['terminal_status']['winner']=1
 else:
  node=next(n for n in nodes if n['children']);node['children'][0]['action']['pattern_id']='foreign-pattern'
 with pytest.raises((ValueError,KeyError,AssertionError)):
  verify_bound_tree(c,nodes,e['bound'],direction=e['direction'])
def test_missing_actions_remain_unknown():
 nodes={'p':{'actor':0,'legal':2,'terminal':{'status':'ongoing','winner':None},'ply':0},'d':{'actor':1,'legal':0,'terminal':{'status':'max_ply','winner':None},'ply':1}}
 b,_=fold(nodes,[{'parent':'p','action':'a','child':'d'}]);assert b['p']==[0,1]
 nodes['p']['legal']=1;b,_=fold(nodes,[{'parent':'p','action':'a','child':'d'}]);assert b['p']==[0,0]
