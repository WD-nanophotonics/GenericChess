"""Verify this fixed technical capsule; no fitness/search/train calls."""
from __future__ import annotations
import gzip,hashlib,json,math,time
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.transition import legal_successors
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from scripts.research_record import record_value
HERE=Path(__file__).resolve().parent

def digest(v):
 return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def verify(folder=HERE):
 tick=time.perf_counter();manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'));compressed=(folder/'observations.json.gz').read_bytes();assert hashlib.sha256(compressed).hexdigest()==manifest['sha256'];decoded=gzip.decompress(compressed);assert hashlib.sha256(decoded).hexdigest()==manifest['decoded_sha256'];p=json.loads(decoded);contexts={};counts={'new_games':0,'history_plies':0,'literal_PV_edges':0,'cold_queries':0,'cold_PV_edges':0,'offline_games':0,'offline_roots':0,'offline_contrast_checks':0};known=defaultdict(set)
 def context(rule):
  key=json.dumps(rule,sort_keys=True,separators=(',',':'))
  if key not in contexts:contexts[key]=compile_rule(ruleset_from_dict(rule))
  return contexts[key]
 for key,g in p['games'].items():
  run=p['runs'][g['batch']];slot=next(x for x in run['results']['slots']if x['slot']==g['source_slot']);assert slot['game_id']==key and slot['execution']=='new_physical';mode=run['results']['registration']['pair_modes'][slot['pair']];view=run['inputs']['worlds'][slot['world']]['variants'][mode];c=context(view['rule']);s=GameSession(c);assert digest(record_value(s.state))==g['initial_state_sha256'];assert record_value(s.to_record())==g['initial_record'];rec=deserialize_game_record(json.dumps(g['final_record']));assert len(rec.actions)==len(g['queries'])
  for q,a in zip(g['queries'],rec.actions):
   assert q['actor']==s.state.position.side_to_move and q['root_ply']==s.state.ply_count;assert record_value(a)==q['action']==q['decision']['action'];assert q['legal_count']==len(s.legal_actions());d=q['decision'];assert d['runtime_depth_balanced'];assert d['nodes']+d['qnodes']<=2048 and d['qnodes']==0;pv=s.state
   for raw in d['principal_variation']:
    _,pv=next((act,ch)for act,ch in legal_successors(pv,c)if record_value(act)==raw);counts['literal_PV_edges']+=1
   if d['result_source']=='root_immediate_win':assert pv.terminal_status.winner==q['actor']
   s.submit(a);counts['history_plies']+=1
  assert digest(record_value(s.state))==g['final_state_sha256'];assert record_value(s.result)==g['terminal'];value=None if not g['eligible']or g['terminal']['status']in('ongoing','no_contest')else 0 if g['terminal']['winner']is None else 1 if g['terminal']['winner']==g['candidate_role']else-1;assert g['utility']==([value,value]if value is not None else[-1,1]);counts['new_games']+=1
 for name,run in p['runs'].items():
  for slot in run['results']['slots']:
   if slot['status']!='reused':continue
   assert name=='preference';g=p['games'][slot['game_id']];assert g['batch']=='legal';assert g['utility']==slot['utility'];assert slot['source_sha256']==g['source_record_sha256'];assert slot['world']==g['world']and slot['candidate_role']==g['candidate_role'];a=dict(run['inputs']['worlds'][slot['world']]['variants']['preferred']['rule']);b=dict(p['runs']['legal']['inputs']['worlds'][slot['world']]['variants']['full']['rule']);a.pop('metadata',None);b.pop('metadata',None);assert a==b;assert run['registration']['limits']==p['runs']['legal']['registration']['limits']
 cold=p['analyses']['material_cold'];roots={x['world']:x for x in p['analyses']['material_cold_inputs']['cases']};mrun=p['runs']['material'];leaf_checks=0
 for q in cold['queries']:
  root=roots[q['world']];rule=mrun['inputs']['worlds'][q['world']]['variants']['preferred']['rule'];c=context(rule);s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])));assert record_value(s.state)==root['full_state'];d=q['decision'];pv=s.state;assert d['nodes']+d['qnodes']<=2048 and d['runtime_depth_balanced']
  for raw in d['principal_variation']:
   _,pv=next((a,ch)for a,ch in legal_successors(pv,c)if record_value(a)==raw);counts['cold_PV_edges']+=1
  counts['cold_queries']+=1
 # Offline source records are read from the fixed, already-public parent capsule;
 # only the 256 needed games are replayed, not its other closed campaigns.
 root=Path(__file__).resolve()
 repo=next(x for x in root.parents if(x/'generic_chess').is_dir())
 prior_path=repo/p['prior_packet']['path'];pb=prior_path.read_bytes();assert hashlib.sha256(pb).hexdigest()==p['prior_packet']['sha256'];prior=json.loads(gzip.decompress(pb));old={(g['batch'],g['slot']):g for g in prior['games']};tags={'discard':'small_ladder','resource_controls':'resource_utility','resource_direct':'resource_direct'};ev={}
 for row in p['offline']['results']['games']:
  if row['status']!='measured':continue
  g=old[tags[row['source']],row['slot']];c=context(prior['rules'][g['ruleset_fingerprint']]['rule']);fp=c.ruleset_fingerprint
  if fp not in ev:
   base=build_ruleset_profile(c,EvaluationConfig());board={t:0 if md.is_anchor else 1000 for t,md in c.support.type_metadata.items()};hand={t:0 if md.is_anchor or base.hand_value_by_base_type[t]==0 else 900 for t,md in c.support.type_metadata.items()};unit=replace(base,board_value_by_type=board,hand_value_by_base_type=hand,promotion_gain_by_type={t:0 for t in board},median_non_anchor_value=1000,piece_profiles={t:replace(z,normalized_board_value=board[t],normalized_hand_value=hand[t],promotion_option_value=0)for t,z in base.piece_profiles.items()});ev[fp]=(Evaluator(c,base,EvaluationConfig()),Evaluator(c,unit,EvaluationConfig()))
  es,eu=ev[fp];s=GameSession(c);rec=deserialize_game_record(json.dumps(g['final_record']));record=p['offline']['records'][f'{row["source"]}/{row["slot"]:03d}'];rr=record['roots'];assert len(rr)==len(rec.actions)
  for x,a in zip(rr,rec.actions):
   sg=1 if s.state.position.side_to_move==0 else-1;assert es.evaluate(s.state)*sg==x['Static']and eu.evaluate(s.state)*sg==x['Unit'];assert s.state.ply_count==x['ply']
   for t in(1000,2000):
    for j,n in enumerate(('Static','Unit')):assert abs(x['probability'][str(t)][j]-(.5+.5*math.tanh(x[n]/(2*t))))<1e-14
   if row['known_terminal']:known[digest(record_value(s.state))].add(row['actor0_target'])
   s.submit(a);counts['offline_roots']+=1
  for t in(1000,2000):
   ys=[row['actor0_target']]if row['known_terminal']else[0,.5,1];v=[sum((x['probability'][str(t)][1]-y)**2-(x['probability'][str(t)][0]-y)**2 for x in rr)/len(rr)for y in ys];b=row['metrics'][str(t)]['contrast'];assert abs(min(v)-b[0])<1e-12 and abs(max(v)-b[1])<1e-12;counts['offline_contrast_checks']+=1
  counts['offline_games']+=1
 counts['conflicting_complete_states']=sum(len(v)>1 for v in known.values());assert counts['conflicting_complete_states']==59
 assert counts['new_games']==p['counts']['new_physical_games'];assert counts['history_plies']==p['counts']['new_Player_queries'];assert counts['literal_PV_edges']==p['counts']['new_literal_PV_edges'];assert counts['cold_queries']==24 and counts['cold_PV_edges']==99;assert counts['offline_roots']==13805 and counts['offline_games']==256
 return {'passed':True,**counts,'seconds':time.perf_counter()-tick,'limitation':'SharedproductionCore;noindependentengine,WDLoracle,newfitnessorlearning.'}
if __name__=='__main__':print(json.dumps(verify(),indent=2))
