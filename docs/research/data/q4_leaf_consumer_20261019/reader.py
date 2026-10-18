"""Data-only leaf-prediction audit. No learning updates or Native searches."""
from pathlib import Path
from collections import Counter
import sys,json,time,hashlib,math,os
sys.path.insert(0,str(Path.cwd()))
from tools.local_agent.common import write_json
from scripts.research_record import record_value
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.core.actions import SemanticBoardMove,SemanticDropMove
from generic_chess.core.coordinates import Square
from generic_chess.learning.features import material_features,non_anchor_type_ids
from generic_chess.learning.tdleaf import _normalized_value
D=Path(__file__).resolve().parent;S=Path.cwd()/'.local_agent/root-window-q4-20261019';start=time.monotonic();P=json.loads((D/'plan.json').read_bytes());mismatches=json.loads((S/'reader-result.json').read_bytes())['score_leaf_mismatches'];assert len(mismatches)==1046
queries={(q['slot'],q['relative_ply']):q for q in map(json.loads,(S/'queries.jsonl').read_bytes().splitlines())};models={m['checkpoint_id']:m['checkpoint']for m in json.loads((S/'models.json').read_bytes())['rows']};compiled={g['rule']:compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(g['rules']))for g in map(json.loads,(S/'generation.jsonl').read_bytes().splitlines())if 'rules'in g}
counts=Counter();rows=[];commits=0
def decode(a):
 kw=dict(a);kw['to_square']=Square(**kw['to_square'])
 if 'from_square'in kw:kw['from_square']=Square(**kw['from_square']);return SemanticBoardMove(**kw)
 return SemanticDropMove(**kw)
for idx,m in enumerate(mismatches):
 assert time.monotonic()-start<180 and idx<P['limits']['max_rows']
 for n in ('rollout','advisor','slack'):
  f=json.loads((Path(os.environ.get('GC_REPLAY_STOP_ROOT',Path.cwd()))/'.local_agent'/(n+'.json')).read_bytes());assert not(f.get('stopped')or f.get('user_paused'))
 q=queries[m['slot'],m['relative_ply']];cp=models[q['checkpoint_id']];c=compiled[m['rule']];s=GameSession(c)
 for a in m['leaf_record']['actions']:s.submit(decode(a));commits+=1
 assert record_value(s.to_record())==m['leaf_record']and not s.state.terminal_status.is_terminal
 board=sum((1 if pc.owner==0 else -1)*cp['board_weights'][pc.current_type_id]for pc in s.state.position.board if pc)
 hand=sum((s.state.position.hands[0].count(t)-s.state.position.hands[1].count(t))*v for t,v in cp['hand_weights'].items());raw=board+hand
 quant=sum((1 if pc.owner==0 else -1)*round(cp['board_weights'][pc.current_type_id]*256)for pc in s.state.position.board if pc)+sum((s.state.position.hands[0].count(t)-s.state.position.hands[1].count(t))*round(v*256)for t,v in cp['hand_weights'].items());assert quant==m['expected']
 features=material_features(s.state.position,non_anchor_type_ids(c),perspective=0);u=_normalized_value(features,cp['board_weights'],cp['hand_weights'],cp['value_scale']);assert abs(u-math.tanh(raw/cp['value_scale']))<1e-12
 hypothetical=math.tanh(m['actual']/(256*cp['value_scale']));counts['mode_'+str(q['root_window_pruning'])]+=1;counts['returned_q'+str(q['result_ordinary_qdepth'])]+=1;counts['candidate'if q['candidate_turn']else'foe']+=1
 rows.append(dict(mismatch_index=idx,slot=m['slot'],relative_ply=m['relative_ply'],rule=m['rule'],mode=q['root_window_pruning'],returned_qdepth=q['result_ordinary_qdepth'],raw_leaf=raw,integer_leaf=quant,integer_root_score=m['actual'],raw_leaf_quantization_gap=quant/256-raw,raw_root_leaf_gap=m['actual']/256-raw,actual_leaf_predictor=u,hypothetical_score_predictor=hypothetical,predictor_gap=hypothetical-u))
 if(idx+1)%256==0:print('LEAF_CONSUMER_REPLAY',idx+1,round(time.monotonic()-start,3),flush=True)
def quantile(v,p):v=sorted(v);return v[int((len(v)-1)*p)]
out=dict(status='PASS_RECORDED_LEAF_CONSUMER_CONTRACT',rows=rows,counts=dict(counts),Core_replay_commits=commits,summary=dict(abs_leaf_quantization_gap_max=max(abs(x['raw_leaf_quantization_gap'])for x in rows),abs_raw_root_leaf_gap_max=max(abs(x['raw_root_leaf_gap'])for x in rows),abs_predictor_gap_quantiles={str(p):quantile([abs(x['predictor_gap'])for x in rows],p)for p in(0,.5,.95,1)},hypothetical_gap_over_01=sum(abs(x['predictor_gap'])>.1 for x in rows)),seconds=time.monotonic()-start,source_files={p:hashlib.sha256(Path(p).read_bytes()).hexdigest()for p in ('generic_chess/learning/selfplay.py','generic_chess/learning/tdleaf.py','generic_chess/learning/arena.py')},current_consumer='ExistingPRIMARYproductcollection/arena explicitlyq0; leafvalue/tdleafUpdate re-evaluate rawleaf features. No current rootScore substitution proven. AUX93 source-only Corefloat/path contract remains independent.',scope='All1046preidentifiedordinaryPV-scoregaps, rawfloat versusNative256 separated. Hypothetical substitution changesnumbers, not observedlearning updates orfitness. No Nativequeries/newgames/learnerupdates/AUXexecution, q4traininggain orAPIdefect claim.')
write_json(D/'result.json',out);print('LEAF_CONSUMER_CLOSED',dict(counts),commits,out['summary'],time.monotonic()-start,flush=True)
