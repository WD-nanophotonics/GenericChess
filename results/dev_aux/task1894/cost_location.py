"""TRAIN-only cost localization for an independent-price sparse proof trigger."""
from pathlib import Path
from collections import Counter,defaultdict
import json,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
OUT=Path('results/dev_aux/task1894')
def run():
 folder=Path('results/dev_aux/task1881');p=json.loads((folder/'run-plan.json').read_text());c=compile_ruleset_for_execution(deserialize_ruleset(Path(p['rules']).read_text()));roots=json.loads(Path(p['roots']).read_text())['roots'];games=[json.loads(x) for x in (folder/'games.jsonl').read_text().splitlines()];allmoves=defaultdict(list)
 for line in (folder/'moves.jsonl').read_text().splitlines():
  m=json.loads(line);allmoves[m['slot']].append(m)
 plan=dict(status='DECLARED_BEFORE_COST_HISTOGRAM',threshold=2,question='Does a fixed at-most-two nonanchor-actor trigger locate most successful proofadoptions while avoiding expensive UNKNOWNproofs?',input_scope='Only96alreadyexposedTRAIN1881 games; NO DEVtriggerselection.',trigger='Count currentnonanchorboardpieces plus nonanchorhandcounts, no prices; allow owneddeclarations regardlesscount, ALWAYS continue existingverifiedcursor. Newproof only if count<=2 orowneddeclarations. This is an optionalcaller schedule, not proofsemantics, genericWDL theorem or quantityreward.',decision='If TRAINshows substantial missedPROOFadoptions, do not pretend exactpolicy equivalence. Only a bounded new pairedactualgame pilot could assess cost/strength. No automaticdefaultadoption or oldreward relabel.')
 with (OUT/'plan.json').open('x') as f:json.dump(plan,f,indent=2)
 start=time.perf_counter();bins=defaultdict(Counter);details=[]
 for game in games:
  if game['phase']!='TRAIN':continue
  s=GameSession(c,roots[game['family']]['setup'])
  for m in allmoves[game['slot']]:
   candidate=m['side']==game['candidate_side'];count=sum(not c.types_by_id[x.current_type_id].is_anchor for x in s.state.position.board if x is not None)+sum(n for hand in s.state.position.hands for tid,n in hand.counts if not c.types_by_id[tid].is_anchor);owns=any(d.owner==s.state.position.side_to_move for d in c.declarations);eligible=count<=2 or owns
   if candidate:
    b=bins[count];b['moves']+=1;b['proof_nodes']+=m['proof_nodes'];b['proof_seconds']+=m['proof_seconds'];b['queries']+=m.get('logical_status')!='NOT_QUERIED';b['PROOF_adoptions']+=m['source']=='PROOF';b['UNKNOWN_queries']+=m.get('logical_status')=='UNKNOWN';b['logical_nodes']+=m.get('logical_proof_nodes',0)
    if m['source']=='PROOF' and not eligible:details.append(dict(slot=game['slot'],family=game['family'],role=game['candidate_side'],ratio=game['ratio'],ply=m['ply'],nonanchors=count,proof_nodes=m['proof_nodes'],proof_seconds=m['proof_seconds']))
   raw=json.loads(serialize_game_record(s.to_record()));raw['actions'].append(m['choice']);s=GameSession.replay(c,deserialize_game_record(json.dumps(raw)))
 out=dict(status='COMPLETE_TRAIN_ONLY_PROOF_COST_LOCATION',bins={k:dict(v) for k,v in bins.items()},missed_proof_adoptions=details,seconds=time.perf_counter()-start,new_search_or_games=0,scope=plan['decision'])
 with (OUT/'result.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps(out))
if __name__=='__main__':run()
