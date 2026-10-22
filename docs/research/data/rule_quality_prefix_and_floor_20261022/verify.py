import json,sys,zipfile,hashlib,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from scripts.research_record import write_record,record_value
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.transition import legal_successors
Z=zipfile.ZipFile('docs/research/data/rule_quality_prefix_and_floor_20261022/measurements.zip');P='.local_agent/rule-quality-prefix-next-20261022/';manifest=json.loads(Z.read('PROVENANCE.json'));assert Z.testzip()is None;assert all(hashlib.sha256(Z.read(x['member'])).hexdigest()==x['public_copy_sha256']for x in manifest['members']);read=lambda n:json.loads(Z.read(n));worlds={mode:{w['index']:w for w in read(path)['worlds']}for mode,path in [('pocket','.local_agent/rule-quality-survey-20261022/inputs.json'),('remove','.local_agent/rule-quality-capture-20261022/inputs.json')]};contexts={};seen={};out={'all_public_member_hashes':len(manifest['members']),'strict_records_compared':0,'unique_replayed_records':0,'history_plies':0,'new_match_games':0,'new_match_PV_edges':0,'dense_parent_frames':0,'opening_defense_cases':0,'next_inputs':0,'scope':'Actualpublished technicalcopy parsed/replayed with maintainedsharedCore. No independentengine,cleancheckout or fullchoice-valueproof claim.'};tick=time.perf_counter()
def verify(mode,w,rawrec,expected):
 rule=worlds[mode][w]['rule'];h=hashlib.sha256(json.dumps(rule,sort_keys=True).encode()).hexdigest()
 if h not in contexts:contexts[h]=compile_rule(ruleset_from_dict(rule))
 c=contexts[h];rec=deserialize_game_record(json.dumps(rawrec));key=(h,json.dumps(rawrec,sort_keys=True));out['strict_records_compared']+=1
 if key in seen:assert seen[key]==expected;return c,rec,None
 s=GameSession.replay(c,rec);assert record_value(s.state)==expected;seen[key]=expected;out['unique_replayed_records']+=1;out['history_plies']+=len(rec.actions);return c,rec,s
for mode,rp in [('pocket','.local_agent/rule-quality-random-20261022/results.json'),('remove','.local_agent/rule-quality-capture-random-20261022/results.json')]:
 for g in read(rp)['games']:
  c,rec,s=verify(mode,g['world'],g['final_record'],g['final_state'])
  if g['reused_from']is None:
   d=read(P+f'dense/{mode}-{g["slot"]:03d}.json');s=GameSession(c)
   for k,frame in enumerate(d['turns']):
    assert hashlib.sha256(json.dumps(record_value(s.state),sort_keys=True,separators=(',',':')).encode()).hexdigest()==frame['full_state_sha256'];out['dense_parent_frames']+=1
    if k<len(rec.actions):s.submit(rec.actions[k])
for folder in('floor-competence','floor-unit-control','crossed-price-next/full'):
 for slot in read(P+folder+'/results.json')['slots']:
  if slot['status']!='finished':continue
  g=read(P+folder+'/'+slot['receipt']);c,rec,s=verify('pocket',slot['world'],g['final_record'],g['final_state']);s=GameSession(c)
  for a,q in zip(rec.actions,g['queries']):
   if q['policy']=='D1':
    st=s.state
    for raw in q['decision']['principal_variation']:
     _,st=next((b,ch)for b,ch in legal_successors(st,c)if record_value(b)==raw);out['new_match_PV_edges']+=1
   s.submit(a)
  out['new_match_games']+=1
for g in read(P+'first-win/results.json')['games']:
 if g['exact_source_reuse']is not None:continue
 x=read(P+'first-win/'+g['receipt']);verify(g['mode'],g['world'],x['derived_record'],x['derived_full_state'])
for g in read(P+'terminal-floor-factorial/results.json')['games']:
 if g['exact_source_reuse']is not None:continue
 for cell in('B','C'):
  r=g['cells'][cell]
  if r['receipt']=='source_original':continue
  x=read(P+'terminal-floor-factorial/'+r['receipt']);verify(g['mode'],g['world'],x['full_record'],x['full_state'])
for x in read(P+'opening-resource/results.json')['differences']:
 verify('pocket',x['world'],x['pocket_record'],x['pocket_full_state']);verify('remove',x['world'],x['remove_record'],x['remove_full_state']);out['opening_defense_cases']+=1
for w in read(P+'prospective-leaf-next/inputs.json')['worlds']:
 c=compile_rule(ruleset_from_dict(w['rule']));s=GameSession.replay(c,deserialize_game_record(json.dumps(w['initial_record'])));assert record_value(s.state)==w['initial_full_state'];out['next_inputs']+=1
out['seconds']=time.perf_counter()-tick;out['all_passed']=True;write_record(Path('.local_agent/rule-quality-prefix-public-qualification.json'),out);print('PUBLICREPLAY',json.dumps(out))
