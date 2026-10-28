"""Actual installed-Native and Core runtime contract check on new saved games.
No Player/search, new game or Native build. Timings are accounting,not speedup.
"""
import argparse,json,time,hashlib
from pathlib import Path
from collections import Counter
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.identity import position_identity_key
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.verify_published_new_family_games import load,record_hash,diagnostic_action
from scripts.research_record import record_value,write_record
import generic_chess.native as native

def state_wire(runtime):
 def stable(identity):
  return identity if isinstance(identity,str) else position_identity_key(identity.position,runtime.compiled)
 return dict(position=record_value(runtime.position),ply_count=runtime.ply_count,terminal_status=record_value(runtime.terminal_status),repetition_counts=[list(x) for x in sorted((stable(k),v) for k,v in runtime.repetition_counts.items())],history=[dict(position_key=stable(x.identity),actor=x.actor,action_signature=x.action_signature,gave_check=x.gave_check) for x in runtime.history])
def key(runtime):return runtime.search_key()
def verify(source,output,max_seconds=900,max_failed_pushes=100000):
 start=time.perf_counter();roots={r['id']:r for r in load(source/'inputs.json.gz')['rows']};games=load(source/'results/games.json.gz');counts=Counter();cache=set();records=[];complete=True
 module=native._module();binary=Path(module.__file__);binary_info=dict(name=binary.name,bytes=binary.stat().st_size,sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
 published_binary=load(source/'results/loaded-binary.json.gz')
 for g in games:
  root=roots[g['case_id']];c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(root['RuleSet']));provider=NativeSemanticLegalityProvider.try_create(c,strict=True);assert provider is not None and not provider.transient_imports;engine=semantic_engine_for(c);s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])))
  for q in g['queries']:
   h=record_hash(s);assert h==q['record_before_sha256'];action=diagnostic_action(q['decision']['action'],root['fingerprint'])
   if h not in cache:
    if time.perf_counter()-start>=max_seconds or counts['failed_pushes']>=max_failed_pushes:complete=False;break
    cache.add(h);legal=set(s.legal_actions());assert provider.supports_position(s.state.position,s.state.ply_count)
    assert {a for a,_ in provider(s.state.position,s.state.ply_count)}==legal;counts['Native_frontiers']+=1
    for side in (0,1):assert provider.in_check(s.state.position,side)==engine.in_check(s.state.position,side);counts['Native_check_queries']+=1
    assert provider.has_legal_action(s.state.position)==bool(legal);counts['Native_availability_queries']+=1
    variants=[('Core',{}),('Native',dict(legal_binding_provider=provider,availability_provider=provider.has_legal_action,check_provider=provider.in_check))]
    for label,kwargs in variants:
     r=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses,**kwargs);r.legal_actions();before=state_wire(r);before_key=key(r);calls=[]
     def count():calls.append(1)
     r.push(action,checkpoint=count);after=state_wire(r);r.pop();assert state_wire(r)==before and key(r)==before_key;r.assert_balanced();counts[label+'_successful_pushes']+=1
     # The real next Session state is separately compared after both variants.
     expected=GameSession.replay(c,s.to_record());expected.submit(action);assert after==record_value(expected.state)
     # Visit every checkpoint of this saved transition with a prefilled parent frontier.
     for at in range(1,len(calls)+1):
      if counts['failed_pushes']>=max_failed_pushes or time.perf_counter()-start>=max_seconds:complete=False;break
      seen=[0]
      class InjectedCancel(RuntimeError):pass
      def interrupt():
       seen[0]+=1
       if seen[0]==at:raise InjectedCancel('fixed_checkpoint_cancel')
      try:r.push(action,checkpoint=interrupt)
      except InjectedCancel:pass
      else:raise AssertionError('expected checkpoint not visited')
      assert state_wire(r)==before and key(r)==before_key and r.depth==0
      r.assert_balanced();counts['failed_pushes']+=1;counts[label+'_cancel_points']+=1
     if not complete:break
    records.append(dict(game=g['game_id'],qid=q['query_id'],record=h,ply=q['ply_before'],complete=complete))
    if not complete:break
   s.submit(action)
  write_record(output,dict(status='RUNNING' if complete else 'PARTIAL',counts=dict(counts),distinct_histories=len(cache),last_game=g['game_id'],wall=time.perf_counter()-start,binary=binary_info,published_binary=published_binary,records=records))
  if not complete:break
 result=dict(status='COMPLETE' if complete else 'PARTIAL',counts=dict(counts),distinct_histories=len(cache),wall=time.perf_counter()-start,limits=dict(seconds=max_seconds,failed_pushes=max_failed_pushes),binary=binary_info,published_binary=published_binary,historical_binary_identical=binary_info['sha256']==published_binary['sha256'],records=records,scope='Fresh semantic compatibility execution on installed older ABI,not historical binary/search replay or measured acceleration. Every warm-parent-frontier transition checkpoint was attempted within caps; initial legal-generation cancellation is outside this sample; unfinished remainsUNKNOWN.')
 write_record(output,result);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(a.source,a.output);print(json.dumps({k:v for k,v in r.items() if k!='records'},indent=2))
