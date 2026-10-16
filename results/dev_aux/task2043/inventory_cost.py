"""Measured cost ceiling for an unqualified unused-type projection hypothesis."""
from pathlib import Path
from collections import Counter,defaultdict
import json
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_proof_rnb_bridge import actor_state
from scripts.generic_inventory_proof_transport import execution_differences,SetupTransportedNoWinFilter
OUT=Path('results/dev_aux/task2043')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def lines(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()]
def inspect(task):
 folder=Path('results/dev_aux')/task;plan=read(folder/'run-plan.json');c=compile_ruleset_for_execution(deserialize_ruleset(Path(plan['rules']).read_text(encoding='utf-8')));roots=read(Path(plan['roots']))['roots'];moves=lines(folder/'moves.jsonl');by=defaultdict(list)
 for x in moves:by[x['slot']].append(x)
 total_pn=scope_pn=total_sec=scope_sec=0;scope_steps=0;inventories=Counter();qualified=SetupTransportedNoWinFilter('results/dev_aux/task2044','results/dev_aux/task2045/coverage.json',c);closed_sec=0;closed_steps=0;closed_games=[]
 for game in lines(folder/'games.jsonl'):
  session=GameSession(c,roots[game['family']]['setup']);first_closed=None
  for step in by[game['slot']]:
   raw=actor_state(session.state);pieces=Counter(x.upper() for x in raw[:-1] if x!='.');key=''.join(sorted(x for x in raw[:-1] if x!='.'));inventories[key]+=1
   scoped=pieces['K']==2 and pieces['N']<=1 and set(pieces)<={'K','N'}
   total_pn+=step['proof_nodes'];total_sec+=step['proof_seconds']
   if scoped:scope_steps+=1;scope_pn+=step['proof_nodes'];scope_sec+=step['proof_seconds']
   if qualified.eligible(session):
    closed_sec+=step['proof_seconds'];closed_steps+=1
    if first_closed is None:first_closed=step['ply']
   record=session.to_record();encoded=dict(schema_version=1,ruleset_fingerprint=c.ruleset_fingerprint,actions=[step['choice']],resigned_by=None);action=deserialize_game_record(json.dumps(encoded)).actions[0];session.submit(action)
  if first_closed is not None:
   assert game['outcome']in('DRAW','UNKNOWN')
   closed_games.append(dict(slot=game['slot'],phase=game['phase'],entry_ply=first_closed,outcome=game['outcome'],remaining_physical_plies=game['moves']-first_closed))
 ref_plan=read(Path('results/dev_aux/task1895/plan.json'));reference=compile_ruleset_for_execution(deserialize_ruleset(Path(ref_plan['rules']).read_text(encoding='utf-8')))
 differences=execution_differences(reference,c);assert differences
 return dict(steps=len(moves),KK_or_singleN_steps=scope_steps,PN_nodes=total_pn,scoped_PN_nodes=scope_pn,PN_seconds=total_sec,scoped_PN_seconds=scope_sec,PN_seconds_fraction=scope_sec/total_sec if total_sec else 0,inventory_steps=dict(inventories),compiled_execution_differences=list(differences),filter_adopted=False,fresh_KK_N_B_noWIN_steps=closed_steps,fresh_KK_N_B_PN_seconds=closed_sec,fresh_noWIN_entry_games=closed_games)
def main():
 result=dict(status='PASS_DESCRIPTIVE_COST_AND_IRREVERSIBLE_NOWIN_ENTRY',cohorts={t:inspect(t) for t in ('task2020','task2037')},hypothesis='Original KKN projection hypothesis preserved below; extended with freshly proven2044 KK/N/B eligibility and irreversible noWIN entry. Under complete remove-only rules with no mechanism to create absent types, an independently verified restricted-inventory semantic projection might reuse KK/KKN noWIN proof. Current exact whole-compiler gate correctly rejects extraB. No general unused-type projection implemented; fresh actualKRNB census removes the relevant ambiguity for these exact classes only.',scope='Actual spent PN work is only an optimistic cost ceiling. Old KRN compiler differences block old-census adoption. Fresh2044qualification used for entry audit only; initialization/replay costs still count. No6boardtransfer, WDL reward change or new Native/proof/census execution. Future work justified only if saving meaningful and projection sound.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:{x:v[x] for x in ('steps','KK_or_singleN_steps','PN_seconds','scoped_PN_seconds','PN_seconds_fraction','compiled_execution_differences')} for k,v in result['cohorts'].items()}))
if __name__=='__main__':main()
