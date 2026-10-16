"""Cost attribution on actual audited trajectories, not new reward labels."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from generic_chess.core.actions import action_to_dict
from scripts.generic_inventory_proof_transport import SetupTransportedNoWinFilter
BASE=Path('results/dev_aux');OUT=BASE/'task2013'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p):return [json.loads(x)for x in Path(p).read_text().splitlines()]
def one(task):
 root=BASE/f'task{task}';p=read(root/'run-plan.json');g=lines(root/'games.jsonl');m=lines(root/'moves.jsonl');by=defaultdict(list)
 for x in m:by[x['slot']].append(x)
 c=compile_ruleset_for_execution(deserialize_ruleset(Path(p['rules']).read_text()));filt=SetupTransportedNoWinFilter(BASE/'task1895',BASE/'task1896/coverage.json',c);parents={x['slot']:x for x in lines(p['parent_games'])}if p.get('conditional_continuation')else{}
 roots=read(p['roots'])['roots'];phases=Counter();counts=Counter();finals=Counter()
 for row in g:
  record=deserialize_game_record(json.dumps(row['record']));s=GameSession.replay(c,deserialize_game_record(json.dumps(parents[row['parent_slot']]['record'])))if parents else GameSession(c,roots[row['family']]['setup'])
  for x in by[row['slot']]:
   assert hashlib.sha256(repr(s.state).encode()).hexdigest()==x['before_state_sha']
   eligible=filt.eligible(s);counts['actual_decisions']+=1;counts['actual_proof_visits']+=x['proof_nodes']
   if eligible:
    counts['eligible_decisions']+=1;counts['eligible_actual_proof_visits']+=x['proof_nodes'];counts['eligible_native_calls']+=x['source']=='EXTERNAL_SEARCH';assert x['source']not in ('PROOF','PROOF_CONTINUATION')
   for k in ('admission_seconds','proof_seconds','verification_seconds','normal_seconds','seconds','commit_seconds'):phases[k]+=x[k]
   action=record.actions[x['ply']];assert action_to_dict(action)==x['choice'];s.submit(action);assert hashlib.sha256(repr(s.state).encode()).hexdigest()==x['after_state_sha']
  assert hashlib.sha256(repr(s.state).encode()).hexdigest()==row['final_state_sha']
  inventory=''.join(sorted(piece.current_type_id for piece in s.state.position.board if piece is not None));finals[(row['outcome'],s.result.status.value,inventory)]+=1
 wall=sum(x['seconds']for x in g)
 return dict(task=task,parent_cases=len(g),new_moves=len(m),recorded_case_seconds=wall,phase_seconds=dict(phases),counts=dict(counts),eligible_fraction_of_actual_proof_visits=counts['eligible_actual_proof_visits']/max(1,counts['actual_proof_visits']),actual_terminal_inventory=[dict(outcome=k[0],status=k[1],inventory=k[2],count=v)for k,v in sorted(finals.items())],scope='Exactfixedcompiledsetuptransport eligibility on alreadyphysicalreplayed states. Counts are observedcost opportunities, not re-run filteredpaths, guaranteed wall savings or theoreticalWDL. Flatphasefields only; fillverification nestedinsideproof not addedtwice. Terminalinventorydescription earns no reward.')
def run():
 assert read(BASE/'task1998/result.json')['status']=='PASS_COMMON_POLICY_FRESH_LEARNING'
 assert read(BASE/'task2006/result.json')['status']=='PASS_PREDECLARED_CONDITIONAL_H48'
 assert read(BASE/'task2012/result.json')['status']=='PASS_PREDECLARED_ACTUAL_RULE_COMPLETION'
 result=dict(status='PASS_ACTUAL_TRAJECTORY_COST_ATTRIBUTION',studies=[one(x)for x in(1997,2005,2011)],new_Native_or_proof_calls=0,source='Actual Core/fullhistory replay, compiledexecutionfield equality and retainednode/timerreceipts; normal/PN visits remain distinctunits. Not selectingroot/price/horizonfromterminalinventory.')
 with(OUT/'result.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps([{k:v for k,v in x.items()if k not in ('actual_terminal_inventory','scope')}for x in result['studies']]))
if __name__=='__main__':run()
