"""Independent common-state/profile/legality grouping; no search or fit."""
from pathlib import Path
from collections import defaultdict,Counter
import json,hashlib,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_proof_rnb_bridge import actor_state,uci
ROOT=Path('results/dev_aux/task1866');OUT=Path('results/dev_aux/task1867')
def main():
 start=time.perf_counter();p=json.loads((ROOT/'plan.json').read_text());done=json.loads((ROOT/'completion.json').read_text());rows=[json.loads(x) for x in (ROOT/'queries.jsonl').read_text().splitlines()];assert done['status']=='COMPLETE' and len(rows)==p['expected_go']==2304
 c=compile_ruleset_for_execution(deserialize_ruleset(Path(p['rules']).read_text()));actor=RoyalActor(4);states={};groups=defaultdict(list)
 for spec in p['states']:
  s=GameSession.replay(c,deserialize_game_record(json.dumps(spec['record'])));root=GameSession(c,s.to_record().initial_setup_key);command='position fen '+actor.fen(actor_state(root.state))+(' moves '+' '.join(uci(a) for a in s.to_record().actions) if s.to_record().actions else '')
  states[spec['index']]=(set(uci(a) for a in s.legal_actions()),hashlib.sha256(repr(s.state).encode()).hexdigest(),command)
  assert set(dict(actor.moves(actor_state(s.state))))==states[spec['index']][0]
 for slot,row in zip(p['slots'],rows):
  assert all(slot[k]==row[k] for k in slot);legal,digest,command=states[row['state']];assert row['move'] in legal and row['state_sha']==digest and row['position']==command
  assert row['record']==p['states'][row['state']]['record']
  if row['control']=='depth5':assert row['completed_depth']==5
  groups[row['state'],row['profile']['ratio'],row['control']].append(row)
 # Counterfactual units share exactlysame input and requestedgo; completed
 # Native depth and actualnodes may vary. Such variation is the tested effect.
 summaries=[];examples=[]
 for control in ('nodes64','nodes4096','depth5'):
  selected=[xs for k,xs in groups.items() if k[2]==control];assert len(selected)==192 and all(len(xs)==4 for xs in selected)
  changed=[xs for xs in selected if len({x['move'] for x in xs})>1]
  summaries.append(dict(control=control,quartets=len(selected),different_actions=len(changed),same_reported_depth_different_actions=sum(len({x['completed_depth'] for x in xs})==1 for xs in changed),different_depths=sum(len({x['completed_depth'] for x in xs})>1 for xs in selected),node_overshoots=sum(x['reported_nodes']>int(control[5:]) for xs in selected for x in xs) if control.startswith('nodes') else None,depth_range=[min(x['completed_depth'] for xs in selected for x in xs),max(x['completed_depth'] for xs in selected for x in xs)]))
  for xs in changed[:8]:examples.append(dict(state=xs[0]['state'],family=p['states'][xs[0]['state']]['family'],ratio=xs[0]['profile']['ratio'],control=control,rows=[{k:x[k] for k in ('slot','profile','move','reported_nodes','completed_depth','score_kind','score_value')} for x in xs]))
 events=[json.loads(x) for x in (ROOT/'run/transport.jsonl').read_text().splitlines()];sent=[x for x in events if x['event']=='SENT'];intents=[x for x in events if x['event']=='INTENT'];chosen=[x for x in events if x['event']=='CHOICE'];profiles=[x for x in events if x['event']=='PROFILE'];assert len(sent)==len(intents)==len(chosen)==2304
 for i,(s,a,b,row) in enumerate(zip(sent,intents,chosen,rows)):
  assert s['query']==a['query']==b['query']==i and a['slot']==row['slot'] and a['position']==row['position'] and a['profile']==row['profile'] and b['move']==row['move'] and b['reported_nodes']==row['reported_nodes']
 result=dict(status='PASS_COMPLETE_INPUT_PROFILE_ACTION_BINDINGS',queries=len(rows),full_states=len(states),profiles=len(profiles),perfts=done['perft'],summaries=summaries,examples=examples,seconds=time.perf_counter()-start,native_seconds=done['seconds'],source_unchanged_at_completion=done['source_unchanged'],conclusion='Commonunits can change policy iff changedaction quartets>0; samereporteddepth differences cannot be explained solely by more completed depth. This doesnot distinguish idealmaterialties from suboptimal actions, prove winimprovement, isolate one pruning heuristic, select units, or invalidate old source-pinned conditionalresults. Current100ms actualpolicy differs from these fixednode/depth controls.')
 with (OUT/'unit_report.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k!='examples'}))
if __name__=='__main__':main()
