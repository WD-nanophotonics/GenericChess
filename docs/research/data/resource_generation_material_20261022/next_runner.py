import json,sys,time,random,traceback,hashlib
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.research_record import write_record,record_value
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.movement import LeapAtom
from generic_chess.rules.schema import RuleSet,ruleset_from_dict,ruleset_to_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.session.session import GameSession
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.config import EvaluationConfig
from dataclasses import replace
class Adapter:
 def __init__(self,leaf,order):self.evaluate=leaf.evaluate;self.type_value=order.type_value;self.capture_order_value=order.capture_order_value
from generic_chess.ai.limits import SearchLimits
from rule_quality_floor_policy import floor_action
D=Path('.local_agent/legal-thinning-20261022-1020/opening-preference/material-leaf-next/common-unit-order-next')
if sys.argv[1]=='run':
 assert not(D/'results.json').exists();frozen=json.loads((D/'registration.json').read_text());assert hashlib.sha256((D/'inputs.json').read_bytes()).hexdigest()==frozen['input_sha256'];inputs=json.loads((D/'inputs.json').read_text(encoding='utf-8'));reg=json.loads((D/'registration.json').read_text(encoding='utf-8'));reg={**reg,'whole_cap_seconds':max(0,reg['whole_cap_seconds']-reg['preparation_seconds']),'preparation_only':False,'fitness_games':'EXECUTION_REGISTERED','Player_queries':'Seeactualresultsqueries','frozen_registration_sha256':hashlib.sha256((D/'registration.json').read_bytes()).hexdigest()};write_record(D/'execution-registration.json',reg);assert inputs['status']=='CLOSED';slots=[{'slot':i,'world':w,'pair':pair,'candidate_role':role,'status':'not_started','utility':[-1,1]}for i,(w,pair,role)in enumerate((w,pair,role)for w in reg['worlds']for pair in reg['pairs']for role in ((0,)if pair=='Static_self'else(0,1)))];order=list(range(len(slots)));random.Random(reg['shuffle_seed']).shuffle(order);out={'status':'RUNNING','registration':reg,'input_sha256':hashlib.sha256((D/'inputs.json').read_bytes()).hexdigest(),'execution_order':order,'slots':slots,'failures':[],'queries':0};write_record(D/'results.json',out);tick=time.perf_counter();contexts={}
 for ix in order:
  if time.perf_counter()-tick>=reg['whole_cap_seconds']:break
  slot=slots[ix];world=inputs['worlds'][slot['world']];role=slot['candidate_role'];t=time.perf_counter();row={**slot,'queries':[],'censor':None,'failure':None}
  if world['status']!='ready':slot['status']='setup_failed';slot['input_failure']=world.get('failure');write_record(D/'results.json',out);continue
  try:
   w=slot['world'];mode=reg['pair_modes'][slot['pair']];ctx=(w,mode);view=world['variants'][mode]
   if ctx not in contexts:contexts[ctx]=compile_rule(ruleset_from_dict(view['rule']))
   c=contexts[ctx];s=GameSession(c);assert record_value(s.state)==view['initial_state'];pols={role:reg['pairs'][slot['pair']][0],1-role:reg['pairs'][slot['pair']][1]};players={a:AlphaBetaPlayer(c,use_disk_cache=False)for a in (0,1)if pols[a]in('D1','D2')or pols[a].startswith('N')};seeds={int(a):v for a,v in world['source_seeds'][str(role)].items()};rng={a:random.Random(seeds[a])for a in (0,1)}
   base=players[role].evaluation_profile;saved=inputs['profiles_by_world'][str(w)];assert saved['Static']==record_value(base);es=Evaluator(c,base,EvaluationConfig());ob={t:0 if m.is_anchor else 1000 for t,m in c.support.type_metadata.items()};op=replace(base,board_value_by_type=ob,piece_profiles={t:replace(p,normalized_board_value=ob[t])for t,p in base.piece_profiles.items()});assert saved['UnitOrder']==record_value(op);eo=Evaluator(c,op,EvaluationConfig());players={a:AlphaBetaPlayer(c,evaluator_override=Adapter(es,eo),use_disk_cache=False)for a in (0,1)}
   if slot['pair']=='M0_vs_Static':
    saved=inputs['profiles_by_world'][str(w)];assert saved['Static']==record_value(base);board={t:0 for t in base.board_value_by_type};hand={t:0 for t in base.hand_value_by_base_type};unit=replace(base,board_value_by_type=board,hand_value_by_base_type=hand,promotion_gain_by_type=base.promotion_gain_by_type,median_non_anchor_value=base.median_non_anchor_value,piece_profiles={t:replace(p,normalized_board_value=board[t],normalized_hand_value=hand[t],promotion_option_value=p.promotion_option_value)for t,p in base.piece_profiles.items()});assert saved['M0']==record_value(unit);es=Evaluator(c,base,EvaluationConfig());eu=Evaluator(c,unit,EvaluationConfig());players[role]=AlphaBetaPlayer(c,evaluator_override=Adapter(eu,eo),use_disk_cache=False)
   row.update(initial_record=record_value(s.to_record()),policy_by_actor=pols,rng_seeds=seeds);path=D/f'game-{ix:03d}.json';write_record(path,row)
   while not s.state.terminal_status.is_terminal and s.state.ply_count<reg['caller_plies']:
    if time.perf_counter()-tick>=reg['whole_cap_seconds']:row['censor']='whole_cap';break
    a=s.state.position.side_to_move;policy=pols[a];row['current_record']=record_value(s.to_record());write_record(path,row);qt=time.perf_counter();q={'actor':a,'policy':policy,'root_ply':s.state.ply_count,'legal_count':len(s.legal_actions())}
    if policy=='RNG':legal=s.legal_actions();action=legal[rng[a].randrange(len(legal))]
    elif policy=='FLOOR':action,detail=floor_action(s,rng[a],float('inf'));q['floor']=detail
    else:
     dec=players[a].choose_action(s,SearchLimits(max_depth=64 if policy.startswith('N')else int(policy[1:]),**{**reg['limits'],'max_nodes':int(policy[1:])if policy.startswith('N')else 2048}));action=dec.action;q['decision']=record_value(dec)
    q.update(action=record_value(action),seconds=time.perf_counter()-qt);row['queries'].append(q);out['queries']+=1;write_record(path,row)
    if action is None:row['censor']='no_action';break
    s.submit(action)
   row.update(final_record=record_value(s.to_record()),final_state=record_value(s.state),terminal=record_value(s.result));row.pop('current_record',None);bad=any(q.get('decision',{}).get('native_legality_operational_failures',0) or q.get('decision',{}).get('result_source')in('fallback','legal_fallback','root_scan_fallback')for q in row['queries']);eligible=not(row['censor']or bad);res=s.result;value=None if not eligible or res.status.value in('ongoing','no_contest')else 0 if res.winner is None else 1 if res.winner==role else-1;row.update(status='finished',eligible=eligible,utility=[value,value]if value is not None else[-1,1],seconds=time.perf_counter()-t);write_record(path,row);slot.update(status='finished',receipt=path.name,terminal=row['terminal'],utility=row['utility'],plies=s.state.ply_count,eligible=eligible)
  except Exception as e:
   row.update(failure={'error':repr(e),'traceback':traceback.format_exc()},status='failed');write_record(D/f'game-{ix:03d}-failure.json',row);slot.update(status='failed',failure=row['failure']);out['failures'].append(slot.copy())
  write_record(D/'results.json',out)
  if ix%8==0 or slot['status']!='finished':print('FAMILY',ix,slot['world'],slot['pair'],slot['status'],slot['utility'],round(time.perf_counter()-tick,1),flush=True)
 out.update(status='CLOSED',seconds=time.perf_counter()-tick,unattempted=[s['slot']for s in slots if s['status']=='not_started']);write_record(D/'results.json',out);print('FAMILYCLOSED',Counter(s['status']for s in slots),out['queries'],round(out['seconds'],1),flush=True)
