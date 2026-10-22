"""Verify compact arithmetic and literal Core witnesses,not the full graph census."""
from __future__ import annotations
import json,gzip,hashlib,time,importlib.util,sys
from pathlib import Path
from collections import Counter,defaultdict
from copy import deepcopy,copy
from fractions import Fraction as F
from math import isclose,tanh
from dataclasses import replace
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.transition import legal_successors
from generic_chess.core.actions import action_to_dict,action_from_dict
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,MATE
from generic_chess.ai.alphabeta.search import terminal_score
from generic_chess.core.pieces import Piece
from scripts.leaper_retrograde import fresh_state
from scripts.research_record import record_value
from scripts.leaper_design import state_sha
from datetime import datetime

def check_queries(qrows,qsummary,analysis,roots,columns):
 counts=defaultdict(Counter);groups=defaultdict(dict);nodes=0
 for row in qrows:
  q=dict(zip(columns,row));r=roots[q['root']];groups[r[0]][q['B'],q['requested']]=q;nodes+=q['nodes'];key=f"B{q['B']}:D{q['requested']}";c=counts[key];c['queries']+=1;c['nodes']+=q['nodes'];c['seconds']+=q['seconds'];c['full_depth']+=q['completed']==q['requested']and q['chosen_WDL']is not None;c['errors']+=q['chosen_WDL']is not None and q['chosen_WDL']<r[4]
  if q['action']is not None:assert q['chosen_WDL']==next(b[1]for b in r[9]if b[0]==q['action'])
  else:assert q['chosen_WDL']is None
 assert nodes==qsummary['nodes'];assert len(qrows)==qsummary['recorded'];assert qsummary['missing']==qsummary['planned']-len(qrows)
 for key,c in counts.items():
  for k,v in c.items():assert isclose(v,qsummary['conditions'][key][k],rel_tol=1e-10,abs_tol=1e-8)
 if analysis is None:
  qs=[dict(zip(columns,row))for row in qrows];assert sum(q['new_call']for q in qs)==qsummary['new_Player_queries'];assert sum(not q['new_call']for q in qs)==qsummary['reused_queries'];assert sum(q['nodes']for q in qs if q['new_call'])==qsummary['new_nodes'];return nodes
 # Recompute all price/depth contrast counts and whole-source missing bounds.
 for name,expected in analysis['contrasts'].items():
  full=name.endswith(':full_requested');label=name.split(':')[0]
  if label.startswith('B'):
   after,before=map(float,label[1:].split('-B'));depth=int(name.split(':')[1][1:]);left,right=(before,depth),(after,depth)
  else:b=float(name.split(':')[1][1:]);left,right=(b,2),(b,4)
  vals=[];changes=0
  for hid,g in groups.items():
   if left not in g or right not in g:continue
   a,b=g[left],g[right]
   if a['chosen_WDL']is None or b['chosen_WDL']is None or(full and(a['completed']!=a['requested']or b['completed']!=b['requested'])):continue
   vals.append(b['chosen_WDL']-a['chosen_WDL']);changes+=a['action']!=b['action']
  n=expected['source_histories'];missing=n-len(vals);assert(len(vals),sum(v>0 for v in vals),sum(v<0 for v in vals),changes)==(expected['paired'],expected['improves'],expected['worsens'],expected['action_changes']);assert expected['whole_source_bounds']==[str(F(sum(vals)-2*missing,n)),str(F(sum(vals)+2*missing,n))]
 return nodes

