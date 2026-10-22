"""Replay the five current-segment batches; no producer/fitness reruns."""
import json,sys,hashlib,random,time
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path.cwd() if (Path.cwd()/'generic_chess').is_dir() else next(p for p in Path(__file__).resolve().parents if(p/'generic_chess').is_dir())))
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.transition import legal_successors
from scripts.research_record import record_value
BATCHES=('prospective-price-q0-next','prospective-price-q-interaction','prospective-price-q0-floor','prospective-price-q0-order','prospective-price-q0-remove')

def verify(root,batches=BATCHES):
 root=Path(root);inputpath=root/'prospective-price-q0-next/inputs.json';raw=json.loads(inputpath.read_text(encoding='utf-8'));assert raw['status']=='PREPARED_NOTRUN'and raw['Player_queries']==0;worlds={w['index']:w for w in raw['worlds']};assert len(worlds)==12 and not raw['failures'];contexts={};out={'physical_games':0,'queries':0,'history_plies':0,'pv_plies':0,'floor_returns':0,'Player_returns':0,'batches':{},'scope':'SharedCorefull-history/literalPV/policy/configqualification,not independentengine orscalarq/WDLproof. RawUNKNOWN neverreplaced.'};tick=time.perf_counter()
 for w,item in worlds.items():
  c=compile_rule(ruleset_from_dict(item['rule']));s=GameSession(c);assert record_value(s.state)==item['initial_full_state'];assert record_value(s.to_record())==item['initial_record'];contexts[w]=c
 for name in batches:
  d=root/name
  if name=='prospective-price-q0-remove':
   inputpath=d/'inputs.json';worlds={w['index']:w for w in json.loads(inputpath.read_text(encoding='utf-8'))['worlds']};contexts={w:compile_rule(ruleset_from_dict(v['rule']))for w,v in worlds.items()}
  r=json.loads((d/'results.json').read_text(encoding='utf-8'));assert r['status']=='CLOSED';assert (r.get('execution_registration',r['registration']))['input_sha256']==hashlib.sha256(inputpath.read_bytes()).hexdigest();count=0
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
      assert q['requested_depth']==64 and limits['max_time_seconds']is None and limits['max_nodes']==2048;assert dec['nodes']+dec['qnodes']<=2048;assert q['candidate']==(actor==role);expectedq=1 if name=='prospective-price-q-interaction'and q['candidate']else 0;assert limits['quiescence_max_depth']==expectedq
      if expectedq==0:assert dec['qnodes']==0
     if qi<len(rec.actions):assert dec['action']==record_value(rec.actions[qi])
     out['Player_returns']+=1
    else:
     assert name=='prospective-price-q0-floor'and q['policy']=='FLOOR'and not q['candidate']and actor!=role;legal=list(legal_successors(s.state,c));win=next((a for a,ch in legal if ch.terminal_status.winner==actor),None)
     if qi<len(rec.actions):expected=win if win is not None else legal[rng[actor].randrange(len(legal))][0];assert expected==rec.actions[qi];assert q['floor']['winning_action_found']==(win is not None)
     out['floor_returns']+=1
    if qi<len(rec.actions):s.submit(rec.actions[qi]);out['history_plies']+=1
    else:assert g['censor']or g['failure']
   assert record_value(s.state)==g['final_state'];assert record_value(s.result)==g['terminal'];value=None if not g['eligible']or g['terminal']['status']in('ongoing','no_contest')else 0 if g['terminal']['winner']is None else 1 if g['terminal']['winner']==role else-1;assert g['candidate_utility_interval']==([value,value]if value is not None else[-1,1]);out['physical_games']+=1;count+=1
  out['batches'][name]={'physical_games':count,'planned_physical':len(r['slots']),'unattempted':r['unattempted_slots'],'source_failures':len(r['failures'])}
 out['seconds']=time.perf_counter()-tick;out['all_retained_games_passed']=True;return out

