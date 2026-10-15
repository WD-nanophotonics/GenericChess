"""ALL first price divergences from paid studies, outcome-independent diagnostic."""
from pathlib import Path
from collections import defaultdict,Counter
import json,hashlib,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_royal_actor import RoyalActor
from results.dev_aux.task1928.audit import lines,read,state_sha
O=Path('results/dev_aux/task1946')
def run():
 beg=time.perf_counter();pairs=[];cases=[];counts=Counter();actor=RoyalActor(4);sources={}
 for task in (1939,1943):
  folder=Path(f'results/dev_aux/task{task}');p=read(folder/'run-plan.json');assert read(folder/'completion.json')['status']=='COMPLETE';games=lines(folder/'games.jsonl');moves=lines(folder/'moves.jsonl');events=lines(folder/'run/transport.jsonl');by=defaultdict(list)
  for m in moves:by[m['slot']].append(m)
  ext=[m for m in moves if m['source']=='EXTERNAL_SEARCH'];ints=[e for e in events if e['event']=='INTENT'];chs=[e for e in events if e['event']=='CHOICE'];assert len(ext)==len(ints)==len(chs)
  receipts={(m['slot'],m['ply']):(i,ch) for m,i,ch in zip(ext,ints,chs)};c=compile_ruleset_for_execution(deserialize_ruleset(Path(p['rules']).read_text()));idx={(g['family'],g['candidate_side'],g.get('opponent_nodes',p['opponent_nodes']),g['ratio']):g for g in games};groups=sorted({key[:3] for key in idx})
  for family,role,opp in groups:
   a,b=idx[family,role,opp,1.],idx[family,role,opp,2.];aa,bb=by[a['slot']],by[b['slot']];counts['paired_policies']+=1
   prefix=0
   while prefix<min(len(aa),len(bb)) and aa[prefix]['choice']==bb[prefix]['choice']:prefix+=1
   case=dict(study=task,family=family,role=role,opponent_nodes=opp,phase=a['phase'],common_prefix=prefix,outcomes=[a['outcome'],b['outcome']])
   if prefix==min(len(aa),len(bb)):
    case['kind']='SAME_FULL_PATH' if len(aa)==len(bb) else 'LENGTH_ONLY';cases.append(case);counts[case['kind']]+=1;continue
   common={**a['record'],'actions':a['record']['actions'][:prefix]};assert common=={**b['record'],'actions':b['record']['actions'][:prefix]};root=GameSession.replay(c,deserialize_game_record(json.dumps(common)));assert state_sha(root.state)==aa[prefix]['before_state_sha']==bb[prefix]['before_state_sha'];side=root.state.position.side_to_move;case['first_side']=side;case['kind']='CANDIDATE_PRICE_DIVERGENCE' if side==role else 'FIXED_OPPONENT_DIVERGENCE';counts[case['kind']]+=1;case['sources']=[aa[prefix]['source'],bb[prefix]['source']];alternatives=[]
   for ratio,g,steps in ((1.,a,aa),(2.,b,bb)):
    step=steps[prefix];child={**g['record'],'actions':g['record']['actions'][:prefix+1]};s=GameSession.replay(c,deserialize_game_record(json.dumps(child)));action=deserialize_game_record(json.dumps(child)).actions[-1];assert actor_state(s.state)==dict(actor.moves(actor_state(root.state)))[uci(action)] and state_sha(s.state)==step['after_state_sha']
    native=None
    if step['source']=='EXTERNAL_SEARCH':
     intent,choice=receipts[g['slot'],prefix];assert intent['root_record']==repr(root.to_record()) and choice['move']==uci(action) and choice['requested_nodes']==step['budget'];native=dict(intent=intent,choice=choice)
    alternatives.append(dict(ratio=ratio,uci=uci(action),action=step['choice'],source=step['source'],child_record=child,native_receipt=native))
   case['alternatives']=alternatives;cases.append(case)
   if side==role:
    assert all(x['source']=='EXTERNAL_SEARCH' for x in alternatives)
    pairs.append(dict(pair=len(pairs),family=family,role=role,law=f'task{task}_{a["phase"]}_opp{opp}',rules=p['rules'],common_record=common,alternatives=alternatives,original_candidate_side=role))
  for path in [folder/'run-plan.json',folder/'completion.json',folder/'games.jsonl',folder/'moves.jsonl',folder/'run/transport.jsonl']:sources[path.as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
 assert counts['paired_policies']==192
 out=dict(status='PASS_ALL192_PAIRS',counts=dict(counts),cases=cases,pairs=pairs,source_sha=sources,seconds=time.perf_counter()-beg,scope='All192policy pairs selected bystudy/family/role/opponent only, no outcome filter. Only firstcommonstate candidate-priced NORMAL divergences form the exactvalue panel. Fixedopponent divergences are retained separately, cannot attribute to changedopponentprices. No new games/price selection. Originalroles/caps/Native histories verified.')
 (O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(counts=counts,pairs=len(pairs),seconds=out['seconds'])))
if __name__=='__main__':run()
