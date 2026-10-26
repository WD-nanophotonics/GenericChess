"""Guard against false fixed-work/profile conclusions and leaked instrumentation."""
import json
from pathlib import Path
import pytest
from scripts.verify_leaper_cost_profile import analyze
from scripts.leaper_push_span_trial import observe_push
from generic_chess.core.search_runtime import SearchPathRuntime

def packet(tmp_path):
 for slot,arm in enumerate(('before','profile','after')):
  row={'slot':slot,'case_id':'frozen-rule-h2','depth':6,'arm':arm,'choose_seconds':1.0 if arm!='profile' else 4.0,
       'decision':{'completed_depth':6,'action':{'literal':'a'},'score':3,'nodes':10,'qnodes':20,'tt_hits':2,'pvs_researches':1,'elapsed_seconds':1.0+slot}}
  (tmp_path/f'return-{slot:03}.json').write_text(json.dumps(row))
 profile={'total_tt':2.0,'functions':[{'file':'generic_chess/core/search_runtime.py','line':1,'name':'push','exclusive_instrumented_cpu':2.0,'inclusive_instrumented_cpu':2.0}]}
 (tmp_path/'profile-001.json').write_text(json.dumps(profile))
 return tmp_path

def test_timing_disturbance_is_not_work_mismatch(tmp_path):
 result=analyze(packet(tmp_path))
 assert result['summary']['6']['eligible']==1
 assert result['summary']['6']['median_profile_wall_ratio']==4.0

def test_changed_tt_work_cannot_be_called_matched(tmp_path):
 folder=packet(tmp_path);p=folder/'return-001.json';r=json.loads(p.read_text());r['decision']['tt_hits']+=1;p.write_text(json.dumps(r))
 result=analyze(folder)
 assert result['summary']['6']['eligible']==0
 assert result['summary']['6']['parity_failures']==1

def test_partial_profile_does_not_prove_complete_work(tmp_path):
 folder=packet(tmp_path);p=folder/'return-001.json';r=json.loads(p.read_text());r['decision']['completed_depth']=5;p.write_text(json.dumps(r))
 result=analyze(folder)
 assert result['summary']['6']['eligible']==0
 assert result['summary']['6']['incomplete']==1

def test_exclusive_conservation_failure_is_rejected(tmp_path):
 folder=packet(tmp_path);p=folder/'profile-001.json';r=json.loads(p.read_text());r['total_tt']=3.0;p.write_text(json.dumps(r))
 with pytest.raises(AssertionError,match='conservation'):analyze(folder)

def test_observer_restores_method_and_propagates_baseexception(monkeypatch):
 class Sentinel(BaseException):pass
 def original(self,*args,**kwargs):raise Sentinel('unchanged')
 monkeypatch.setattr(SearchPathRuntime,'_push_impl',original)
 with pytest.raises(Sentinel):
  with observe_push(True) as metrics:
   SearchPathRuntime._push_impl(object())
 assert SearchPathRuntime._push_impl is original
 assert metrics['calls']==1 and metrics['exceptions']==1 and metrics['active']==0


def test_public_project_relative_paths_keep_category(tmp_path):
 result=analyze(packet(tmp_path))
 assert result['groups'][0]['category_exclusive_instrumented_cpu']['core']==2.0

def test_duplicate_arm_is_not_silently_overwritten(tmp_path):
 folder=packet(tmp_path);r=json.loads((folder/'return-001.json').read_text());r['slot']=3;(folder/'return-003.json').write_text(json.dumps(r))
 with pytest.raises(AssertionError,match='duplicate'):analyze(folder)

def test_literal_reader_rejects_unbound_history_before_replay(tmp_path):
 from scripts.verify_leaper_profile_replay import replay_saved
 (tmp_path/'source.json').write_text(json.dumps({'input_original_sha256':'wrong'}))
 inputs=tmp_path/'inputs.json';inputs.write_text(json.dumps({'rows':[]}))
 with pytest.raises(AssertionError,match='frozen full-input hash'):replay_saved(tmp_path,inputs)

def test_exact_original_archive_round_trip_and_tamper(tmp_path):
 import gzip,hashlib
 from scripts.verify_leaper_cost_profile import saved_returns
 body=json.dumps({'slot':0,'decision':{'nodes':5}})+'\r\n'
 entry={'sha256':hashlib.sha256(body.encode()).hexdigest(),'original_utf8':body}
 archive=tmp_path/'returns.json.gz';archive.write_bytes(gzip.compress(json.dumps({'0':entry}).encode()))
 assert saved_returns(tmp_path)[0]['decision']['nodes']==5
 entry['original_utf8']=body.replace('5','6')
 archive.write_bytes(gzip.compress(json.dumps({'0':entry}).encode()))
 with pytest.raises(AssertionError,match='original hash'):saved_returns(tmp_path)
