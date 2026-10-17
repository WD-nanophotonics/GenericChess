from pathlib import Path
import sys,json,time,random,hashlib,traceback,subprocess
ROOT=Path.cwd();D=ROOT/'.local_agent/movement-transfer-20261017';START=time.monotonic();sys.path.insert(0,str(ROOT))
from tools.local_agent.common import write_json
from scripts.research_record import record_value
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
PLAN=json.loads((D/'plan.json').read_bytes());A=ROOT/'.local_agent/free-price-20261017/exact/results/dev_aux';TRAIN=json.loads((A/'task2534/result.json').read_bytes());FOES=json.loads((A/'task2535/plan.json').read_bytes())['opponents'];compiled={};native={};models={};roots={};games=[];queries=nodes=0;status='COMPLETE';reason=current=None
assert not(D/'producer-source.json').exists()and not(D/'games.jsonl').exists()
def digest(value):return hashlib.sha256(json.dumps(record_value(value),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def poll():
 if time.monotonic()-START>=PLAN['limits']['global_cap_seconds']:raise TimeoutError('FROZEN_GLOBAL_CAP')
 for name in('rollout','advisor','slack'):
  f=json.loads((ROOT/'.local_agent'/(name+'.json')).read_bytes())
  if f.get('stopped')or f.get('user_paused'):raise InterruptedError('EXPLICIT_STOP')
def assess(session,owner):
 if session.result.status.value=='ongoing':return None
 return 0 if session.result.winner is None else 1 if session.result.winner==owner else-1
write_json(D/'producer-source.json',dict(producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),plan_sha256=hashlib.sha256((D/'plan.json').read_bytes()).hexdigest(),git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),actual91source_sha='03d4a8635bef8d0e203de81eb6335521ba366e36',training_source_sha256=hashlib.sha256((A/'task2534/result.json').read_bytes()).hexdigest(),scope='Newregisteredserved-candidateDIAGNOSTIC; no oldTRAIN/EVALrerun/newlearner. Sourcepinnedbeforefitness.'))
for gs in PLAN['rules']:
 poll();rule=ruleset_from_dict(json.loads((D/f'rule-{gs}.json').read_bytes()));c=compile_legacy_ruleset_for_semantic_execution(rule);compiled[gs]=c;native[gs]=compile_native_semantic_rules(c)
 def fixed(channels,weights,label):
  board={t:0. for t in c.types_by_id};hand=dict(board)
  for(kind,t),w in zip(channels,weights):(board if kind=='board'else hand)[t]=w
  return LearnableMaterialCheckpoint(ruleset_fingerprint=c.ruleset_fingerprint,evaluation_profile_version=label,board_weights=board,hand_weights=hand,material_scale=256,value_scale=10.,reference_median=1.)
 arms=[a for a in TRAIN['arms']if a['generator_seed']==PLAN['variants'][gs]['recipient']];channels=arms[0]['channels']
 for a in arms:
  assert a['channels']==channels;models[gs,a['method']+str(a['seed'])]=fixed(channels,a['weights'],'actual91-'+a['method'])
  if a['method']=='fixed5':models[gs,'initial'+str(a['seed'])]=fixed(channels,a['initial'],'actual91-common-initial')
  else:assert a['initial']==next(b['initial']for b in arms if b['method']=='fixed5'and b['seed']==a['seed'])
 models[gs,'unit']=fixed(channels,FOES['uniform'],'unfitted-unit-control');models[gs,'foe_random99031']=fixed(channels,FOES['random99031'],'frozen-random99031-foe')
 profile=build_ruleset_profile(c,EvaluationConfig());weights=[(profile.board_value_by_type if kind=='board'else profile.hand_value_by_base_type)[t]/1000 for kind,t in channels];models[gs,'rule_static_v2']=fixed(channels,weights,'existing-rule-only-generic-v2-material-control')
 for family in PLAN['families']:
  s=GameSession(c);rng=random.Random(PLAN['variants'][gs]['recipient']*1000000+family)
  for _ in range(4):
   if s.result.status.value!='ongoing':break
   aa=sorted(s.legal_actions(),key=repr);assert aa;s.submit(aa[rng.randrange(len(aa))])
  roots[gs,family]=dict(rule=gs,family=family,record=json.loads(serialize_game_record(s.to_record())),state_sha256=digest(s.state),witnesses_sha256=digest(s._search_witnesses),prefix_completed=s.state.ply_count,terminal_before_game=s.result.status.value!='ongoing',legal_root_actions=len(s.legal_actions())if s.result.status.value=='ongoing'else 0)
