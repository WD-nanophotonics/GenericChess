"""Actual admission-cost feasibility for exact repeated training roots ONLY."""
from pathlib import Path
from collections import Counter
import json,time,hashlib
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2279')
def run():
 assert not(OUT/'started.json').exists();start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());(OUT/'started.json').write_text(json.dumps(dict(cap_seconds=120,method='PREDECLARED_IN_SAMPLE_INCREMENTAL_ONLY',purpose='Costqualificationnotpricebenefit/cacheadoption')));folder=Path('results/dev_aux/task2273');inputs=json.loads((folder/'inputs.json').read_text());queries=[json.loads(x)for x in(folder/'queries.jsonl').read_text().splitlines()];certs={r['query']:r for r in map(json.loads,(folder/'certificates.jsonl').read_text().splitlines())};train=[json.loads(x)for x in Path('results/dev_aux/task2261/games.jsonl').read_text().splitlines()if json.loads(x)['phase']=='TRAIN'];oldroots={r['family']:r for r in json.loads(Path('results/dev_aux/task2261/inputs.json').read_text())['roots']};newroots=json.loads(Path('results/dev_aux/task2271/inputs.json').read_text())['roots'];rows=[];allcost=0.;checks=0
 def cancel():stop();return time.perf_counter()-start>=120
 for q in [q for q in queries if q['method']=='INCREMENTAL']:
  raw=inputs[q['entry']];root=oldroots[q['family']];matches=[g for g in train if g['family']==q['family']];assert len(matches)==20 and root['record']==raw['root_record'];row=dict(family=q['family'],query=q['index'],generic_discovery_verified=q['verified'],observed_discovery_seconds=q['measured_seconds'],exact_saved_TRAIN_games=20,actual_reuse_admissions=0,actual_reuse_admission_seconds=0.,new32_exact_root_matches=sum(r['record']==raw['root_record']and r['state_sha']==raw['root_state_sha']for r in newroots))
  allcost+=q['measured_seconds']
  if q['verified']:
   for g in matches:
    if cancel():raise TimeoutError('qualification_cap')
    tick=time.perf_counter();c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])));cert=decode_graph(s,certs[q['index']]['certificate']);receipt=verify_graph(s,cert,max_nodes=32768,seconds=.5,cancel=cancel);assert receipt['verified'];cursor=GraphStrategyCursor(s,cert,max_nodes=32768,seconds=.5,cancel=cancel);assert cursor.choose(s)is not None;row['actual_reuse_admission_seconds']+=time.perf_counter()-tick;row['actual_reuse_admissions']+=1;checks+=1
   row['illustrative_repeated_discovery_projection']=20*q['measured_seconds'];row['observed_one_discovery_plus_20_admissions']=q['measured_seconds']+row['actual_reuse_admission_seconds']
  rows.append(row)
 result=dict(status='COMPLETE_EXACT_ROOT_REUSE_COST_QUALIFICATION_NO_ADOPTION',method_contexts=4,verified_contexts=sum(r['generic_discovery_verified']for r in rows),actual_double_verification_admissions=checks,all_four_discovery_seconds=allcost,rows=rows,seconds=time.perf_counter()-start,scope='ExactsameFP/GameRecord/root only: 20realTRgamesperroot, BOTHindependentandcurrentcursor checks+compile/replay+choosepaidfreshforeach. GenericINCREMENTALmethodfixed, ALL4successfulandfailedcontextsretained, no cheapest-successalgorithmselection. Projected20*singleobserveddiscovery isILLUSTRATIVE, NOTremeasuredspeedup/gameoutcome. New32validationexactrootmatches0; no broadPosition/ruletransport/cachehitclaim orbank/defaultadoption. RootWINproofwouldoverridepriceandcanremovelearningcontrast inthesolvedsubset; no pricerewardclaim/no newgames/fit. Conditionalengineeringfeasibilityonly.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
