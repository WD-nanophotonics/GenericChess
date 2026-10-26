"""Literal saved-return Core replay; never call Player or execute source capsules."""
import gzip,hashlib,json
from pathlib import Path
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.research_record import record_value,write_record
from scripts.verify_leaper_cost_profile import saved_returns
def load_json(path):
 return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())
def replay_saved(folder,inputs_file):
 original=gzip.decompress(inputs_file.read_bytes()) if inputs_file.suffix=='.gz' else inputs_file.read_bytes()
 source=load_json(folder/('source.json' if (folder/'source.json').exists() else 'source.json.gz'))
 assert hashlib.sha256(original).hexdigest()==source['input_original_sha256'], 'frozen full-input hash mismatch'
 raw=json.loads(original);inputs={r['id']:r for r in raw['rows']}
 assert len(inputs)==len(raw['rows']), 'duplicate full-input case id'
 checked=[];cache={};plies=0
 for r in saved_returns(folder):
  d=r['decision'];row=inputs[r['case_id']]
  assert row['fingerprint']==r['fingerprint']
  assert compute_fingerprint(ruleset_from_dict(row['RuleSet']))==row['fingerprint']
  # Identical whole decision/action/PV variants can share a literal replay only
  # under identical complete RuleSet/record bytes. No position projection.
  binding=json.dumps({'RuleSet':row['RuleSet'],'record':row['record'],'action':d['action'],'pv':d['principal_variation']},sort_keys=True,separators=(',',':'))
  digest=hashlib.sha256(binding.encode()).hexdigest()
  if digest not in cache:
   c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(row['RuleSet']))
   s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])))
   assert record_value(s.to_record())==row['record'],'full history replay changed'
   def recover(raw_action):
    matches=[a for a in s.legal_actions() if record_value(a)==raw_action]
    assert len(matches)==1,'not exactly one full legal action'
    return matches[0]
   if d['action'] is not None:recover(d['action'])
   for i,a in enumerate(d['principal_variation']):
    if i==0:assert a==d['action']
    s.submit(recover(a));plies+=1
   cache[digest]=len(d['principal_variation'])
  checked.append({'slot':r['slot'],'case_id':r['case_id'],'complete_context_action_PV_sha256':digest,'pv_plies':cache[digest]})
 return {'returns_checked':len(checked),'distinct_complete_context_action_PVs_replayed':len(cache),'actual_replayed_pv_plies':plies,'rows':checked,'Player_queries':0,'solver':0,'new_games':0,'limits':'Literal Core/PV compatibility, not WDL, equal-time strength or all-domain observer proof.'}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 result=replay_saved(a.folder,a.inputs);write_record(a.output,result);print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
