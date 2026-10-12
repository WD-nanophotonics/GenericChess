import json,hashlib,math,time
from pathlib import Path
import chess,numpy as np
R=Path.cwd();O=R/'results/dev_aux/task213';D=json.loads((O/'declaration.json').read_bytes())
def read_value(meta):
 lines=[s for s in meta['uci_info'] if ' score ' in s and ' pv ' in s and 'lowerbound' not in s and 'upperbound' not in s]
 if not lines:return None
 f=lines[-1].split();i=f.index('score');kind=f[i+1];value=int(f[i+2]);return dict(kind=kind,raw=value,bounded=math.tanh(value/400) if kind=='cp' else (1 if value>0 else -1),line=lines[-1])
def execute():
 assert not (O/'dataset.json').exists();P=R/'results/dev_aux/task187/controller.json';assert hashlib.sha256(P.read_bytes()).hexdigest()==D['source_controller_sha256'];C=json.loads(P.read_bytes());started=time.monotonic();rows=[];excluded=[]
 for c in C['calls']:
  x=c['context']
  if not(x['start_seed'] in D['seeds'] and x['opponent']=='random-original' and x['phase']=='train' and x['sweep']==0 and x['coordinate']==0 and x['arm']==0):continue
  r=c['result'];col=x['agent_color'];b=chess.Board(r['root_fen'])
  for m in r['opening_history']:b.push_uci(m)
  states=[];positions=[];ix=0
  for ply,txt in enumerate(r['actions']):
   if b.turn==col:
    meta=r['search_records'][ix];assert meta['full_history']==[m.uci() for m in b.move_stack] and meta['root_fen']==b.root().fen();states.append((b.copy(stack=True),meta,ply));positions.append(ply);ix+=1
   assert chess.Move.from_uci(txt) in b.legal_moves;b.push_uci(txt)
  assert ix==len(r['search_records']) and b.fen()==r['final_fen']
  for i,(s,meta,ply) in enumerate(states):
   successor=s.copy(stack=True)
   for m in r['actions'][ply:ply+2]:successor.push_uci(m)
   out=successor.outcome(claim_draw=False);nextmeta=states[i+1][1] if i+1<len(states) else None
   if out:target=0 if out.winner is None else (1 if out.winner==col else -1);kind='actual_terminal';value=None
   elif nextmeta:
    assert nextmeta['full_history']==[m.uci() for m in successor.move_stack];value=read_value(nextmeta)
    if value is None:excluded.append(dict(game=x['name'],index=i,reason='successor no unboundedreportedPVvalue'));continue
    target=value['bounded'];kind='frozen_search_bootstrap'
   else:excluded.append(dict(game=x['name'],index=i,reason='unknowncutoff no successorsearch,notdraw/noinventedtarget'));continue
   phi=[len(s.pieces(t,col))-len(s.pieces(t,not col)) for t in range(1,6)];ratios=np.array([c['weights'][k]/208 for k in 'NBRQ']);student=math.tanh((phi[0]+np.dot(phi[1:],ratios))/4);grad=(1-student*student)/4*np.array(phi[1:])*ratios
   rows.append(dict(game=x['name'],seed=x['start_seed'],root_index=x['root_index'],agent_color=col,index=i,root_fen=meta['root_fen'],full_history=meta['full_history'],actual_root_fen=s.fen(),actual_successor_fen=successor.fen(),features_actor=phi,target=target,target_kind=kind,successor_report=value,teacher_weights=c['weights'],gradient_at_initial=grad.tolist(),current_student_at_initial=student))
 summaries=[]
 for seed in D['seeds']:
  rr=[r for r in rows if r['seed']==seed];X=np.array([[1]+r['features_actor'] for r in rr],dtype=float);G=np.array([r['gradient_at_initial'] for r in rr]);summaries.append(dict(seed=seed,transitions=len(rr),raw_feature_rank=int(np.linalg.matrix_rank(X)),NBRQ_feature_rank=int(np.linalg.matrix_rank(X[:,2:])),countvariation=dict(zip('PNBRQ',np.ptp(X[:,1:],axis=0).tolist())),gradient_singular_values=np.linalg.svd(G,compute_uv=False).tolist(),nonzero_gradient_rows=int(np.sum(np.linalg.norm(G,axis=1)>1e-12)),true_terminal_targets=sum(r['target_kind']=='actual_terminal' for r in rr),forecast_mate_targets=sum(bool(r['successor_report'] and r['successor_report']['kind']=='mate') for r in rr)))
 out=dict(complete=True,rows=rows,excluded=excluded,summaries=summaries,seconds=time.monotonic()-started,scope='Allfirst-blockstates, noPVleaffeatures orsearchgradient/pricefit/newgames. Actualterminationdistinctfromforecastmate andunknowncutoffs; fixed4pawn-scale link approximation.');(O/'dataset.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(complete=True,transitions=len(rows),excluded=len(excluded),summaries=summaries,seconds=out['seconds']),indent=2))
if __name__=='__main__':execute()
