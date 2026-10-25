"""Read-only Core/paired-budget qualification; never executes source capsules."""
from pathlib import Path
from collections import defaultdict
import argparse,json,hashlib,statistics
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.verify_leaper_forced_continuation import raw,load,rows,key
from generic_chess.ai.evaluation.config import MATE_THRESHOLD

def paired(records):
 groups=defaultdict(dict)
 for r in records:
  k=(r['budget'],r['key']);assert r['arm']not in groups[k],'duplicatearm';groups[k][r['arm']]=r
 result={}
 for b in ['balanced50k','deep200k']:
  complete=[(k,a)for k,a in groups.items()if k[0]==b and set(a)=={'default','anywin'}];pairs=[]
  for k,a in complete:
   base=a['default'];can=a['anywin'];pairs.append(dict(key=k[1],default=base,anywin=can,repair=not base['correct']and can['correct'],regression=base['correct']and not can['correct'],ratio=can['seconds']/base['seconds'],caller_ratio=can['caller_seconds']/base['caller_seconds'],work_ratio=can['events']/base['events']if base['events']else None))
  non_goal=[p for p in pairs if all(not p[a]['win_band']and not p[a]['time_censored']and 'parity_signature'in p[a]for a in ['default','anywin'])]
  result[b]=dict(exact_non_goal_pairs=len(non_goal),exact_non_goal_mismatches=[p['key']for p in non_goal if p['default']['parity_signature']!=p['anywin']['parity_signature']],action_changes=[p['key']for p in pairs if p['default'].get('action_key')!=p['anywin'].get('action_key')],cpu_seconds={a:sum(p[a].get('cpu_seconds',0)for p in pairs)for a in ['default','anywin']},pairs=len(pairs),correct={a:sum(p[a]['correct']for p in pairs)for a in ['default','anywin']},sensitive=sum(p['default']['sensitive']for p in pairs),sensitive_correct={a:sum(p[a]['correct']and p[a]['sensitive']for p in pairs)for a in ['default','anywin']},repairs=[p['key']for p in pairs if p['repair']],regressions=[p['key']for p in pairs if p['regression']],goal_stops=sum(p['anywin']['goal_stop']for p in pairs),win_band={a:sum(p[a]['win_band']for p in pairs)for a in ['default','anywin']},time_censored={a:[p['key']for p in pairs if p[a]['time_censored']]for a in ['default','anywin']},seconds={a:sum(p[a]['seconds']for p in pairs)for a in ['default','anywin']},caller_seconds={a:sum(p[a]['caller_seconds']for p in pairs)for a in ['default','anywin']},events={a:sum(p[a]['events']for p in pairs)for a in ['default','anywin']},median_paired_latency_ratio=statistics.median(p['ratio']for p in pairs)if pairs else None,pair_rows=pairs)
 return result

def completed_prefix(path, limit):
 return [json.loads(line)for line in raw(path).splitlines(keepends=True)if line.endswith(b'\n')][:limit]

def assess(directory, prefix_limit=None):
 d=Path(directory);p=load(d/'plan.json');data=load(d/'inputs.json');rr=rows(d/'queries.jsonl')if prefix_limit is None else completed_prefix(d/'queries.jsonl',prefix_limit);qq=rows(d/'qualification.jsonl')if prefix_limit is None else completed_prefix(d/'qualification.jsonl',prefix_limit)
 if prefix_limit is None:receipt=load(d/'receipt.json')
 else:
  assert prefix_limit==128 and len(rr)>=128 and len(qq)>=128,'only whole frozen50k milestone';rr=rr[:128];qq=qq[:128];assert all(r['slot']['budget']=='balanced50k'for r in rr);receipt=dict(status='RUNNING_QUALIFIED_50K_PREFIX_NOT_BATCH_RECEIPT',queries=128,source_sha256=p['source_sha256'])
 assert hashlib.sha256(raw(d/'inputs.json')).hexdigest()==p['inputs_sha256']and receipt['source_sha256']==p['source_sha256'];assert receipt['queries']==len(rr)and [r['slot']for r in rr]==p['slots'][:len(rr)]
 if receipt['status']=='CLOSED':assert len(rr)==len(qq)==len(p['slots'])==160
 cases={c['key']:c for c in data['cases']};qmap={key(q['slot']):q for q in qq};assert len(qmap)==len(qq);out=[];pv_steps=0;seen={}
 for r in rr:
  slot=r['slot'];case=cases[slot['key']];c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]));s=replay(c,case['record']);assert L.state_sha(s.state)==case['state_sha256']==r['state_sha256']and s.state.position.side_to_move==case['actor'];labels={key(x['action']):x['truth']['value']for x in case['labelled_actions']};assert set(labels)=={key(L.record_value(a))for a in s.legal_actions()};assert(max if case['actor']==0 else min)(labels.values())==case['root_global_WDL'];dec=r['decision'];q=qmap[key(slot)];v=labels[key(dec['action'])];correct=v==case['root_global_WDL'];assert q['chosen_global_WDL']==v and q['correct']==correct;assert dec['runtime_depth_balanced']and dec['runtime_pushes']==dec['runtime_pops'];band=dec['score']>=MATE_THRESHOLD;assert q['score_in_win_band']==band
  if band:assert correct,'win-band wronglabel; no cost-only rescue'
  if dec['termination_reason']=='root_win_found':assert slot['arm']=='anywin'and band
  for a in dec['principal_variation']:s.submit(L.match_action(s,a));pv_steps+=1
  tuning=dict(r['tuning']);assert tuning.pop('stop_after_root_win')==(slot['arm']=='anywin');k=(slot['budget'],slot['key']);meta=(tuning,r['evaluation_profile']);assert k not in seen or seen[k]==meta;seen[k]=meta
  signature=[dec[x]for x in ['action','score','principal_variation','completed_depth','nodes','qnodes','tt_probes','tt_hits','tt_cutoffs','beta_cutoffs']]
  out.append(dict(cpu_seconds=r['cpu_seconds'],action_key=key(dec['action']),parity_signature=signature,**slot,correct=correct,value=v,sensitive=len(set(labels.values()))>1,seconds=r['seconds'],caller_seconds=r['caller_seconds'],events=dec['nodes']+dec['qnodes'],win_band=band,goal_stop=dec['termination_reason']=='root_win_found',time_censored=dec['termination_reason']=='time_limit',source=dec['result_source'],completed_depth=dec['completed_depth'],score=dec['score'],termination=dec['termination_reason']))
 return dict(execution_receipt_required=prefix_limit is None,status=receipt['status'],queries=len(rr),pv_steps=pv_steps,missing_slots_UNKNOWN=p['slots'][len(rr):],by_budget=paired(out),limitations='WDL anywinningchoice objective, not shortestmate/sameaction/depth. SharedCore/fixedpublishedAUX labels;oneexposedRuleSet/64correlatedTRAINhistories/44physicalpositions,deep16predeterminedsubset. ReturnedWDL distinct from desirednode budget and45safetycensor. Current pairedwalltime includes sharedload; goals may finish below nodebudget intentionally. No independent solver, holdout, strength or default/UI activation.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();print(json.dumps(assess(a.directory),indent=2))