def verify(directory=None):
 directory=Path(directory or Path(__file__).resolve().parent);tick=time.perf_counter();manifest=json.loads((directory/'manifest.json').read_text());blob=(directory/manifest['file']).read_bytes();assert len(blob)==manifest['bytes']and hashlib.sha256(blob).hexdigest()==manifest['sha256'];raw=gzip.decompress(blob);assert len(raw)==manifest['uncompressed_bytes'];p=json.loads(raw)
 compiled={fp:compile_rule(ruleset_from_dict(rule))for fp,rule in p['rules'].items()};assert all(c.ruleset_fingerprint==fp==compute_fingerprint(ruleset_from_dict(p['rules'][fp]))for fp,c in compiled.items())
 roots=p['roots'];ri={r[0]:r for r in roots};assert len(ri)==len(roots)==manifest['roots'];assert all(r[4]==max(b[1]for b in r[9])and r[7]==(len({b[1]for b in r[9]})>1)for r in roots);assert all(not r[6]or(r[4]==0 and all(b[1]==0 for b in r[9]))for r in roots)
 assert len(p['trajectories'])==p['triage']['inventory']['unique_records'];assert sum(len(t['refs'])for t in p['trajectories'])==p['triage']['inventory']['packet_refs'];assert len(roots)==p['triage']['labelled_histories'];known=set();maxply=dead_maxply=win_maxply=0;refs=0
 corpus_moves=corpus_bindings=0;case_by_id={r['id']:r for r in p['triage']['cases']}
 for t in p['trajectories']:
  labelled=[(step[0],roots[step[1]],step[2])for step in t['path']if step[1]is not None];known.update(r[0]for ply,r,n in labelled);dead=[ply for ply,r,n in labelled if r[6]];wins=[ply for ply,r,n in labelled if r[4]==1]
  if 'record_header'in t:
   record=t['record_header']|dict(actions=[p['actions'][step[3]]for step in t['path']if step[3]is not None]);assert hashlib.sha256(json.dumps(record,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()==t['id'];session=GameSession(compiled[record['ruleset_fingerprint']]);bad=[]
   for ply,index,n,action in t['path']:
    assert session.state.ply_count==ply and sum(pc is not None for pc in session.state.position.board)==n
    if index is not None:
     r=roots[index];assert state_sha(session.state)==r[0];corpus_bindings+=1
     if action is not None and next(b[1]for b in r[9]if b[0]==action)<r[4]:bad.append(ply)
    if action is not None:session.submit(action_from_dict(p['actions'][action]));corpus_moves+=1
   assert record_value(session.to_record())==record and record_value(session.result)==t['terminal'];assert(min(bad)if bad else None)==case_by_id[t['id']]['first_inferior']
  if dead:assert all(r[6]for ply,r,n in labelled if ply>=min(dead))
  maxply+=t['terminal']['status']=='max_ply';dead_maxply+=bool(dead)and t['terminal']['status']=='max_ply';win_maxply+=bool(wins)and t['terminal']['status']=='max_ply';refs+=len(t['refs'])
 assert len(known)==len(roots);u=p['triage']['unique_records'];assert(maxply,dead_maxply,win_maxply)==(u['max_ply'],u['maxply_entered_dead'],u['maxply_had_WIN'])
 query_nodes=check_queries(p['queries'],p['query_summary'],p['public_analysis'],roots,p['query_columns']);assert len(p['queries'])==manifest['queries']
 five_nodes=0
 if p.get('five_query_summary') is not None:five_nodes=check_queries(p['five_queries'],p['five_query_summary'],p['five_public_analysis'],roots,p['query_columns'])
 prior_calls=prior_new=prior_reused=0;baseline={}
 for row in p.get('five_queries',[]):
  q=dict(zip(p['query_columns'],row));baseline[q['root'],q['B'],q['requested']]=q
 for name,block in p.get('priors',{}).items():
  check_queries(block['queries'],block['summary'],None,roots,p['prior_columns']);prior_calls+=len(block['queries']);prior_new+=block['summary']['new_Player_queries'];prior_reused+=block['summary']['reused_queries']
  for row in block['queries']:
   q=dict(zip(p['prior_columns'],row));fp=p['fingerprints'][roots[q['root']][1]];m=p['prior_metadata'][fp];ratio=m['geometry'][1]['mean_empty_board_degree']/m['geometry'][0]['mean_empty_board_degree']if name=='mobility'else m['board_values']['B']/m['board_values']['A'];assert q['B']==ratio
   if not q['new_call']:
    old=baseline[q['root'],q['B'],q['requested']]
    for k in p['query_columns']:assert q[k]==old[k]
  for depth in(2,4):
   qs=[dict(zip(p['prior_columns'],row))for row in block['queries']if row[2]==depth];vals=[q['chosen_WDL']-baseline[q['root'],1.,depth]['chosen_WDL']for q in qs];expected=p['priors_analysis']['comparisons'][f'{name}:D{depth}'];assert(sum(vals),sum(q['chosen_WDL']<roots[q['root']][4]for q in qs))==(expected['sum_delta'],expected['errors'])
 # Shared all-defense verifier walks actual GameSessions; no graph labels input.
 spec=importlib.util.spec_from_file_location('existing_core_proof',directory.parent/'leaper_primary_AB_truth_20261022'/'verify.py');proof_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(proof_module);proof_nodes=sum(proof_module.verify_proof(compiled[r['record']['ruleset_fingerprint']],r)for r in p['proofs']);assert proof_nodes==manifest['literal_proof_nodes']and len(p['proofs'])==manifest['proofs'];negative=0
 for layer in('low','4'):
  row=next(r for r in p['proofs']if(ri[r['id']][3]<=3)==(layer=='low')and len(r['leaf_paths'])>1)
  for kind in('winner','missingbranch'):
   bad=deepcopy(row)
   if kind=='winner':bad['winner']=1-bad['winner']
   else:bad['leaf_paths'].pop()
   try:proof_module.verify_proof(compiled[bad['record']['ruleset_fingerprint']],bad)
   except(AssertionError,KeyError):negative+=1
   else:raise AssertionError('corrupted proof accepted')
 assert sum(r['status']!='COMPLETE'for r in p['proof_statuses'])==3
 intervention_nodes=closure_states=closure_edges=binding_negative=0
 if p.get('price_control')is not None:
  control=p['price_control'];fp=control['root_record']['ruleset_fingerprint'];c=compiled[fp];rule=ruleset_from_dict(p['rules'][fp]);assert c.repetition_limit==4 and c.max_ply==128 and c.repetition_policy=='draw';assert rule.capture_disposition=='remove_from_game'and not rule.promotion_allowed and not rule.promotion_forced;assert all(not pc.is_promotable for pc in rule.piece_types);assert all(not any(mask)for masks in rule.drop_allowed.values()for mask in masks)
  for name in('no_progress_draw','automatic_adjudications','consecutive_action_adjudications','repeated_cycle_target_conditions'):assert not getattr(c.support,name,None)
  witnesses=next(w for w in p['witnesses']if w['truth']['id']==control['id'])
  for name,b in(('bad',2.),('safe',.5)):
   q=next(q for q in witnesses['queries']if q['B']==b and q['requested']==4);assert q['action']==control[name+'_action']
   expected=control['root_record']|dict(actions=control['root_record']['actions']+[q['action']]);assert expected==(control['bad_proof']['record']if name=='bad'else control['safe_record'])
  if control['bad_proof']['status']=='COMPLETE':intervention_nodes=proof_module.verify_proof(c,control['bad_proof'])
  safe=GameSession.replay(c,deserialize_game_record(json.dumps(control['safe_record'])));template=GameSession(c).state.position;positions=set()
  for row in control['safe_positions']:
   board=tuple(Piece(pc[0],pc[1],pc[1])if pc else None for pc in row['board']);positions.add(replace(template,board=board,side_to_move=row['side']))
  assert safe.state.position in positions and set(safe.legal_actions())=={ac for ac,ch in legal_successors(fresh_state(safe.state.position,c),c)}
  for pos in positions:
   s=fresh_state(pos,c);assert s.terminal_status.winner is None
   for ac,ch in legal_successors(s,c):assert ch.position in positions and ch.terminal_status.winner is None;closure_edges+=1
  closure_states=len(positions);assert closure_states==len(control['safe_positions'])and closure_edges==control['safe_edges']
  if intervention_nodes:
   broken=deepcopy(control['bad_proof']);broken['record']=control['safe_record']
   try:proof_module.verify_proof(c,broken)
   except(AssertionError,KeyError):binding_negative=1
   else:raise AssertionError('wrong intervention binding accepted')
 clock_nodes=0
 def exact(s,c,cache):
  nonlocal clock_nodes
  clock_nodes+=1
  if s.terminal_status.is_terminal:
   w=s.terminal_status.winner;return 0 if w is None else 1 if w==s.position.side_to_move else -1
  assert s.ply_count<128
  if s in cache:return cache[s]
  value=-1
  for ac,ch in legal_successors(s,c):
   value=max(value,-exact(ch,c,cache))
   if value==1:break
  cache[s]=value;return value
 for row in p['clock']['rows']:
  c=compiled[row['record']['ruleset_fingerprint']];s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record']))).state;cache={};assert exact(s,c,cache)==row['WDL'];r=ri[row['id']];expected={json.dumps(p['actions'][b[0]],sort_keys=True):b[1]for b in r[9]}
  for ac,ch in legal_successors(s,c):assert-exact(ch,c,cache)==expected[json.dumps(action_to_dict(ac),sort_keys=True)]
 assert clock_nodes==p['clock']['nodes']
 literal_price_nodes=0
 if p.get('literal_price')is not None:
  control=p['literal_price'];prices=control['prices']
  def scores(s,c,d,ply,cache):
   nonlocal literal_price_nodes
   literal_price_nodes+=1
   if s.terminal_status.is_terminal:
    v=terminal_score(s.terminal_status,s.position.side_to_move,ply);return(v,)*len(prices)
   if not d:
    a=sum((1 if pc.owner==0 else-1)for pc in s.position.board if pc and pc.current_type_id=='A');b=sum((1 if pc.owner==0 else-1)for pc in s.position.board if pc and pc.current_type_id=='B');sign=1 if s.position.side_to_move==0 else-1;return tuple(sign*(a+x*b)for x in prices)
   key=(s,d)
   if key in cache:return cache[key]
   best=[-float('inf')]*len(prices)
   for ac,ch in legal_successors(s,c):best=[max(v,-w)for v,w in zip(best,scores(ch,c,d-1,ply+1,cache))]
   cache[key]=tuple(best);return tuple(best)
  for witness in control['rows']:
   c=compiled[witness['record']['ruleset_fingerprint']];s=GameSession.replay(c,deserialize_game_record(json.dumps(witness['record']))).state
   for row in witness['depths']:
    cache={};expected={json.dumps(b['action'],sort_keys=True):b['scores']for b in row['branches']}
    for ac,ch in legal_successors(s,c):assert[-v for v in scores(ch,c,row['depth']-1,1,cache)]==expected[json.dumps(action_to_dict(ac),sort_keys=True)]
    for j,price in enumerate(prices):
     top=max(b['scores'][j]for b in row['branches']);actual=[i for i,b in enumerate(row['branches'])if b['scores'][j]==top];assert actual==row['supports'][str(price)]
  if control['status']=='COMPLETE':assert literal_price_nodes==control['nodes']
 pv_edges=pv_calls=0
 for witness in p['witnesses']:
  record=witness['truth']['record'];c=compiled[record['ruleset_fingerprint']]
  for q in witness['queries']:
   if not q['usable']or q['action']is None:continue
   session=GameSession.replay(c,deserialize_game_record(json.dumps(record)))
   for ac in q['PV']:session.submit(action_from_dict(ac));pv_edges+=1
   env=FixedScaleSessionEnv(session,unit_type='A');terminal=env.terminal()
   if terminal is not None:assert q['pv_terminal']and q['value']==MATE*terminal
   else:
    assert not q['pv_terminal']and list(env.features())==q['pv_phi'];m=Model([q['B']if name=='B'else 1. for kind,name in env.names]);assert isclose(m.raw(env.features()),q['value'],abs_tol=1e-10)
   pv_calls+=1
 # Reuse the already published old fiveactor capsule,not another raw copy.
 old=json.loads(gzip.decompress((directory.parent/'leaper_natural_decisions_20261022'/'evidence.json.gz').read_bytes()))['five'];assert old['full_query_sha256']==p['old_five_gradient']['query_sha256'];oldgroups=defaultdict(dict);weights=Counter(v[0]for v in old['visits']);table=defaultdict(Counter)
 for row in old['queries']:
  q=dict(zip(old['query_columns'],row));oldgroups[q['root']][q['B'],q['requested']]=q
 for root,g in oldgroups.items():
  for depth in(2,4):
   q=g[1.,depth];r=old['roots'][root];phi=q['pv_phi'];kind='terminal'if q['pv_terminal']else'nonzero_B_Jacobian'if phi and phi[1]*(1-tanh(q['value']/10)**2)/10 else'zero_B_Jacobian';c=table[f'D{depth}:{kind}'];c['histories']+=1;c['visits']+=weights[root];c['true_forks']+=r['distinct_WDL'];c['deployed_errors']+=q['chosen_WDL']<r['root_WDL'];c['any_price_improves']+=any(g[b,depth]['chosen_WDL']>q['chosen_WDL']for b in(.25,.5,.75,1.5,2.,4.));c['any_price_worsens']+=any(g[b,depth]['chosen_WDL']<q['chosen_WDL']for b in(.25,.5,.75,1.5,2.,4.))
 assert dict(table)==p['old_five_gradient']['table']
 work=p['effective_work'];confirmed=sum((datetime.fromisoformat(w['ended_at'])-datetime.fromisoformat(w['started_at'])).total_seconds()for w in work['work_intervals']);assert isclose(confirmed,work['effective_work_seconds'],abs_tol=1e-5)
 return dict(status='PASS',compact_histories=len(roots),literal_corpus_records=len(p['trajectories']),literal_corpus_moves=corpus_moves,literal_corpus_bindings=corpus_bindings,compact_calls=len(p['queries']),five_compact_calls=len(p.get('five_queries',[])),prior_receipts=prior_calls,new_prior_calls=prior_new,reused_prior_calls=prior_reused,proofs=len(p['proofs']),literal_proof_nodes=proof_nodes,negative_controls=negative,intervention_proof_nodes=intervention_nodes,wrong_intervention_negative=binding_negative,safe_closure_states=closure_states,safe_closure_edges=closure_edges,clock_checks=len(p['clock']['rows']),literal_clock_nodes=clock_nodes,literal_price_nodes=literal_price_nodes,literal_saved_PV_calls=pv_calls,literal_saved_PV_edges=pv_edges,old_five_calls=len(old['queries']),confirmed_work_seconds=confirmed,seconds=time.perf_counter()-tick,scope='Arithmetic,actual-history replay/proofs/clock,argmax,safeclosure and savedPV replay only. No full graph census rerun,new Player query,training or independent population claim.')

if __name__=='__main__':print(json.dumps(verify(),indent=2))
