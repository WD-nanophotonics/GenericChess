"""Declared eight-repeat continuation at every original finite frontier."""
import sys,json,random,hashlib,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.transition import initial_state,apply_action
from generic_chess.core.movegen import legal_actions
from generic_chess.core.actions import SemanticBoardMove,SemanticDropMove
from scripts.research_record import write_record,record_value
p=Path(__file__).parent;prior=ROOT/'.local_agent/custody-kernel-20261008'
raw=(prior/'pretransfer-coupling.json').read_bytes();src=json.loads(raw);defs=(prior/'kernel-completed.json').read_bytes();cases=json.loads(defs)['cases']
out=p/'remaining-custody.json';assert not out.exists();start=time.perf_counter()
cs=[compile_ruleset_for_execution(ruleset_from_dict(x['definition'])) for x in cases]
r=dict(complete=False,producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),source_sha256=hashlib.sha256(raw).hexdigest(),definition_sha256=hashlib.sha256(defs).hexdigest(),declaration='All13 frozen frontiers,8 repeats each,original total32plies minus consumed ply. Uniform canonical legal actions both players; exchangeable same-base hand tag, ordinary tagged captures+1 owner0/-1 owner1, terminal stop/no WDL bonus. Seeds2026100811+100*frontier_index+repeat shared across G/P; extra tag draws may change coupling but not marginal action law.51 nontransfer zero contrasts retain denominator64. Descriptive exposed finite development pilot, no positive-price inference. Maximum4320 continuation transitions,16-context checkpoint bound,stop each trajectory.',cells=[],transitions=0)
write_record(out,r)
for fi,f in enumerate(sorted(src['frontiers'],key=lambda x:x['seed'])):
 for case,c,actions,saved in zip(cases,cs,f['paired_actions'],f['paired_states']):
  state=initial_state(c)
  for v in actions:state=apply_action(state,next(a for a in legal_actions(state,c) if record_value(a)==v),c)
  assert record_value(state)==saved;anchors={t.type_id for t in c.piece_types if t.is_anchor};base=case['base'];cell=dict(frontier_seed=f['seed'],base=base,remaining=32-f['ply'],trials=[])
  for trial in range(8):
   assert not json.loads((ROOT/'.local_agent/rollout.json').read_bytes()).get('user_paused')
   rng=random.Random(2026100811+100*fi+trial);s=state;square=None;hand=1;reward=0;aa_saved=[];events=[]
   for ply in range(32-f['ply']):
    if s.terminal_status.is_terminal:break
    aa=sorted(legal_actions(s,c),key=lambda a:json.dumps(record_value(a),sort_keys=True));assert aa
    a=aa[rng.randrange(len(aa))];owner=s.position.side_to_move
    if isinstance(a,SemanticBoardMove):
     origin=(a.from_square.file,a.from_square.rank);target=(a.to_square.file,a.to_square.rank);victim=s.position.board[a.to_square.file+9*a.to_square.rank]
     if origin==square:
      if victim is not None and victim.owner!=owner and victim.current_type_id not in anchors:reward+=1 if owner==0 else -1;events.append(dict(ply=ply,owner=owner))
      square=target
     elif target==square:
      assert victim is not None and victim.base_type_id==base;square=None;hand=owner
    elif isinstance(a,SemanticDropMove) and hand==owner and a.base_type_id==base:
     if rng.randrange(s.position.hands[owner].count(base))==0:square=(a.to_square.file,a.to_square.rank);hand=None
    s=apply_action(s,a,c);r['transitions']+=1;aa_saved.append(record_value(a))
    if square is not None:tag=s.position.board[square[0]+9*square[1]];assert tag is not None and tag.base_type_id==base
    else:assert hand in (0,1) and s.position.hands[hand].count(base)>=1
   cell['trials'].append(dict(repeat=trial,reward=reward,actions=aa_saved,events=events,terminal=record_value(s.terminal_status)))
  r['cells'].append(cell)
 write_record(out,r)
diffs=[sum(r['cells'][2*i]['trials'][j]['reward']-r['cells'][2*i+1]['trials'][j]['reward'] for i in range(13))/64 for j in range(8)]
r.update(complete=True,original_population_repeat_differences=diffs,mean_difference=sum(diffs)/8,seconds=time.perf_counter()-start);write_record(out,r);print(json.dumps({k:r[k] for k in ('transitions','mean_difference','original_population_repeat_differences','seconds')}))
