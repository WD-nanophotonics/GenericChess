from pathlib import Path
import json,collections,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1595';O.mkdir(exist_ok=False);states=list(map(tuple,json.loads((R/'results/dev_aux/task1532/states.json').read_bytes())));ix={s:i for i,s in enumerate(states)};oracle=json.loads((R/'results/dev_aux/task1532/values.json').read_bytes());sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1531/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
graphs={p:json.loads((R/f'results/dev_aux/task1576/graph_R{p}.json').read_bytes()) for p in [720,1728]};values={p:json.loads((R/f'results/dev_aux/task1593/B64_R{p}.json').read_bytes()) for p in [720,1728]};rootpairs=[]
for (fam,i),(ff,j) in zip(graphs[720]['roots'],graphs[1728]['roots']):
 assert fam==ff;gain=values[1728]['value'][j]-values[720]['value'][i];rootpairs.append((gain,fam,i,j))
gain,fam,i,j=max(rootpairs);sid,c=graphs[720]['keys'][i];assert graphs[1728]['keys'][j]==[sid,c];traces=[]
for price,startindex in [(720,i),(1728,j)]:
 g=graphs[price];z=values[price];index={tuple(k):n for n,k in enumerate(g['keys'])};q=sid;seen=set();steps=[];boundary=False;rootv=z['value'][startindex];terminal=None
 for step in range(5000):
  s=states[q];ll=T.moves(s)
  if q in seen:assert rootv==0;terminal='INFINITE_CYCLE_DRAW';break
  seen.add(q)
  if not ll:terminal='CHECKMATE' if T.attacked(s,s[3*s[6]],1-s[6]) else 'STALEMATE';payoff=(-1 if s[6]==c else 1) if terminal=='CHECKMATE' else 0;assert payoff==rootv;break
  if sum(x!=12 for x in s[:6])<=4:
   boundary=True;cv=oracle['value'][q];target=cv
   candidates=[(u,ix[t]) for u,t in ll if -oracle['value'][ix[t]]==target]
   if cv:move,child=min(candidates,key=lambda x:(oracle['rank'][x[1]],x[0]));assert oracle['rank'][child]<oracle['rank'][q]
   else:move,child=min(candidates)
   basis='COMMON_PERFECT_4_RULE_CONTINUATION'
  else:
   n=index[q,c];adj=g['adj'][n];cv=z['value'][n];own=s[6]==c;targets=[h for h in adj if z['value'][h]==cv]
   assert targets
   if cv:
    targets=[h for h in targets if z['rank'][h]<z['rank'][n]];assert targets
   h=min(targets,key=lambda x:(z['rank'][x] if z['rank'][x] is not None else 0,g['keys'][x][0]));child=g['keys'][h][0];move=next(u for u,t in ll if ix[t]==child);basis=g['basis'][n]
   if own:assert len(adj)==1
  steps.append({'ply':step,'sid':q,'fen':T.fen(s),'move':move,'child':child,'basis':basis});assert dict(ll)[move]==states[child];q=child
 else:raise AssertionError('Witness bound not completed')
 traces.append({'price':price,'candidatecolor':c,'root_WDL':rootv,'terminal':terminal,'plies':len(steps),'common4_handoff_used':boundary,'steps':steps})
out={'status':'PASS_LITERAL_ACTUAL_FIVE_POLICY_AND_COMMON_FOUR_COMPLETE_WITNESSES','family':fam,'root_sid':sid,'root_fen':T.fen(states[sid]),'gain':gain,'traces':traces,'scope':'One exposed selectedmaxcontrast diagnostic, not validation or all-defenseproof alone. Parentall-opponent/ranks supply quantifiedcertificate. 5actor actualcold64, aftercapturecommonperfectrulepolicy. Drawcycle represents infinitecycle rule; zero nativego.'};(O/'result.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='traces'});print([{k:v for k,v in t.items() if k!='steps'} for t in traces])