def replay_analysis(extracted):
 import contextlib,io
 data=extracted/'data';source=extracted/'source'
 specs=[('rule_quality_price_q0_next_analysis.py','prospective-price-q0-next/paired-analysis.json'),('rule_quality_price_q_interaction_analysis.py','prospective-price-q-interaction/factorial-analysis.json'),('rule_quality_price_q0_floor_analysis.py','prospective-price-q0-floor/opponent-analysis.json'),('rule_quality_price_q0_order_analysis.py','prospective-price-q0-order/order-analysis.json'),('rule_quality_price_q0_remove_analysis.py','prospective-price-q0-remove/paired-analysis.json'),('rule_quality_capture_interaction.py','prospective-price-q0-remove/capture-interaction.json'),('rule_quality_price_censor_cost.py','prospective-price-q0-next/censoring-and-fullcost-bounds.json'),('rule_quality_precapture_context.py','prospective-price-q0-remove/pre-capture-context-diagnosis.json'),('rule_quality_q_mechanism_verify.py','prospective-q-mechanism/independent-qualified.json'),('rule_quality_q_pilots_verify.py','pilot-independent-qualified.json')]
 for filename,target in specs:
  before=json.loads((data/target).read_text(encoding='utf-8'));code=(source/filename).read_text(encoding='utf-8-sig').replace('.local_agent/rule-quality-prefix-next-20261022',data.as_posix())
  with contextlib.redirect_stdout(io.StringIO()):exec(compile(code,str(source/filename),'exec'),{'__name__':'_qualification_replay_','__file__':str(source/filename)})
  after=json.loads((data/target).read_text(encoding='utf-8'));before.pop('seconds',None);after.pop('seconds',None);assert before==after,filename
 # Recreate only the exact old34-case join, not its expensive tactical scans.
 support=extracted/'support';worlds={w['index']:w for w in json.loads((support/'old-survey-inputs.json').read_text())['worlds']};div=json.loads((support/'old-first-divergence.json').read_text());joined=json.loads((support/'first-divergence-tactical-cross-index.json').read_text());scans={json.loads(p.read_text())['input_sha256']:json.loads(p.read_text())for p in(support/'two-turn').glob('*.json')};matched=0
 for case,row in zip(div['cases'],joined['rows']):
  h=hashlib.sha256(json.dumps({'rule':worlds[case['world']]['rule'],'record':case['common_full_record']},sort_keys=True,separators=(',',':')).encode()).hexdigest();assert h==row['input_sha256']
  if h in scans:
   matched+=1;scan=scans[h];assert scan['root_state_sha256']==case['common_full_state_sha256']
   for label,key in [('Static','static_action'),('Unit','unit_action')]:
    child=next(x for x in scan['children']if x['action']==case[key]);assert child['child_terminal']['status']=='ongoing'and not child['opponent_winning_replies'];assert row['actions'][label]['classification']=='UNKNOWN'
  else:assert row['alignment']=='NO_EXACT_SAVED_SCAN'
 assert len(div['cases'])==len(joined['rows'])==34 and matched==10
 return {'analysis_replays':len(specs),'old_join_cases':34,'old_exact_matches':matched,'no_old_scans_or_fitness_rerun':True}

def main():
 import argparse,zipfile
 parser=argparse.ArgumentParser(description='Verify hashes, full Core histories/PVs and finite analyses; never run fitness producers.')
 parser.add_argument('--output',required=True,help='NEW disposable directory under your checkout; existing directory is refused.')
 args=parser.parse_args();here=Path(__file__).resolve().parent;manifest=json.loads((here/'manifest.json').read_text(encoding='utf-8'));archive=here/manifest['archive'];assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['sha256'];dest=Path(args.output).resolve();assert not dest.exists(),'Choose a new output directory; no overwrite/removal is performed.';dest.mkdir(parents=True)
 with zipfile.ZipFile(archive)as z:
  assert z.testzip()is None;assert set(z.namelist())==set(manifest['reviewed_member_hashes'])
  for name in z.namelist():
   target=(dest/name).resolve();assert target.is_relative_to(dest)and not Path(name).is_absolute();raw=z.read(name);assert hashlib.sha256(raw).hexdigest()==manifest['reviewed_member_hashes'][name];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
 result=verify(dest/'data');result['archive_members_checked']=len(manifest['reviewed_member_hashes']);result['analysis']=replay_analysis(dest);print(json.dumps(result,indent=2));return result
if __name__=='__main__':main()