write_json(D/'roots.json',dict(rows=list(roots.values()),attempted_rules=16,families_per_rule=8,unfiltered=True));write_json(D/'models.json',dict(rows=[dict(rule=gs,label=label,checkpoint_id=cp.checkpoint_id,checkpoint=cp.to_dict())for(gs,label),cp in models.items()],scope='ALL48actual91unchangednumericaltablesreboundbytypeIDs+variantstatic/unit/fixedfoe, explicit256/no optimizer/defaultchange.'))
slots=[(gs,family,label,owner,foe)for gs in PLAN['rules']for family in PLAN['families']for label in PLAN['profiles']for foe in PLAN['foes']for owner in((0,)if label=='unit'and foe=='uniform'else(0,1))];assert len(slots)==7040;random.Random(PLAN['random_order_seed']).shuffle(slots);write_json(D/'slots.json',dict(slots=slots))
try:
 with(D/'queries.jsonl').open('x',encoding='utf8')as qlog,(D/'games.jsonl').open('x',encoding='utf8')as glog:
  for slot,(gs,family,label,owner,foe_name)in enumerate(slots):
   poll();c=compiled[gs];n=native[gs];root=roots[gs,family];s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])));assert digest(s.state)==root['state_sha256']and digest(s._search_witnesses)==root['witnesses_sha256'];candidate=models[gs,label];unit=models[gs,'unit'if foe_name=='uniform'else'foe_random99031'];engines={owner:SemanticSearchEngine(c,n,checkpoint=candidate,tt_megabytes=0),1-owner:SemanticSearchEngine(c,n,checkpoint=unit,tt_megabytes=0)};ending='HORIZON_UNKNOWN';localnodes=localqueries=0;current=dict(slot=slot,rule=gs,family=family,label=label,candidate_owner=owner,foe=foe_name,checkpoint_id=candidate.checkpoint_id,root_state_sha256=root['state_sha256'])
   try:
    for relative_ply in range(PLAN['horizon_after_prefix']):
     poll()
     if s.result.status.value!='ongoing':ending='ACTUAL_TERMINAL';break
     remaining=PLAN['limits']['global_cap_seconds']-(time.monotonic()-START)
     if remaining<2.:raise TimeoutError('FROZEN_GLOBAL_CAP_BEFORE_FULL_QUERY')
     before=(s.state,s.to_record(),s.history,s._search_witnesses);beforehash=digest(s.state);side=s.state.position.side_to_move;stamp=time.perf_counter();r=engines[side].search(s,SearchLimits(max_depth=2,max_nodes=8192,max_time_seconds=2.,quiescence_max_depth=0),root_window_pruning=False);elapsed=time.perf_counter()-stamp;assert before==(s.state,s.to_record(),s.history,s._search_witnesses);localqueries+=1;localnodes+=r.nodes;queries+=1;nodes+=r.nodes;committed=None;leaf=s
     if r.completed_depth<2:ending='SEARCH_LIMIT_UNKNOWN'
     elif r.declaration_id is not None:s.declare(r.declaration_id);committed=r.declaration_id
     elif r.action is None:ending='NO_ACTION_UNKNOWN'
     else:
      assert r.action in s.legal_actions();s.submit(r.action);committed=record_value(r.action)
     # The full final record plus root and ordered committed query edges permits
     # complete replay; hash full states rather than duplicating O(history) records.
     qlog.write(json.dumps(dict(slot=slot,relative_ply=relative_ply,actor=side,checkpoint_id=(candidate if side==owner else unit).checkpoint_id,before_sha256=beforehash,after_sha256=digest(s.state),returned_action=record_value(r.action),committed=committed,declaration_id=r.declaration_id,decision_line=record_value(r.decision_line),requested_depth=2,requested_nodes=8192,requested_seconds=2.,completed_depth=r.completed_depth,selective_depth=r.selective_depth,nodes=r.nodes,qnodes=r.qnodes,used_fallback=r.used_fallback,cause=r.termination_reason,score=r.score,kernel_seconds=r.elapsed_seconds,caller_seconds=elapsed),separators=(',',':'))+'\n');qlog.flush()
     if ending in('SEARCH_LIMIT_UNKNOWN','NO_ACTION_UNKNOWN'):break
    if s.result.status.value!='ongoing':ending='ACTUAL_TERMINAL'
   except(TimeoutError,InterruptedError)as exc:ending='INTERRUPTED_UNKNOWN';reason=repr(exc);status='INTERRUPTED'
   fresh=GameSession.replay(c,s.to_record());assert(fresh.state,fresh.history,fresh._search_witnesses,fresh.result)==(s.state,s.history,s._search_witnesses,s.result)
   current.update(ending=ending,result=record_value(s.result),reward=assess(s,owner),record=json.loads(serialize_game_record(s.to_record())),final_state_sha256=digest(s.state),final_witnesses_sha256=digest(s._search_witnesses),nodes=localnodes,queries=localqueries,relative_plies=s.state.ply_count-root['prefix_completed'],full_replay_equal=True);games.append(current);glog.write(json.dumps(current,separators=(',',':'))+'\n');glog.flush();current=None
   if len(games)%32==0:print('CLOSED_GAMES',len(games),'queries',queries,'seconds',round(time.monotonic()-START,3),flush=True)
   if qlog.tell()+glog.tell()>PLAN['limits']['max_output_bytes']:status='INTERRUPTED';reason='FROZEN_OUTPUT_CAP';break
   if status!='COMPLETE':break
except Exception as exc:status='ERROR';reason=repr(exc);traceback.print_exc()
result=dict(status=status,reason=reason,planned_physical=7040,returned_physical=len(games),unstarted_physical=7040-len(games),queries=queries,nodes=nodes,seconds=time.monotonic()-START,current_unclosed_slot=current,physical_with_queries=sum(g['queries']>0 for g in games),terminal_before_query=sum(g['queries']==0 and g['ending']=='ACTUAL_TERMINAL'for g in games),actual_terminal=sum(g['ending']=='ACTUAL_TERMINAL'for g in games),unknown=sum(g['reward']is None for g in games),scope='Registeredmovementrecombinationtwofixedopponent diagnostic on16predeclaredmovementvariants; all48frozeninitial/endpointmodels, nofit ornewtraining/learner/AUXchanges.7168logicalcellsinclude128Unitrolecopies, not7168independentphysicalgames. Fullstate/history/promotion/drop retained; U neverdraw, noproducer/capextension.');write_json(D/'result.json',result);print('CLOSED',json.dumps(result),flush=True)
