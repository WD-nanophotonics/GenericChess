import json,math,hashlib,time
from pathlib import Path
import chess,numpy as np
R=Path.cwd();O=R/'results/dev_aux/task212';D=json.loads((O/'declaration.json').read_bytes())
def reported(meta):
 lines=[t for t in meta['uci_info'] if ' score ' in t and ' pv ' in t and 'lowerbound' not in t and 'upperbound' not in t]
 if not lines:return None
 f=lines[-1].split();i=f.index('score');kind=f[i+1];num=int(f[i+2]);b=chess.Board(meta['root_fen'])
 for z in meta['full_history']:b.push_uci(z)
 sign=1 if b.turn else -1;return dict(kind=kind,raw_actor=num,white_value=sign*(math.tanh(num/400) if kind=='cp' else (1 if num>0 else -1)),line=lines[-1])
def board(meta):
 b=chess.Board(meta['root_fen'])
 for z in meta['full_history']:b.push_uci(z)
 return b

def value(theta,phi):return math.tanh((phi[0]+np.dot(phi[1:],np.exp(theta)))/4)
def gradient(theta,phi):
 v=value(theta,phi);return (1-v*v)/4*phi[1:]*np.exp(theta)
def execute():
 assert not (O/'analysis.json').exists();started=time.monotonic();P=R/'results/dev_aux/task187/controller.json';assert hashlib.sha256(P.read_bytes()).hexdigest()==D['source_controller_sha256'];C=json.loads(P.read_bytes());out=[];excluded=[]
 for ix,c in enumerate(D['cases']):
  game=next(v for v in C['calls'] if v['context']['name']==c['game']);records=game['result']['search_records'];idx=c['search_index'];cur=records[idx];s=board(cur);reported_now=reported(cur)
  if idx+1>=len(records):excluded.append(dict(case=ix,reason='noactualnextactorrecord'));continue
  successor=records[idx+1];ss=board(successor);assert s.turn==ss.turn and successor['full_history'][:len(cur['full_history'])]==cur['full_history'] and len(successor['full_history'])-len(cur['full_history'])==2;rr=reported(successor)
  if reported_now is None or rr is None:excluded.append(dict(case=ix,reason='missingunboundedreportedvalue,noresample'));continue
  terminal=ss.outcome(claim_draw=False);target=(0 if terminal.winner is None else (1 if terminal.winner else -1)) if terminal else rr['white_value'];phi=np.array([len(s.pieces(i,True))-len(s.pieces(i,False)) for i in range(1,6)],dtype=float);base=np.array([c['weights'][k]/208 for k in 'NBRQ']);profiles={'unit':np.ones(4),'same_teacher':base,'reversed_teacher_NBRQ':base[::-1]}
  for name,ratios in profiles.items():
   theta=np.log(ratios);student=value(theta,phi);grad=gradient(theta,phi);numerical=np.array([(value(theta+np.eye(4)[j]*1e-6,phi)-value(theta-np.eye(4)[j]*1e-6,phi))/(2e-6) for j in range(4)]);assert np.max(abs(grad-numerical))<1e-7;step=.001/max(1,float(grad@grad));correct=target-student;mixed=target-reported_now['white_value'];new=np.clip(theta+step*correct*grad,math.log(.25),math.log(16));wrong=np.clip(theta+step*mixed*grad,math.log(.25),math.log(16));loss=(target-student)**2;lossnew=(target-value(new,phi))**2;losswrong=(target-value(wrong,phi))**2;active=float(grad@grad)>1e-20;assert lossnew<=loss+1e-12
   out.append(dict(case=ix,student_profile=name,teacher_weights=c['weights'],root_fen=cur['root_fen'],full_history=cur['full_history'],successor_full_history=successor['full_history'],root_white_features=phi.tolist(),reported_current=reported_now,reported_successor=rr,target=target,student_value=student,correct_residual=correct,mixed_residual=mixed,gradient=grad.tolist(),gradient_max_error=float(np.max(abs(grad-numerical))),nonzero_updatable_features=active,strict_sign_conflict=correct*mixed<0 and active,loss_before=loss,loss_correct=lossnew,loss_mixed=losswrong,old_update_increases_loss=losswrong>loss+1e-12,step=step))
 result=dict(complete=True,cases=len(D['cases']),excluded=excluded,rows=out,gradient_checks=len(out),correctloss_nonincreasing=sum(r['loss_correct']<=r['loss_before']+1e-12 for r in out),sign_conflicts=sum(r['strict_sign_conflict'] for r in out),mixedloss_increases=sum(r['old_update_increases_loss'] for r in out),seconds=time.monotonic()-started,scope=D['scope']);(O/'analysis.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
if __name__=='__main__':execute()
