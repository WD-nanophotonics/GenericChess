import json,time,hashlib
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task282';D=json.loads((R/'results/dev_aux/task281/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task281/result.json').read_bytes());T=json.loads((R/'results/dev_aux/task258/tree.json').read_bytes());old=json.loads((R/'results/dev_aux/task259/result.json').read_bytes());start=time.monotonic();assert X['complete'];checks=[]
for z in X['rows']:
 f=next(f for f in D['roots'] if f['id']==z['root']);tree=next(t for t in T['roots'] if t['root']==z['root']);w=z['weights'];actor=chess.Board(f['fen']).turn
 def value(ld):return ld['terminal'] if 'terminal' in ld else sum(w[k]*v for k,v in zip('PNBRQ',ld['vector']))
 scores={}
 for a in tree['actions']:
  scores[a['move']]=min(value(br['terminal']) if 'terminal' in br else max(value(ch['leaf']) for ch in br['children']) for br in a['branches'])
 best=max(scores.values());argmax=[a for a,v in scores.items() if v==best];raw=z['result'];assert raw['score']==best and raw['completed_depth']==3 and z['action'] in argmax and raw['root_window_pruning']==True and not raw['used_fallback'];b=chess.Board(f['initial_fen'])
 for text in f['history']:b.push_uci(text)
 texts=[]
 for action in raw['principal_variation']:
  fr=action['from_square'];to=action['to_square'];text=chess.square_name(chess.square(fr['file'],fr['rank']))+chess.square_name(chess.square(to['file'],to['rank']));p=action.get('promotion_target_id');text+=p.lower() if p else '';m=chess.Move.from_uci(text);assert m in b.legal_moves;b.push(m);texts.append(text)
 oo=b.outcome(claim_draw=False);literal=0 if oo is not None and oo.winner is None else ((100000000-len(texts) if oo.winner==actor else -100000000+len(texts)) if oo is not None else sum(w[k]*(len(b.pieces(i+1,actor))-len(b.pieces(i+1,not actor))) for i,k in enumerate('PNBRQ')));assert len(texts)==3 or oo is not None;assert literal==raw['score'];base=next(v for v in old['rows'] if v['root']==z['root'] and v['profile']==z['profile'] and v['depth']==3);assert base['result']['score']==raw['score'];checks.append(dict(root=z['root'],profile=z['profile'],score=best,argmax=argmax,new_action=z['action'],old_action=base['action'],same_action=z['action']==base['action'],literal_PV_leaf=literal,new_caller_seconds=z['seconds'],old_caller_seconds=base['wall_seconds'],new_nodes=raw['nodes'],old_nodes=base['result']['nodes']))
out=dict(complete=True,actual_newbinary_score_argmax_PVleaf_checks=len(checks),matched_oldscore_checks=len(checks),same_actions=sum(z['same_action'] for z in checks),new_caller_seconds_sum=sum(z['new_caller_seconds'] for z in checks),old_caller_seconds_sum=sum(z['old_caller_seconds'] for z in checks),new_node_sum=sum(z['new_nodes'] for z in checks),old_node_sum=sum(z['old_nodes'] for z in checks),binary_sha256=D['binary_sha256'],source_commit=D['source_commit'],seconds=time.monotonic()-start,checks=checks,scope='Actualownfixednewbinary16D3queries+independentcompletefiniteoracle/literalPVleaf; noMAINexecutionclaim. NewRootTrue/TT1/f1easource/Clang vsoldRootFalse/TT0/oldsource/binary areUNALIGNEDalgorithm/TT/source/compiler planes; timing/nodechangesnotisolatedcanonicalrepaircausality or equalprimitiveproven speedup. Owninstalled2f97binary unchanged; source-backedprivateexperimentonly.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='checks'},indent=2))
