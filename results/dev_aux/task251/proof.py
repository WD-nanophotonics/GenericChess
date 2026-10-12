import json,time
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task251';O.mkdir(exist_ok=True);T=json.loads((R/'results/dev_aux/task250/tree.json').read_bytes());X=json.loads((R/'results/dev_aux/task250/result.json').read_bytes());start=time.monotonic();bound=0;negative=0;nonterminal=0;deltas=[];roots=[]
for r in T['roots']:
 goals=[Fraction(z['goal']) for z in r['rows']];unique=sorted(set(goals));ds=[b-a for a,b in zip(unique,unique[1:])];deltas+=ds;roots.append(dict(root=r['root'],unique_goal_values=[str(x) for x in unique],minimum_positive_gap=None if not ds else str(min(ds))))
 for row in r['rows']:
  for branch in row['branches']:
   ll=branch.get('unique_leaves', [['terminal',branch['terminal']]] if 'terminal' in branch else [])
   for vector in ll:
    if vector[0]=='terminal':negative+=vector[1]<0;continue
    nonterminal+=1;p,*f=vector;hi=208*p+sum(a*(3328 if a>=0 else 52) for a in f);lo=208*p+sum(a*(52 if a>=0 else 3328) for a in f);bound=max(bound,abs(lo),abs(hi))
assert negative==0 and deltas;gap=min(deltas);dominant=Fraction(100000000)*gap>2*(bound+3);assert dominant
proof=dict(complete=True,box=dict(P=208,K=0,NBRQ=[52,3328]),nonterminal_leaf_bound=bound,negative_terminal_leaves=negative,unique_nonterminal_leaf_vectors_visited=nonterminal,minimum_goal_gap=str(gap),mate_gap_product=str(Fraction(100000000)*gap),maximum_residual_difference_bound=2*(bound+3),mean3_goal_order_invariant_over_entire_continuous_box=True,proof='AtfinalWhite choices, everyrealmate terminal1e8-ply dominates everynonterminalmaterial abs<=B. NoBlackwin terminal occurs in completefamilytree. Thus uniformBlack expectedD3material E(a,w)=1e8*U(a)+r(a,w), |r|<=B+3 for everyallowed continuouspositivepricevector. Foranydifferentgoal probabilitiesdelta>=declaredexactminimumgap, E-order follows U-order because1e8*delta>2*(B+3). ThereforemeanD3 choosesa goal-optimalrootaction forEVERYw inthedeclaredbox; notjust625grid. Ties maychangeaction butnotfinitegoalvalue. Taskcannotidentifyhumanratios withinthatbox evenwithperfectglobaloptimization.',roots=roots,seconds=time.monotonic()-start,scope='Specific24exposed6pieceCgeometryfamily, exact3plymean-opponentgoal andfixedterminalencoding. Notunboundedpositiveprices/fullChess/unknownfutureWDL, notproof againstmateriallearning underotherdistributions/objectives. Boundsderiveactualentireleafsets; noexpertpricevector queried.');(O/'proof.json').write_text(json.dumps(proof,indent=2),encoding='utf-8');print(json.dumps({k:proof[k] for k in ('complete','box','nonterminal_leaf_bound','negative_terminal_leaves','minimum_goal_gap','mate_gap_product','maximum_residual_difference_bound','seconds')},indent=2))
