"""Replay the six current-segment batches; no producer/fitness reruns."""
import json,sys,hashlib,random,time
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(next(p for p in Path(__file__).resolve().parents if(p/'generic_chess').is_dir())))
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.transition import legal_successors
from scripts.research_record import record_value
BATCHES=('prospective-leaf-next','prospective-fixed-search','prospective-q1-fixed-search','prospective-node-ladder','prospective-node-q0-control','prospective-node-adjacent-rung')
def verify(root,batches=BATCHES):
 root=Path(root);inputpath=root/'prospective-leaf-next/inputs.json';raw=json.loads(inputpath.read_text(encoding='utf-8'));assert raw['status']=='PREPARED_NOTRUN'and raw['fitness_queries']==0;worlds={w['index']:w for w in raw['worlds']};assert len(worlds)==12 and not raw['failures'];contexts={};out={'physical_games':0,'queries':0,'history_plies':0,'pv_plies':0,'floor_returns':0,'Player_returns':0,'batches':{},'scope':'SharedCorefull-history/literalPV/policy/configqualification,not independentengine orscalarq/WDLproof. RawUNKNOWN neverreplaced.'};tick=time.perf_counter()
 for w,item in worlds.items():
  c=compile_rule(ruleset_from_dict(item['rule']));s=GameSession(c);assert record_value(s.state)==item['initial_full_state'];assert record_value(s.to_record())==item['initial_record'];contexts[w]=c
 for name in batches:
  d=root/name;r=json.loads((d/'results.json').read_text(encoding='utf-8'));assert r['status']=='CLOSED';assert (r.get('execution_registration',r['registration']))['input_sha256']==hashlib.sha256(inputpath.read_bytes()).hexdigest();count=0
  for slot in r['slots']:
   if slot['status']!='finished':continue
   g=json.loads((d/slot['receipt']).read_text(encoding='utf-8'));w=slot['world'];role=slot['candidate_role'];c=contexts[w];s=GameSession(c);rec=deserialize_game_record(json.dumps(g['final_record']));assert g['initial_record']==record_value(s.to_record());assert len(g['queries'])in(len(rec.actions),len(rec.actions)+1);seed=worlds[w]['config']['seed']*1009;rng={0:random.Random(seed),1:random.Random(seed+1)}
   for qi,q in enumerate(g['queries']):
    actor=s.state.position.side_to_move;assert q['root_ply']==s.state.ply_count and q['actor']==actor;out['queries']+=1
    if 'decision'in q:
     dec=q['decision'];assert dec['runtime_depth_balanced'];pv=s.state
     for a in dec['principal_variation']:_,pv=next((b,ch)for b,ch in legal_successors(pv,c)if record_value(b)==a);out['pv_plies']+=1
     if dec['result_source']=='root_immediate_win':assert pv.terminal_status.winner==actor
     if 'limits'in q:
      limits=q['limits']
      if name.startswith('prospective-node'):
       assert q['requested_depth']==64 and limits['max_time_seconds']is None;assert limits['max_nodes']==(r['registration']['arms'][slot['arm']]['nodes']if q['candidate']else(2048 if name.endswith('adjacent-rung')else 1024));assert dec['nodes']+dec['qnodes']<=limits['max_nodes'];assert limits['quiescence_max_depth']==(0 if name.endswith('q0-control')and q['candidate']else 1)
      elif name=='prospective-q1-fixed-search':assert limits['quiescence_max_depth']==(1 if q['candidate']else 4)
     if qi<len(rec.actions):assert dec['action']==record_value(rec.actions[qi])
     out['Player_returns']+=1
    else:
     assert name=='prospective-leaf-next'and q['policy']=='FLOOR';legal=list(legal_successors(s.state,c));win=next((a for a,ch in legal if ch.terminal_status.winner==actor),None)
     if qi<len(rec.actions):expected=win if win is not None else legal[rng[actor].randrange(len(legal))][0];assert expected==rec.actions[qi];assert q['floor']['winning_action_found']==(win is not None)
     out['floor_returns']+=1
    if qi<len(rec.actions):s.submit(rec.actions[qi]);out['history_plies']+=1
    else:assert g['censor']or g['failure']
   assert record_value(s.state)==g['final_state'];assert record_value(s.result)==g['terminal'];value=None if not g['eligible']or g['terminal']['status']in('ongoing','no_contest')else 0 if g['terminal']['winner']is None else 1 if g['terminal']['winner']==role else-1;assert g['candidate_utility_interval']==([value,value]if value is not None else[-1,1]);out['physical_games']+=1;count+=1
  out['batches'][name]={'physical_games':count,'planned_physical':len(r['slots']),'unattempted':r['unattempted_slots'],'source_failures':len(r['failures'])}
 out['seconds']=time.perf_counter()-tick;out['all_retained_games_passed']=True;return out
if __name__=='__main__':print(json.dumps(verify(sys.argv[1]),indent=2))
