"""Specific frozen qualification contract controls on actual saved returns."""
from pathlib import Path
from copy import deepcopy
import gzip,json,hashlib
import pytest
from scripts.verify_published_new_family_games import verify_qualification_packet
FIX=Path(__file__).parents[1]/'fixtures'/'new_family_qualification_contract.json.gz'
@pytest.fixture(scope='module')
def packet():return json.loads(gzip.decompress(FIX.read_bytes()))
def changed_raw(p,slot,fn):
 q=p['quals'][slot];row=p['returns'][q['query_id']];raw=json.loads(row['original_utf8']);fn(raw);q['decision']=deepcopy(raw['decision']);text=json.dumps(raw,indent=2)+'\n';h=hashlib.sha256(text.encode()).hexdigest();row.update(original_utf8=text,sha256=h)
 if slot<19:p['frozen']['plan']['prior_return_hashes'][q['query_id']+'.json']=h
 return p
def test_actual_amended_packet_passes_and_keeps_original_failed(packet):
 r=verify_qualification_packet(**packet);assert (r['count'],r['reused'],r['new'],r['pv_plies'])==(24,19,5,44);assert r['original_registration'].startswith('FAILED')
@pytest.mark.parametrize('mutation',['pair_score','fast_win_score','whole_cap','service_contract','success_gate','planned_games','root_schedule','arm_schedule','node_limit','remaining_budget','deterministic','availability_decline','original_failure','extra_reuse','seat_bool','ply_bool','on_int','added_source','missing_caller_source','invalid_source_hash','plan_input_binding','failed_return'])
def test_semantic_contract_changes_reject_even_with_coherent_return_hashes(packet,mutation):
 p=deepcopy(packet)
 if mutation=='pair_score':changed_raw(p,1,lambda r:r['decision'].__setitem__('score',r['decision']['score']+1))
 elif mutation=='fast_win_score':
  for i in (22,23):changed_raw(p,i,lambda r:r['decision'].__setitem__('score',r['decision']['score']-10))
 elif mutation=='whole_cap':p['frozen']['plan']['cap_minutes']+=1
 elif mutation=='service_contract':p['frozen']['plan']['service_seconds']=2
 elif mutation=='success_gate':p['frozen']['plan']['success']='weakened outcome requirement'
 elif mutation=='planned_games':p['frozen']['plan']['planned_games']=22
 elif mutation=='root_schedule':p['frozen']['plan']['root_ids'][:2]=reversed(p['frozen']['plan']['root_ids'][:2])
 elif mutation=='arm_schedule':p['quals'][0],p['quals'][1]=p['quals'][1],p['quals'][0];p['quals'][0]['slot']=0;p['quals'][1]['slot']=1
 elif mutation=='node_limit':changed_raw(p,20,lambda r:r['limits'].__setitem__('max_nodes',500001))
 elif mutation=='remaining_budget':changed_raw(p,20,lambda r:r['limits'].__setitem__('max_time_seconds',4))
 elif mutation=='deterministic':changed_raw(p,20,lambda r:r['limits'].__setitem__('deterministic',False))
 elif mutation=='availability_decline':changed_raw(p,20,lambda r:r['provider_delta']['availability'].__setitem__('declines',1))
 elif mutation=='added_source':p['frozen']['plan']['sources']['new_unregistered_runtime.py']='0'*64
 elif mutation=='missing_caller_source':p['frozen']['plan']['sources'].pop('scripts/leaper_new_family_pvs.py')
 elif mutation=='invalid_source_hash':p['frozen']['plan']['sources']['scripts/leaper_new_family_pvs.py']=None
 elif mutation=='plan_input_binding':
  p['frozen']['plan']['input_sha256']=p['old']['plan']['input_sha256']='0'*64
 elif mutation=='failed_return':changed_raw(p,20,lambda r:r.__setitem__('status','FAILED'))
 elif mutation=='seat_bool':changed_raw(p,20,lambda r:r.__setitem__('seat',False))
 elif mutation=='ply_bool':changed_raw(p,20,lambda r:r.__setitem__('ply_before',False))
 elif mutation=='on_int':changed_raw(p,20,lambda r:r.__setitem__('on',int(r['on'])))
 elif mutation=='original_failure':p['quals'][18]['original_status']='RETURNED'
 elif mutation=='extra_reuse':p['frozen']['plan']['prior_return_hashes']['q0019.json']='0'*64
 with pytest.raises((AssertionError,ValueError)):verify_qualification_packet(**p)
