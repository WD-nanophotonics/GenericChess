import json,collections,hashlib
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task882';O.mkdir(exist_ok=False);assert json.loads((R/'results/dev_aux/task877/result.json').read_bytes())['status']=='PASS_ALL40_NB_ROOTS_AND104_PILOT_GAMES';P=R/'results/dev_aux/task876/games.jsonl';gs=[json.loads(l) for l in P.open(encoding='utf-8')];table={(g['profile'],g['opponent'],g['root']['seed'],g['color']):g for g in gs};pairs=[];totals=[]
def state(g):
 t=g['termination'];return 'C' if t['kind'].startswith('cap') else 'D' if t['winner'] is None else 'W' if t['winner']==g['color'] else 'L'
def score(g):return F(1 if state(g)=='W' else -1 if state(g)=='L' else 0)
for opp in ['unit_search','uniform_random']:
 counts=collections.Counter();trans=collections.Counter();rowpairs=[]
 for seed in sorted(set(g['root']['seed'] for g in gs)):
  for color in [0,1]:
   a,b=table['unit',opp,seed,color],table['random_ratio',opp,seed,color];qa=[q for q in a['queries'] if q['player']=='candidate'];qb=[q for q in b['queries'] if q['player']=='candidate'];comparable=bool(qa and qb)
   if comparable:assert qa[0]['history']==qb[0]['history'];counts['first_candidate_move_comparable']+=1;counts['first_candidate_move_changed']+=qa[0]['bestmove']!=qb[0]['bestmove']
   changed=a['actions']!=b['actions'];counts['full_action_sequence_changed']+=changed;counts['true_terminal_contribution_changed']+=score(a)!=score(b);counts['both_uncertain']+=state(a)==state(b)=='C';counts['same_observed_win_loss_draw_class']+=state(a)==state(b) and state(a)!='C';trans[state(a)+'->'+state(b)]+=1
   row=dict(seed=seed,color=color,opponent=opp,unit_outcome=state(a),other_outcome=state(b),action_sequence_changed=changed,first_candidate_move_changed=qa[0]['bestmove']!=qb[0]['bestmove'] if comparable else None,terminal_delta=str(score(b)-score(a)));pairs.append(row);rowpairs.append(row)
 for profile in ['unit','random_ratio']:
  gg=[g for g in gs if g['profile']==profile and g['opponent']==opp];co=collections.Counter(state(g) for g in gg);n=len(gg);jh=sum(score(g) for g in gg)/n;c=F(co['C'],n);totals.append(dict(profile=profile,opponent=opp,N=n,counts=dict(co),J24=str(jh),unresolved_fraction=str(c),eventual_net_value_identification_interval=[str(jh-c),str(jh+c)],bound_scope='Conservativealgebraic bound only assuming eachunresolvedeventualreturn in[-1,1]; no assumptionitwillfinish/no probabilityestimate.'))
 counts['paired_cases']=len(rowpairs);print(opp,dict(counts),dict(trans));totals.append(dict(opponent=opp,pair_counts=dict(counts),transitions=dict(trans)))
result=dict(status='QUALIFIED_NB104_ZERO_GO_PRICE_INFORMATION_REVIEW',source_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),totals=totals,pairs=pairs,new_go=0,new_fit_epochs=0,scope='Boundeduser-requestedmethodreview, notnewresearchsegment/durationsample. All52pairedtraincases only; noholdoutread/newgames/humanfitness. Observedtwo-priceinvariance notproofallpricesinvariant; trueoutcomechange notcertaintyofeventualvalue.');(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('SUMMARY',json.dumps(totals))
