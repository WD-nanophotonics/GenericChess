"""All observed first price divergences, full-history replay; no new search."""
from pathlib import Path
import json,hashlib,time
from collections import defaultdict,Counter
from dataclasses import asdict
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_win_proof import _same_state

O=Path('results/dev_aux/task1910');P=Path('results/dev_aux/task1904')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p):return [json.loads(x) for x in Path(p).read_text().splitlines()]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def state_sha(s):return hashlib.sha256(repr(s).encode()).hexdigest()
def inv(s):
 return {str(owner):{typ:sum(p is not None and p.owner==owner and p.current_type_id==typ for p in s.position.board) for typ in ('R','N')} for owner in (0,1)}
def delta(inv,side):return {t:inv[str(side)][t]-inv[str(1-side)][t] for t in ('R','N')}
def main():
 start=time.perf_counter();plan=read(P/'run-plan.json');games=lines(P/'games.jsonl');moves=lines(P/'moves.jsonl');old=read('results/dev_aux/task1905/range_report.json');by=defaultdict(list)
 for x in moves:by[x['slot']].append(x)
 external=[m for m in moves if m['source']=='EXTERNAL_SEARCH'];events=lines(P/'run/transport.jsonl');intents=[x for x in events if x['event']=='INTENT'];choices=[x for x in events if x['event']=='CHOICE'];assert len(external)==len(intents)==len(choices)==1190
 receipts={(m['slot'],m['ply']):(i,ch) for m,i,ch in zip(external,intents,choices)}
 c=compile_ruleset_for_execution(deserialize_ruleset(Path(plan['rules']).read_text()));actor=RoyalActor(4);index={(g['family'],g['candidate_side'],g['ratio']):g for g in games};pairs=[]
 for detail in old['first_difference_details']:
  family,side,ply=detail['family'],detail['role'],detail['first_ply'];pair=dict(pair=len(pairs),family=family,role=side,first_ply=ply,old_wholepolicy_outcomes=detail['outcomes']);alternatives=[];common=None
  for ratio in (2.,4.):
   g=index[family,side,ratio];steps=by[g['slot']];record={**g['record'],'actions':g['record']['actions'][:ply]};s=GameSession.replay(c,deserialize_game_record(json.dumps(record)));before=s.state
   assert s.state.position.side_to_move==side and state_sha(before)==steps[ply]['before_state_sha'];assert steps[ply]['source']=='EXTERNAL_SEARCH'
   if common is None:common=GameSession.replay(c,s.to_record())
   else:assert _same_state(s.to_record(),common.to_record()) and _same_state(s.state,common.state)
   for i in range(ply):assert steps[i]['choice']==by[index[family,side,2.]['slot']][i]['choice']
   parent=json.loads(serialize_game_record(s.to_record()));full={**g['record'],'actions':g['record']['actions'][:ply+1]};action=deserialize_game_record(json.dumps(full)).actions[-1];action_text=uci(action)
   intent,choice=receipts[g['slot'],ply];assert intent['query']==choice['query'];assert intent['root_record']==repr(s.to_record());assert choice['move']==action_text;assert intent['R']==choice['R']==[g['R'],720,720,720]
   initial=GameSession(c,record.get('initial_setup_key'));expected='position fen '+actor.fen(actor_state(initial.state))+(' moves '+' '.join(uci(a) for a in s.to_record().actions) if s.to_record().actions else '')
   assert intent['position']==expected
   legal=dict(actor.moves(actor_state(before)));assert action_text in legal;s.submit(action);assert actor_state(s.state)==legal[action_text] and state_sha(s.state)==steps[ply]['after_state_sha']
   bi,ai=inv(before),inv(s.state);pre,post=delta(bi,side),delta(ai,side);change={t:post[t]-pre[t] for t in ('R','N')};captured=before.position.board[action.to_square.file+4*action.to_square.rank]
   raw=actor_state(s.state);check=actor.attacked(raw,actor.king(raw,1-side),side);info=[line for line in choice['raw'] if line.startswith('info depth ')];last=info[-1] if info else None
   alternatives.append(dict(ratio=ratio,old_slot=g['slot'],action=steps[ply]['choice'],uci=action_text,moving_type=before.position.board[action.from_square.file+4*action.from_square.rank].current_type_id,captured=None if captured is None else dict(owner=captured.owner,type=captured.current_type_id),before_inventory=bi,after_inventory=ai,own_net_change=change,immediate_material_change_at2=1440*change['R']+720*change['N'],immediate_material_change_at4=2880*change['R']+720*change['N'],gives_check=check,legal_children=len(legal),after_state_sha=state_sha(s.state),child_record=json.loads(serialize_game_record(s.to_record())),result={**asdict(s.result),'status':s.result.status.value},native_receipt=dict(intent=intent,choice=choice,last_info=last)))
  assert alternatives[0]['uci']!=alternatives[1]['uci'];pair.update(common_record=json.loads(serialize_game_record(common.to_record())),common_state_sha=state_sha(common.state),alternatives=alternatives);pairs.append(pair)
 assert len(pairs)==11 and len({(p['family'],p['role']) for p in pairs})==11
 out=dict(status='PASS',pairs=pairs,seconds=time.perf_counter()-start,source_sha={(p.relative_to(Path.cwd()).as_posix() if p.is_absolute() else p.as_posix()):sha(p) for p in [P/'run-plan.json',P/'games.jsonl',P/'moves.jsonl',P/'run/transport.jsonl',Path(__file__)]},summary=dict(pairs=len(pairs),both_quiet=sum(all(a['captured'] is None for a in p['alternatives']) for p in pairs),different_capture=sum(p['alternatives'][0]['captured']!=p['alternatives'][1]['captured'] for p in pairs),different_check=sum(p['alternatives'][0]['gives_check']!=p['alternatives'][1]['gives_check'] for p in pairs)),scope='ALL11firstactiondivergences selectedbyactioninequality only; original TRAIN exposed. Immediate deltas are not minimax/WDL value, Native score is heuristic. No price selection, search, fresh validation or oldcap continuation.')
 with (O/'result.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps(out['summary']))
if __name__=='__main__':main()
