"""Replay histories/PVs and exported WIN trees; do not rerun proof/search jobs."""
import sys,json,gzip,math,time,copy,argparse,hashlib
from pathlib import Path
from collections import Counter,defaultdict
from fractions import Fraction as F
sys.path.insert(0,str(Path.cwd()))
from scripts.leaper_design import compile_rule,ruleset_from_dict,GameSession,state_sha,record_value,match_action,material_profiles
from scripts.leaper_prices import relative_profiles
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.alphabeta.search import terminal_score
from generic_chess.core.actions import action_to_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,MATE,SessionChoice
from scripts.generic_session_certificate_json import decode_session_certificate
from scripts.generic_session_win_proof import verify_session_certificate
from scripts.leaper_microgames import role_stop_requested

canon=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'))
def session(compiled,record):return GameSession.replay(compiled,deserialize_game_record(canon(record)))
def match(s,raw):
 aa=[a for a in s.legal_actions()if action_to_dict(a)==raw];assert len(aa)==1;return aa[0]
def intersect(a,b):
 result=[max(a[0],b[0]),min(a[1],b[1])];assert result[0]<=result[1];return result

def verify(path):
 beg=time.perf_counter();counts=Counter();packet=json.loads(gzip.decompress(path.read_bytes()));assert packet['schema']=='leaper_tie_truth_v1'
 def guard():
  if role_stop_requested()or time.perf_counter()-beg>240:raise RuntimeError('VERIFY_CAP_OR_STOP')
 def pv(s,r,weights):
  assert r['complete']and r['action']is not None;leaf=FixedScaleSessionEnv(s,unit_type='A');rawpv=r['pv'];assert rawpv
  for raw in rawpv:
   guard()
   if raw.get('kind')=='DECLARATION':leaf.push(SessionChoice('DECLARATION',declaration_id=raw['declaration_id']))
   else:
    a=raw['action']if raw.get('kind')=='ACTION'else raw
    leaf.push(SessionChoice('ACTION',action=match(leaf.session,a)))
   counts['PV_edges']+=1
  first=rawpv[0]['action']if rawpv[0].get('kind')=='ACTION'else rawpv[0];assert first==r['action']
  terminal=leaf.terminal()
  if terminal is None:
   assert not r['pv_terminal']and tuple(r['pv_phi'])==leaf.features()
   assert math.isclose(Model(weights).raw(leaf.features()),r['value'],rel_tol=1e-12,abs_tol=1e-10)
  else:assert r['pv_terminal']and r['value']==MATE*terminal;counts['literal_terminal_PVs']+=1
  counts['queries']+=1
 def certificate(c,row,expected):
  guard();s,cert=decode_session_certificate(c,row['certificate'],max_nodes=100000);assert state_sha(s.state)==expected and cert.target==row['target']
  r=verify_session_certificate(s,cert,max_nodes=100000,seconds=30,cancel=role_stop_requested);assert r['verified']and row['verification']['verified'];counts['certificates']+=1;counts['certificate_nodes']+=r['nodes'];return cert

 source_raw=path.with_name('strongfoe-source.json.gz').read_bytes();assert hashlib.sha256(source_raw).hexdigest()==packet['strongfoe']['config']['source_sha256'];source=json.loads(gzip.decompress(source_raw));groups=defaultdict(dict)
 for row in source['games']:
  g=row['game'];groups[(g['world'],g['repeat'],g['role'])][g['pair']]=row
 selected=[];identical=0;seen=set();sourcecs={}
 for key,pair in sorted(groups.items()):
  guard();a=pair['STATIC_FOE3'];b=pair['UNIT_FOE3'];ga=a['game'];gb=b['game'];assert a['rule']==b['rule']and ga['initial_record']==gb['initial_record'];aa=ga['final_record']['actions'];bb=gb['final_record']['actions'];i=next((i for i,(x,y)in enumerate(zip(aa,bb))if x!=y),None)
  if i is None:assert aa==bb;identical+=1;continue
  fp=ga['initial_record']['ruleset_fingerprint']
  if fp not in sourcecs:sourcecs[fp]=compile_rule(ruleset_from_dict(a['rule']))
  record={**ga['final_record'],'actions':aa[:i],'resigned_by':None};ss=session(sourcecs[fp],record);keysha=state_sha(ss.state);assert ss.state.position.side_to_move==ga['role']
  if keysha in seen:continue
  seen.add(keysha);selected.append(dict(id=keysha,rule=a['rule'],record=record,Static_action=aa[i],Unit_action=bb[i],world=key[0],repeat=key[1],role=key[2],ply=i,original_slots=[ga['slot'],gb['slot']],original_file_sha256=[a['original_game_file_sha256'],b['original_game_file_sha256']]))
 cfg=packet['strongfoe']['config'];assert(len(groups),identical,len(selected))==(cfg['source_frames'],cfg['identical_trajectories'],cfg['distinct_divergence_histories']);assert selected[:32]==packet['strongfoe']['inputs']['roots']and selected[32:]==packet['strongfoe']['inputs']['unqueried_roots'];counts['source_frames']=len(groups);counts['source_first_divergences']=len(selected)

 n=packet['neutral'];p=n['plan'];c=compile_rule(ruleset_from_dict(p['world']['rule']));s=session(c,p['case']['record']);assert state_sha(s.state)==p['case']['id'];root=copy.copy(s);tree=packet['old_residual_tree'];eligible=p['eligible_indices']
 key=lambda i:(tree['branches'][i]['action']['actor_type_id'],*tree['branches'][i]['action']['from'],*tree['branches'][i]['action']['to'])
 assert p['chosen_index']==min(eligible,key=key)and eligible==tree['supports']['unit']
 chosen=tree['branches'][p['chosen_index']]['action'];assert chosen==n['result']['forced_action'];s.submit(match(s,chosen))
 for q in packet['neutral_queries']:
  assert(q['id'],q['ply'],q['actor'])==(state_sha(s.state),s.state.ply_count,s.state.position.side_to_move)
  pv(s,q['receipt'],q['weights']);s.submit(match(s,q['receipt']['action']))
 assert record_value(s.to_record())==n['result']['final_record'];v=FixedScaleSessionEnv(s,unit_type='A').terminal();assert v is not None
 sign=1 if p['case']['role']==0 else-1;assert n['result']['utility']==[sign*v]*2==[-1,-1]
 for old in [packet['old_TD_first_mobility_tail'],dict(final_record=packet['old_mobility_baseline']['record'],utility=packet['old_mobility_baseline']['metadata']['utility'])]:
  ss=session(c,old['final_record']);v=FixedScaleSessionEnv(ss,unit_type='A').terminal();assert v is not None and old['utility']==[sign*v]*2;counts['old_controls']+=1
 cert=certificate(c,n['root-loss-result'],p['case']['id']);assert cert.target==1-p['case']['role']and n['root-loss-result']['root_bounds']==[-1,-1]
 assert len(cert.tree.edges)==len(root.legal_actions());counts['all_root_defenses']=len(cert.tree.edges)
 for row in n['proof-rows']:
  if row['certificate']is not None:certificate(c,row,row['id'])
 a=n['analysis'];assert a['known_conditional_utilities']=={'1':[0,0],'3':[-1,-1],'2':[-1,-1]};bounds={i:a['known_conditional_utilities'].get(str(i),[-1,1])for i in eligible};expected=[sum(F(bounds[i][j],len(eligible))for i in eligible)for j in(0,1)];assert list(map(str,expected))==a['uniform_first_choice_expected_utility']
 assert a['unmeasured_indices']==[i for i in eligible if str(i)not in a['known_conditional_utilities']]
 for row in n['execution-rows']+n['iteration-rows']+n.get('D10-rows',[]):pv(root,row['receipt'],p['world']['priors'][row.get('model')])
 assert all(r['status']=='COMPLETE'for r in n['horizon-summary']['rows'])and[(r['depth'],r['forced_win_within'])for r in n['horizon-summary']['rows']]==[(4,False),(6,False),(8,False),(10,True)]

 tables={}
 for name in('TD_firstdiv','strongfoe'):
  data=packet[name];ins=data['inputs'];roots=ins['roots'];roots=roots if isinstance(roots,dict)else{r['id']:r for r in roots};cs={}
  for key,r in roots.items():
   rule=r.get('rule')or ins['worlds'][str(r['world'])]['rule'];cs[key]=compile_rule(ruleset_from_dict(rule));ss=session(cs[key],r['record']);assert state_sha(ss.state)==key;counts['proof_roots']+=1
  rows={r['slot']:r for r in data['queries']};assert len(rows)==len(data['queries']);table=defaultdict(lambda:[-1,1]);attempted=0
  for slot in data['slots']:
   r=roots[slot['root']];ss=session(cs[slot['root']],r['record']);action=slot.get('action')or r[slot['policy']+'_action'];ss.submit(match(ss,action));assert record_value(ss.to_record())==slot['record']and state_sha(ss.state)==slot['child']
   b=[-1,1]
   if slot['status']=='finished':
    attempted+=1;row=rows[slot['slot']];assert row['child']==slot['child']and row['target']==slot['target']
    if row['certificate']is not None:
     certificate(cs[slot['root']],row,slot['child']);b=[1,1]if slot['target']==slot['actor']else[-1,-1]
    else:assert row['status']=='UNKNOWN'
   else:assert slot['slot']not in rows
   assert b==slot['bounds'];table[(slot['root'],canon(action))]=intersect(table[(slot['root'],canon(action))],b)
  assert attempted==len(rows)
  if 'summary'in data:assert data['summary']['attempted']==attempted and data['summary']['not_started']==[s['slot']for s in data['slots']if s['status']!='finished']
  pairs=ins['comparisons']if name=='TD_firstdiv'else[dict(id=r['id'],arm='Static',base='Unit',arm_action=r['Static_action'],base_action=r['Unit_action'])for r in roots.values()]
  contrasts=[]
  for r in pairs:
   x=table[(r['id'],canon(r['arm_action']))];y=table[(r['id'],canon(r['base_action']))];contrasts.append(dict(root=r['id'],arm=r['arm'],base=r['base'],arm_bounds=x,base_bounds=y,difference=[x[0]-y[1],x[1]-y[0]],strict=x[0]>y[1]or y[0]>x[1],equal_certified=x==y and x[0]==x[1]))
  tables[name]=dict(planned=len(data['slots']),attempted=attempted,certified_children=sum(b[0]==b[1]for b in table.values()),unknown_children=sum(b[0]!=b[1]for b in table.values()),comparisons=contrasts)
 d=packet['depth'];roots=d['inputs']['roots'];worlds=d['inputs']['worlds'];cs={k:compile_rule(ruleset_from_dict(worlds[str(r['world'])]['rule']))for k,r in roots.items()}
 depthrows={}
 for row in d['rows']:
  ss=session(cs[row['root']],roots[row['root']]['record']);assert state_sha(ss.state)==row['root'];r=row['receipt']
  if r['complete']:pv(ss,r,worlds[str(roots[row['root']]['world'])]['priors'][row['model']])
  depthrows[(row['root'],row['model'],row['depth'])]=r
 depthcomparisons=[]
 for comparison in d['inputs']['comparisons']:
  for depth in(6,8):
   aa=depthrows.get((comparison['id'],comparison['arm'],depth));bb=depthrows.get((comparison['id'],comparison['base'],depth))
   if aa is not None and bb is not None:depthcomparisons.append(dict(root=comparison['id'],arm=comparison['arm'],base=comparison['base'],requested=depth,both_completed=aa['completed_depth']==bb['completed_depth']==depth,same_action=aa['action']==bb['action'],both_literal_terminal=aa['pv_terminal']and bb['pv_terminal'],values=[aa['value'],bb['value']]))
 worlds={w['world']:w for w in source['runs']['strongfoe']['files']['inputs.json']['worlds']};evaluators={};source_counts=Counter();records=packet['source_targets']['rows'];idx=0;recovery_candidates=[];seen=set();chosen_counts=Counter()
 for wrapped in source['games']:
  g=wrapped['game'];w=worlds[g['world']];fp=g['initial_record']['ruleset_fingerprint']
  if fp not in sourcecs:sourcecs[fp]=compile_rule(ruleset_from_dict(w['rule']))
  c=sourcecs[fp]
  if g['world']not in evaluators:
   base,zero=material_profiles(c);prices,_=relative_profiles(ruleset_from_dict(w['rule']),base);assert w['material_profiles']=={'Static':record_value(base),'M0':record_value(zero)}and w['price_profiles']=={k:record_value(v)for k,v in prices.items()};evaluators[g['world']]={'STATIC_ADAPTER':Evaluator(c,base,EvaluationConfig()),'UNIT':Evaluator(c,prices['UNIT'],EvaluationConfig())}
  ss=session(c,g['initial_record']);actions=deserialize_game_record(canon(g['final_record'])).actions[len(ss.to_record().actions):];assert len(actions)==len(g['queries'])
  for q,action in zip(g['queries'],actions,strict=True):
   guard();saved=records[idx];idx+=1;assert saved['root']==q['state_sha256']==state_sha(ss.state)and saved['slot']==g['slot'];leaf=copy.copy(ss);decision=q['decision'];pvs=decision['principal_variation']
   for raw in pvs:leaf.submit(match_action(leaf,raw));counts['source_target_PV_edges']+=1
   terminal=leaf.state.terminal_status.is_terminal;expected=terminal_score(leaf.state.terminal_status,q['actor'],len(pvs))if terminal else evaluators[g['world']][q['base_policy']].evaluate(leaf.state)*(1 if leaf.state.position.side_to_move==q['actor']else-1);matchscore=expected==decision['score'];full=len(pvs)==decision['completed_depth'];usable=bool(pvs)and matchscore and(terminal or full);reason='literal_terminal'if usable and terminal else'literal_nonterminal'if usable else'no_literal_PV'if not pvs else'nonterminal_short_PV'if not terminal and not full else'leaf_score_mismatch'
   assert(saved['literal_leaf_score'],saved['score_matches'],saved['depth_matches'],saved['literal_source_target'],saved['reason'])==(expected,matchscore,full,usable,reason);source_counts[reason]+=1
   if not usable and q['policy']in('STATIC_ADAPTER','UNIT')and saved['root']not in seen and chosen_counts[q['policy']]<4:
    seen.add(saved['root']);chosen_counts[q['policy']]+=1;recovery_candidates.append(dict(old=saved,query=q,record=record_value(ss.to_record()),world=w))
   ss.submit(action)
  assert record_value(ss.to_record())==g['final_record'];counts['source_target_games']+=1
 assert idx==len(records)==packet['source_targets']['summary']['checked'];counts['source_target_returns']=idx
 for k,v in source_counts.items():assert packet['source_targets']['summary']['counts'][k]==v
 recovery=packet['target_recovery'];assert recovery_candidates==recovery['inputs'];literal=Counter()
 for row in recovery['rows']:
  case=recovery_candidates[row['slot']];w=case['world'];c=sourcecs[w['fingerprint']];ss=session(c,case['record']);assert state_sha(ss.state)==row['root'];decision=row['decision'];leaf=copy.copy(ss)
  for raw in decision['principal_variation']:leaf.submit(match_action(leaf,raw));counts['recovery_PV_edges']+=1
  terminal=leaf.state.terminal_status.is_terminal;expected=terminal_score(leaf.state.terminal_status,ss.state.position.side_to_move,len(decision['principal_variation']))if terminal else evaluators[w['world']][row['policy']].evaluate(leaf.state)*(1 if leaf.state.position.side_to_move==ss.state.position.side_to_move else-1)
  usable=bool(decision['principal_variation'])and expected==decision['score']and(terminal or len(decision['principal_variation'])==decision['completed_depth']);assert(expected,terminal,usable)==(row['literal_leaf_score'],row['leaf_terminal'],row['literal_source_target']);literal[str(row['require_full_pv'])]+=usable;counts['fresh_recovery_queries']+=1
 assert len(recovery['rows'])==16 and literal=={'False':8,'True':8}
 pilot=packet['free_prior_pilot'];chosen=[];rolecounts=Counter()
 for r in packet['strongfoe']['inputs']['roots']:
  if rolecounts[r['role']]<4:chosen.append(r);rolecounts[r['role']]+=1
 assert chosen==pilot['inputs']['roots']and rolecounts=={0:4,1:4};games={g['slot']:g for g in pilot['games']};pilot_counts=Counter();utilities={}
 for slot in pilot['slots']:
  if slot['status']=='not_started':assert slot['slot']not in games and slot['utility']==[-1,1];utilities[(slot['frame'],slot['model'])]=[-1,1];continue
  g=games[slot['slot']];r=chosen[slot['frame']];w=pilot['inputs']['worlds'][str(r['world'])];assert w==worlds[r['world']];c=sourcecs[w['fingerprint']];ss=session(c,r['record']);assert state_sha(ss.state)==g['root']==r['id'];env=FixedScaleSessionEnv(ss,unit_type='A');prices=w['price_profiles']['MOBILITY']['board_value_by_type'];weights=[(1. if slot['model']=='Unit'else prices[t]/prices['A'])if kind=='board'else 0. for kind,t in env.names];assert weights==g['weights']
  for qi,q in enumerate(g['queries']):
   guard();assert(q['id'],q['actor'])==(state_sha(ss.state),ss.state.position.side_to_move)
   if q['actor']==r['role']:
    assert q['weights']==weights and q['model']==slot['model'];receipt=q['receipt']
    if not receipt['complete']or receipt['action']is None:assert qi==len(g['queries'])-1 and g['censor'];break
    pv(ss,receipt,weights);action=match(ss,receipt['action']);pilot_counts['candidate_queries']+=1;pilot_counts['candidate_nodes']+=receipt['nodes']
   else:
    receipt=q['decision']
    if receipt['action']is None:assert qi==len(g['queries'])-1 and g['censor'];break
    leaf=copy.copy(ss)
    for pa in receipt['principal_variation']:leaf.submit(match_action(leaf,pa));counts['pilot_opponent_PV_edges']+=1
    action=match_action(ss,receipt['action']);pilot_counts['opponent_queries']+=1;pilot_counts['opponent_nodes']+=receipt['nodes']+receipt['qnodes']
   ss.submit(action);counts['pilot_actual_moves']+=1
  assert record_value(ss.to_record())==g['final_record']and record_value(ss.result)==g['terminal'];v=FixedScaleSessionEnv(ss,unit_type='A').terminal();u=[-1,1]if v is None else[v*(1 if r['role']==0 else-1)]*2;assert g['utility']==slot['utility']==u
  if v is not None:assert slot['status']=='finished'and not g['censor'];pilot_counts[slot['model']+':'+str(u[0])]+=1
  else:assert slot['status']=='censored'
  utilities[(slot['frame'],slot['model'])]=u
 differences=[]
 for frame in range(8):
  aa=utilities[(frame,'Mobility')];bb=utilities[(frame,'Unit')];differences.append([aa[0]-bb[1],aa[1]-bb[0]])
 pilot_result=dict(counts=pilot_counts,paired_differences=differences,mean_difference=[str(sum(F(x[j],8)for x in differences))for j in(0,1)],scope='Finite exposed-history conditional play through learner search,0updates. Same paired opponent/limits,not PRIMARY policyfamily,not independent holdout or minimax labels.')
 crossresults={}
 for label in('prior_crossscores','negative_crossscores'):
  cross=packet[label];case=cross['inputs'];frame=case['frame'];ga=games[frame*2];gb=games[frame*2+1];aa=ga['final_record']['actions'];bb=gb['final_record']['actions'];i=next(i for i,(a,b)in enumerate(zip(aa,bb))if a!=b);record={**ga['final_record'],'actions':aa[:i],'resigned_by':None};assert record==case['record']and case['actions']=={'Unit':aa[i],'Mobility':bb[i]};c=sourcecs[case['world']['fingerprint']];ss=session(c,record);assert state_sha(ss.state)==cross['summary']['root'];crossvalues={m:{}for m in('Unit','Mobility')}
  for row in cross['rows']:
   child=copy.copy(ss);child.submit(match(child,case['actions'][row['forced']]));assert record_value(child.to_record())==row['child_record']and state_sha(child.state)==row['child'];pv(child,row['receipt'],case['weights'][row['model']]);v=row['receipt']['value']*(1 if case['role']==0 else-1);assert v==row['root_score'];crossvalues[row['model']][row['forced']]=v
  assert crossvalues==cross['summary']['scores']and cross['summary']['complete']==4
  assert crossvalues['Unit']['Unit']==crossvalues['Unit']['Mobility']and crossvalues['Mobility']['Mobility']>crossvalues['Mobility']['Unit']
  for model in('Unit','Mobility'):
   old=case['old_queries'][model]['receipt'];assert old['completed_depth']==cross['summary']['requested_root_depth']and math.isclose(max(crossvalues[model].values()),old['value']*(1 if case['role']==0 else-1),abs_tol=1e-10)
  crossresults[label]=crossvalues
 for capsule in packet['producer_sources'].values():assert hashlib.sha256(capsule['text'].encode('utf8')).hexdigest()==capsule['sha256']
 return dict(status='PASS',seconds=time.perf_counter()-beg,counts=counts,tables=tables,depthcomparisons=depthcomparisons,source_target_counts=source_counts,pilot=pilot_result,crossscores=crossresults,scope='Independent literal public-Core/PV and actual-Session certificate replay,not independent engine or new search. UNKNOWN never draw;fixed-opponent utilities are not actionWDL. Embedded sources not executed. Horizon predicate rows are retained producer receipts,not independently rerun here.')

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('packet',type=Path);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();result=verify(a.packet);a.output.write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in result.items()if k not in('tables','depthcomparisons')}))
