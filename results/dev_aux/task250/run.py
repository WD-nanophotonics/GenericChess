import json,itertools,time,math,datetime,importlib.util
from fractions import Fraction
from pathlib import Path
import chess,numpy as np
R=Path.cwd();O=R/'results/dev_aux/task250';D=json.loads((O/'declaration.json').read_bytes());assert not (O/'result.json').exists();old=json.loads((R/'results/dev_aux/task241/result.json').read_bytes());N=json.loads((R/'results/dev_aux/task247/result.json').read_bytes());profiles=list(json.loads((R/'results/dev_aux/task247/declaration.json').read_bytes())['profiles']);actualW=[N['rows'][next(i for i,z in enumerate(N['rows']) if z['profile']==p)]['weights'] for p in profiles];ratios=list(itertools.product(D['grid'],repeat=4));W=np.array([[208]+[round(208*x) for x in rr] for rr in ratios]+[[w[k] for k in 'PNBRQ'] for w in actualW],dtype=np.int64);start=time.monotonic();trees=[];rootPolicies=[];leafvisits=0;nativechecks=0
s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P)
for fixture in D['roots']:
 b=chess.Board(fixture['fen']);actor=b.turn;source=next(r for r in old['results'] if r['name']==fixture['name']);moveRows=[];mins=[];sums=[];dens=[];goals=[]
 def leaf(ply):
  global leafvisits
  leafvisits+=1
  if leafvisits%2048==0:P.A.guard(start+180,P.stop)
  out=b.outcome(claim_draw=False)
  if out:return ('terminal',0 if out.winner is None else (100000000-ply if out.winner==actor else -100000000+ply)), bool(out.winner==actor)
  return tuple(len(b.pieces(t,actor))-len(b.pieces(t,not actor)) for t in range(1,6)),False
 for move in sorted(b.legal_moves,key=lambda z:z.uci()):
  b.push(move);term=b.outcome(claim_draw=False);branches=[];mvalues=[];successes=[]
  if term:
   leafdata,win=leaf(1);vals=np.full(629,leafdata[1],dtype=np.int64);mvalues.append(vals);successes.append(int(win));branches.append(dict(terminal=leafdata[1],success=int(win)))
  else:
   for reply in sorted(b.legal_moves,key=lambda z:z.uci()):
    b.push(reply);term=b.outcome(claim_draw=False);uniq=set();win=False
    if term:ld,win=leaf(2);uniq.add(ld)
    else:
     for third in sorted(b.legal_moves,key=lambda z:z.uci()):b.push(third);ld,w=leaf(3);win|=w;uniq.add(ld);b.pop()
    branch_values=[]
    for vector in uniq:branch_values.append(np.full(629,vector[1],dtype=np.int64) if vector[0]=='terminal' else W@np.array(vector,dtype=np.int64))
    vals=np.max(branch_values,axis=0);mvalues.append(vals);successes.append(int(win));branches.append(dict(reply=reply.uci(),unique_leaves=[list(v) for v in sorted(uniq,key=str)],success=int(win)));b.pop()
  b.pop();minvalues=np.min(mvalues,axis=0);sumvalues=np.sum(mvalues,axis=0);goal=Fraction(sum(successes),len(successes));sr=next(z for z in source['rows'] if z['move']==move.uci());expected=Fraction(sum(z['success_within3'] for z in sr['replies']),len(sr['replies'])) if sr['replies'] else Fraction(int(sr['goal_success_probability']));assert goal==expected;mins.append(minvalues);sums.append(sumvalues);dens.append(len(mvalues));goals.append(goal);moveRows.append(dict(move=move.uci(),branches=branches,goal=str(goal)))
 mat=np.array(mins);nums=np.array(sums);den=np.array(dens,dtype=np.int64);minimum=mat.max(axis=0);chosenMin=np.argmax(mat,axis=0);chosenMean=np.zeros(629,dtype=np.int64)
 for i in range(1,len(moveRows)):
  col=np.arange(629);better=nums[i]*den[chosenMean]>nums[chosenMean,col]*den[i];chosenMean[better]=i
 meanTies=nums*den[chosenMean]==nums[chosenMean,np.arange(629)]*den[:,None];minTies=mat==minimum
 for j,p in enumerate(profiles):
  rr=next(z for z in N['rows'] if z['root']==fixture['name'] and z['profile']==p);assert rr['decision']['completed_depth']==3 and rr['decision']['score']==int(minimum[625+j]);assert rr['action'] in [moveRows[i]['move'] for i in np.where(minTies[:,625+j])[0]];nativechecks+=1
 methods={}
 for method,chosen,ties in [('min',chosenMin,minTies),('mean',chosenMean,meanTies)]:
  methods[method]=dict(chosen_indices=chosen.tolist(),goal_values=[str(goals[i]) for i in chosen],tie_goal_min=[str(min(goals[i] for i in np.where(ties[:,j])[0])) for j in range(629)],tie_goal_max=[str(max(goals[i] for i in np.where(ties[:,j])[0])) for j in range(629)])
 trees.append(dict(root=fixture['name'],phase=fixture['phase'],rows=moveRows));rootPolicies.append(dict(root=fixture['name'],phase=fixture['phase'],moves=[r['move'] for r in moveRows],goal_oracle=str(max(goals)),methods=methods))
train=[r for r in rootPolicies if r['phase']=='train'];held=[r for r in rootPolicies if r['phase']=='heldout'];models=[];endpoints={}
for method in ('min','mean'):
 ms=[sum(Fraction(r['methods'][method]['goal_values'][j]) for r in train)/len(train) for j in range(625)];best=max(ms);ties=[j for j,v in enumerate(ms) if v==best];selected=min(ties,key=lambda j:(sum(math.log(v)**2 for v in ratios[j]),ratios[j]));endpoints[method]=dict(index=selected,ratios=dict(zip('NBRQ',ratios[selected])),train=str(ms[selected]),train_optima=len(ties),frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat());(O/'endpoints.json').write_text(json.dumps(endpoints,indent=2),encoding='utf-8');hm=[sum(Fraction(r['methods'][method]['goal_values'][j]) for r in held)/len(held) for j in range(625)];models.append(dict(method=method,selected_heldout=str(hm[selected]),unit=dict(train=str(ms[312]),heldout=str(hm[312])),configs=[dict(index=j,ratios=dict(zip('NBRQ',ratios[j])),train=str(ms[j]),heldout=str(hm[j])) for j in range(625)]))
bounds=[]
for phase in ('train','heldout'):
 rr=[r for r in rootPolicies if r['phase']==phase]
 for method in ('min','mean'):
  bounds.append(dict(phase=phase,method=method,unit_canonical=str(sum(Fraction(r['methods'][method]['goal_values'][312]) for r in rr)/len(rr)),unit_favorable=str(sum(Fraction(r['methods'][method]['tie_goal_max'][312]) for r in rr)/len(rr)),any625_favorable=str(sum(max(Fraction(v) for v in r['methods'][method]['tie_goal_max'][:625]) for r in rr)/len(rr)),true_goal_oracle=str(sum(Fraction(r['goal_oracle']) for r in rr)/len(rr))))
out=dict(complete=True,seconds=time.monotonic()-start,third_leaf_visits=leafvisits,native_score_argmax_checks=nativechecks,endpoints=endpoints,models=models,bounds=bounds,root_policies=rootPolicies,scope=D['scope']);(O/'tree.json').write_text(json.dumps(dict(complete=True,roots=trees),indent=2),encoding='utf-8');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:out[k] for k in ('complete','seconds','third_leaf_visits','native_score_argmax_checks','endpoints','bounds')},indent=2))
