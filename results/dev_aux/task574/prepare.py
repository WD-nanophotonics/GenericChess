import json,time,random,sys,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task574'
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
policy=dict(seeds=list(range(2026104510,2026104520)),prefix=40,unavailable='Beforegeneration freezefirstterminalpolicy, retainallmissing/no replacements',question='Do fixedweak-opponent gains survive finitepopulation feedback onnewindependentfamilies?',direction='New574 onlyINPUTS; useALLeightactualendpoints+twoinitials, dedupaliases; no sourcehumanvector/opponent/fitness, no source-distance selection',frozen_at=time.time());(O/'input_policy.json').write_text(json.dumps(policy,indent=2),encoding='utf-8');roots=[];missing=[]
for i,seed in enumerate(policy['seeds']):
 b=A.shogi.Board();f=dict(seed=seed,index=i,phase='population_pilot',initial_sfen=b.sfen(),history=[]);keys=[G.key(b)];checks=[b.is_check()];movers=[];rng=random.Random(seed)
 for ply in range(40):
  t=G.terminal(b,keys,checks,movers)
  if t:missing.append(dict(seed=seed,ply=ply,terminal=t));break
  u=rng.choice(sorted(m.usi() for m in b.legal_moves));movers.append(b.turn);b.push_usi(u);f['history'].append(u);keys.append(G.key(b));checks.append(b.is_check())
 else:
  t=G.terminal(b,keys,checks,movers)
  if t:missing.append(dict(seed=seed,ply=40,terminal=t));continue
  f['expected_sfen']=b.sfen();roots.append(f)
profiles=[];source={}
for route,tasks in [('pure24',[554,555]),('mixed12',[565,566])]:
 for task in tasks:
  p=R/f'results/dev_aux/task{task}/endpoints.json';source[task]=hashlib.sha256(p.read_bytes()).hexdigest();ep=json.loads(p.read_bytes())
  for e in ep['endpoints']:
   for stage,w in [('initial',e['initial']),('endpoint',e['endpoint'])]:
    if not any(x['weights']==w for x in profiles):profiles.append(dict(weights=w,names=[]))
    next(x for x in profiles if x['weights']==w)['names'].append(route+'-'+ep['opponent']+'-'+e['family']+'-'+stage)
d=dict(question=policy['question'],input_policy=policy,roots=roots,unavailable=missing,profiles=profiles,source_endpoints_sha256=source,cap=24,nodes=1024,policy='warm_game',executable_sha256='c69d96c10244b65da124d66c653449bc701680f4e3da05ec48b3979ef950d2e2',pairs='ALLunorderedprofilepairs/BOTHcandidatecolors/ALLeligiblefreshroots; bothactorsownfixedmaterial1handSEEprices, no extrafit/human/sourcefitness',declared_max_games=len(profiles)*(len(profiles)-1)//2*len(roots)*2,estimated_cost='Expected1-4min up to900shortgames/600sfuse after implementingfinitepairprotocol; no query/game/fitness executed bypreparation.',decision='If terminalfeedback isflatdo notreusepureterminal learnerunchanged. If population reversesweakopponent gains, consider predeclaredpopulationfitness; any sourceagreement remains descriptive, no automatichumanvectorselection/epochs.',scope='NEXTINPUTSONLY, NOTactualpopulationexperiment/learning/consensus/independentvalidationresult. Needrow-specific opponentweights anddualrole priceACKaudit, same fullhistory/mate/repetition/stops. No product/default/UI/othercheckout writes.')
(O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8');print(json.dumps(dict(status='INPUTS_ONLY',profiles=len(profiles),eligible_roots=len(roots),unavailable=missing,declared_max_games=d['declared_max_games'],actual_go=0)))
