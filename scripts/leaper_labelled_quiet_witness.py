"""Find one legal source-attributed quiet/noisy WDL contrast; no solver or Player."""
import argparse,json,time
from collections import Counter
from pathlib import Path
from scripts.qualify_leaper_quality_endpoints import source_h6,action as normalized,canon
from scripts.leaper_postexchange_source import sha,stamp,stopped
from scripts.leaper_check_extension_quality import record_interval
from scripts.research_record import record_value,write_record
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.core.search_runtime import _plain_leaper_hash_patterns
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from generic_chess.ai.alphabeta.quiescence import classify_noisy


def predicate(facts):
 noisy=[x['source_wdl'][1] for x in facts if x['noisy']]
 quiet=[x['source_wdl'][0] for x in facts if not x['noisy']]
 return bool(noisy and quiet and max(quiet)>max(noisy)),bool(not noisy and quiet and len(set(quiet))>1)


def run(plan_path,out):
 plan=json.loads(plan_path.read_bytes());assert sha(__file__)==plan['source_sha256'];assert not out.exists();out.mkdir();write_record(out/'frozen.json',plan)
 begin=stamp();tick=time.perf_counter();inputs,truth,provenance=source_h6();families={x['family']:x for x in inputs['families']};by={}
 for r in inputs['rows']:by.setdefault(r['family'],[]).append(r)
 compiled={};counts=Counter();rows=[];candidate=None;backup=None;transitions=0;halt=None;last=-1
 try:
  for idx,t in enumerate(truth['roots']):
   if stopped() or time.perf_counter()-tick>=plan['batch_seconds'] or transitions>=plan['max_Core_children']:halt='stop_or_frozen_cap';break
   last=idx;counts['visited']+=1;f=t['family_index'];r=by[f][t['root_index']]
   assert r['fingerprint']==t['fingerprint'] and r['full_record']==t['record'];rule=truth['rules'][t['fingerprint']];assert rule==families[f]['rule']
   if not t['wdl_fork']:counts['no_source_action_fork']+=1;continue
   if any(a['terminal']['winner']==0 for a in r['actions']):counts['source_immediate_win']+=1;continue
   fp=t['fingerprint']
   if fp not in compiled:
    rules=ruleset_from_dict(rule);assert compute_fingerprint(rules)==fp;c=compile_legacy_ruleset_for_semantic_execution(rules);assert _plain_leaper_hash_patterns(c) is not None;compiled[fp]=c
   c=compiled[fp];s=GameSession.replay(c,deserialize_game_record(json.dumps(t['record'])));assert s.state.position.side_to_move==0 and s.state.ply_count==0 and not s.state.terminal_status.is_terminal
   if semantic_engine_for(c).in_check(s.state.position,0):counts['in_check']+=1;continue
   legal=s.legal_actions();source={canon(normalized(x['action'])):x for x in t['action_bounds']};assert set(source)=={canon(normalized(record_value(a))) for a in legal}
   facts=[]
   for a in legal:
    if stopped() or time.perf_counter()-tick>=plan['batch_seconds'] or transitions>=plan['max_Core_children']:raise TimeoutError('incomplete_actual_action_set')
    child=GameSession.replay(c,s.to_record());child.submit(a);transitions+=1
    noisy=bool(classify_noisy(s.state,[(a,child.state)],c));label=source[canon(normalized(record_value(a)))]['wdl_bounds'];assert len(label)==2 and label[0]==label[1] and label[0] in (-1,0,1)
    facts.append(dict(action=record_value(a),noisy=noisy,source_wdl=label,source_perspective='globalseat0,parent-to-move',child_terminal=record_value(child.state.terminal_status),child_record=record_value(child.to_record())))
   strong,empty=predicate(facts);counts['complete_noncheck_forks']+=1
   row=dict(index=idx,id=t['id'],family=f,record=record_value(s.to_record()),fingerprint=fp,RuleSet=rule,root_source_wdl=t['wdl_bounds'],source_record=t['record'],actions=facts,strong=strong,empty_noisy_fork=empty,source_provenance=provenance,label_authority='Published AUX shared-Core source claim;not independently solved here')
   rows.append(dict(index=idx,id=t['id'],family=f,strong=strong,empty_noisy_fork=empty,legal=len(legal)))
   if empty and backup is None:backup=row;write_record(out/'first-empty-noisy-fork.json',row)
   if strong:candidate=row;write_record(out/'candidate.json',row);halt='FIRST_COMPLETE_SOURCE_ATTRIBUTED_QUIET_CONTRAST';break
   if len(rows)%50==0:write_record(out/'progress.json',dict(last=idx,counts=dict(counts),Core_children=transitions,elapsed=time.perf_counter()-tick))
  status='CANDIDATE' if candidate is not None else 'UNKNOWN' if halt else 'NO_MATCH_IN_COMPLETE_SOURCE'
 except Exception as e:status='FAILED';halt=type(e).__name__+':'+str(e)
 result=dict(status=status,halt=halt,last_visited=last,source_total=len(truth['roots']),counts=dict(counts),Core_children=transitions,rows=rows,source_provenance=provenance,started_at=begin,ended_at=stamp(),elapsed_seconds=time.perf_counter()-tick,new_Player_calls=0,new_games=0,new_solver=False,claim='One source-attributed finite-H6 legal action-coverage witness,not new truth,actual Q visitation,root correction or strength')
 write_record(out/'summary.json',result);record_interval(begin,result['ended_at'],'research',str(out/'summary.json'),out);print({k:v for k,v in result.items() if k not in ('rows','source_provenance')})

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.plan,a.output)
