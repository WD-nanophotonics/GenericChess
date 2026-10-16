"""Existing heldout B failure attribution: paired outcomes and actual first fork."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.session import GameSession
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_royal_actor import RoyalActor
OUT=Path('results/dev_aux/task2033');ROOT=Path('results/dev_aux/task2020')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def lines(p):return[json.loads(x)for x in Path(p).read_text(encoding='utf-8').splitlines()]
def run():
 p=read(ROOT/'run-plan.json');games=lines(ROOT/'games.jsonl');cells={(g['family'],g['candidate_side'],g['B'],g['opponent_B']):g for g in games if g['phase']=='DEV'};matrix=Counter();negative=[];families=set();forkfamilies=set();changed=0
 steps=defaultdict(list)
 for m in lines(ROOT/'moves.jsonl'):steps[m['slot']].append(m)
 c=compile_ruleset_for_execution(deserialize_ruleset(Path(p['rules']).read_text(encoding='utf-8')));actor=RoyalActor(4);roots=read(p['roots'])['roots'];pairs=[]
 for f in range(8,16):
  for side in (0,1):
   for opp in (360,720,1440):
    base,low=cells[f,side,720,opp],cells[f,side,360,opp];matrix[base['outcome']+'->'+low['outcome']]+=1
    aa,bb=base['record']['actions'],low['record']['actions'];common=0
    while common<min(len(aa),len(bb)) and aa[common]==bb[common]:common+=1
    if common<min(len(aa),len(bb)):changed+=1;forkfamilies.add(f)
    if base['finite_event_score']!=low['finite_event_score']:families.add(f)
    pair=dict(family=f,candidate_side=side,opponent_B=opp,base_slot=base['slot'],low_slot=low['slot'],base_outcome=base['outcome'],low_outcome=low['outcome'],net_delta=low['finite_event_score']-base['finite_event_score'],common_prefix=common,first_fork=common<min(len(aa),len(bb)))
    pairs.append(pair)
    if pair['net_delta']<0:negative.append(pair)
 assert len(pairs)==48 and sum(x['net_delta']for x in pairs)==-2
 first=min(negative,key=lambda x:(x['family'],x['opponent_B'],x['candidate_side']));base=games[first['base_slot']];low=games[first['low_slot']];index=first['common_prefix'];assert first['first_fork']
 session=GameSession(c,roots[first['family']]['setup']);record=deserialize_game_record(json.dumps(base['record']))
 for action in record.actions[:index]:session.submit(action)
 board=actor_state(session.state);legal=dict(actor.moves(board));before=hashlib.sha256(repr(session.state).encode()).hexdigest();fork=[]
 for name,g in [('BASE_B1',base),('LEARNED_B.5',low)]:
  step=steps[g['slot']][index];action=deserialize_game_record(json.dumps(g['record'])).actions[index];move=uci(action);assert move in legal and step['before_state_sha']==before
  child=GameSession.replay(c,session.to_record());child.submit(action);assert actor_state(child.state)==legal[move]
  taken=board[(int(move[3])-1)*4+ord(move[2])-97]
  profile=[1260,720,g['B'] if step['side']==g['candidate_side'] else g['opponent_B'],720]
  fork.append(dict(arm=name,slot=g['slot'],ply=index,actor_side=step['side'],actor_is_candidate=step['side']==g['candidate_side'],actual_profile_RNBP=profile,action=move,captured=taken,source=step['source'],proof_nodes=step['proof_nodes'],proof_reason=step['proof_reason'],normal_nodes=step['search_nodes'],normal_seconds=step['normal_seconds'],decision_seconds=step['seconds'],before_sha=before,after_sha=hashlib.sha256(repr(child.state).encode()).hexdigest(),final_outcome=g['outcome']))
 d=dict(status='PASS_PAIRED_EXISTING_B_FAILURE_COUNTEREXAMPLE',pairs=48,family_clusters=8,outcome_matrix=dict(matrix),outcome_changed_families=sorted(families),first_fork_pairs=changed,first_fork_families=sorted(forkfamilies),negative_pairs=len(negative),selected_first_negative=first,first_fork=fork,actual_prefix_record=json.loads(serialize_game_record(session.to_record())),all_pair_diagnostics=pairs,scope='ExistingexposedDEV diagnostic/no newNative/proof/search/labelselection. Exactsharedfullstate thenliterallegal children andactual final W-L. Firstforkclassifies candidatepricepolicyvsfixedopponent; differingactions are not themselves a gain or isolatedcausalproof. Outcome matrix includesALL48pairedcells/8families, no populationclaim fromselectednegativecase.')
 with(OUT/'result.json').open('x',encoding='utf-8')as f:json.dump(d,f,indent=2)
 print(json.dumps({k:v for k,v in d.items()if k not in ('all_pair_diagnostics','actual_prefix_record')}))
if __name__=='__main__':run()
