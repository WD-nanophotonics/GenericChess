"""Input-only KRNB Native profile/legality feasibility, not value learning."""
from pathlib import Path
import json,hashlib,time,copy,sys
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from scripts.generic_session_native_material import _load_transport
from scripts.generic_proof_rnb_bridge import uci
from results.dev_aux.task2025.provider import KRNB6UnitProvider
OUT=Path('results/dev_aux/task2025')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,d):
 with(OUT/n).open('x',encoding='utf-8')as f:json.dump(d,f,indent=2)
def prepare():
 rules='results/dev_aux/task2024/rules.json';roots='results/dev_aux/task2024/feasibility.json';rr=json.loads(Path(roots).read_text());assert len(rr['roots'])==8
 c=compile_ruleset_for_execution(deserialize_ruleset(Path(rules).read_text()));base=Path('results/dev_aux/task1939/variant.ini').read_text().split('[aux61unit_')[0].replace('aux61base','aux68B6base').replace('maxFile = 4','maxFile = 6').replace('maxRank = 4','maxRank = 6').replace('promotionRank = 4','promotionRank = 6').replace('k3/4/4/3K','k5/6/6/6/6/5K');names={};profiles=[]
 for b in (360,720,1440):
  values=(1260,720,b,720);name=f'aux68B6_{b}';names[str(values)]=name;profiles.append(values);base+=f'\n[{name}:aux68B6base]\npieceValueMg = p:720 n:720 b:{b} r:1260 q:1440\npieceValueEg = p:720 n:720 b:{b} r:1260 q:1440\n'
 with(OUT/'variant.ini').open('x',encoding='utf-8')as f:f.write(base)
 old=json.loads(Path('results/dev_aux/task1997/run-plan.json').read_text());native=copy.deepcopy(old['native_plan']);native.update(fingerprint=c.ruleset_fingerprint,variant_ini=(OUT/'variant.ini').as_posix(),variant_names=names,seconds_cap=120,max_go=48)
 native['files']={k:v for k,v in native['files'].items()if not k.endswith('rules.json')and not k.endswith('variant.ini')};native['files'].update({rules:sha(rules),(OUT/'variant.ini').as_posix():sha(OUT/'variant.ini'),'results/dev_aux/task2025/provider.py':sha('results/dev_aux/task2025/provider.py')})
 states=[]
 for r in rr['roots']:
  for prefix in (False,True):
   s=GameSession(c,r['setup'])
   if prefix:s.submit(s.legal_actions()[0])
   states.append(dict(index=len(states),family=r['family'],prefix=prefix,record=json.loads(serialize_game_record(s.to_record())),state_sha=hashlib.sha256(repr(s.state).encode()).hexdigest()))
 plan=dict(status='FROZEN_BEFORE_NATIVE',question='Can existing materialNative support B with exact fullSession/literal legality on6x6before any futurevaluelearning?',rules=rules,roots=roots,states=states,profiles=profiles,native_plan=native,seconds_cap=120,expected_perfts=48,expected_search_go=48,search_nodes=64,normal_seconds=.1,source_sha={f:sha(f)for f in [rules,roots,'results/dev_aux/task2025/provider.py','results/dev_aux/task2025/qualify.py','scripts/generic_session_native_material.py','results/dev_aux/task1866/unit_panel.py','scripts/generic_royal_actor.py','scripts/generic_proof_rnb_bridge.py']},scope='ALL8pricefreeKRNB6roots/fresh+firstCorelegalprefix/3mechanicalBprofiles. R1260/N720prioranchorlockedbeforecurrentDEV, notselectedusingBlabels.0games/W-L/fitness/prooffilter/training. ExactpinnedKRNB6adapteronly, originalKRNproductsourceunchanged; nofullgeneratedNativeclaim. NativePV isnotCoreWDL/equal-workoptimality.')
 save('plan.json',plan);print(json.dumps(dict(states=16,profiles=3,perfts=48,go64=48,training_games=0)))
def run():
 p=json.loads((OUT/'plan.json').read_text());assert all(sha(f)==h for f,h in p['source_sha'].items());c=compile_ruleset_for_execution(deserialize_ruleset(Path(p['rules']).read_text()));t=_load_transport();beg=time.perf_counter();provider=KRNB6UnitProvider(p['native_plan'],OUT/'run',stop=lambda:t.stop_check(Path.cwd()));rows=[];perfts=[]
 try:
  provider.start()
  for state in p['states']:
   s=GameSession.replay(c,deserialize_game_record(json.dumps(state['record'])))
   for values in p['profiles']:
    n=provider.perft_one(s,values);perfts.append(dict(state=state['index'],values=values,legal=n))
  with(OUT/'queries.jsonl').open('x')as f:
   for state in p['states']:
    s=GameSession.replay(c,deserialize_game_record(json.dumps(state['record'])))
    for values in p['profiles']:
     before=s.to_record();action,nodes=provider.choose(s,s.state,values,p['search_nodes'],p['normal_seconds'],lambda:time.perf_counter()-beg>=120)
     assert s.to_record()==before and action in s.legal_actions();row=dict(state=state['index'],values=values,action=uci(action),reported_nodes=nodes,state_sha=state['state_sha']);f.write(json.dumps(row)+'\n');rows.append(row)
 finally:provider.close()
 assert len(rows)==len(perfts)==48 and time.perf_counter()-beg<120
 save('result.json',dict(status='PASS_SCOPED_KRNB_NATIVE_FEASIBILITY',perfts=perfts,queries=len(rows),games=0,learning=0,seconds=time.perf_counter()-beg,source_unchanged=all(sha(f)==h for f,h in p['source_sha'].items()),scope=p['scope']));print(json.dumps(dict(perfts=48,queries=48,games=0,seconds=time.perf_counter()-beg)))
if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()
