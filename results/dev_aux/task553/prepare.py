import sys,json,random,time,math,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task553'
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
policy=dict(train_seeds=list(range(2026104310,2026104342)),development_seeds=list(range(2026104380,2026104396)),prefix=40,unavailable='Freezebeforegeneration; recordfirstterminalbefore40 andretain no replacement/reseed; no outcome/reference screening',family='Eachseed independentlygeneratedfull40plyrandomtrajectory, no branchsiblings/familycountinflation',frozen_at=time.time());(O/'input_policy.json').write_text(json.dumps(policy,indent=2),encoding='utf-8')
roots=[];missing=[]
for phase,seeds in [('train',policy['train_seeds']),('development',policy['development_seeds'])]:
 for i,seed in enumerate(seeds):
  b=A.shogi.Board();initial=b.sfen();hist=[];keys=[G.key(b)];checks=[b.is_check()];movers=[];rng=random.Random(seed)
  for ply in range(40):
   t=G.terminal(b,keys,checks,movers)
   if t:missing.append(dict(seed=seed,phase=phase,index=i,ply=ply,termination=t,history=hist,final_sfen=b.sfen()));break
   legal=sorted(m.usi() for m in b.legal_moves);u=rng.choice(legal);movers.append(b.turn);b.push_usi(u);hist.append(u);keys.append(G.key(b));checks.append(b.is_check())
  else:
   t=G.terminal(b,keys,checks,movers)
   if t:missing.append(dict(seed=seed,phase=phase,index=i,ply=40,termination=t,history=hist,final_sfen=b.sfen()));continue
   roots.append(dict(phase=phase,index=i,seed=seed,initial_sfen=initial,history=hist,expected_sfen=b.sfen()))
profiles=json.loads((R/'results/dev_aux/task551/declaration.json').read_bytes())['profiles'];rng=random.Random(2026104391);directions={p['name']:[[rng.choice([-1,1]) for _ in range(12)] for _ in range(24)] for p in profiles}
d=dict(question='Does largerindependentfamily training recoverdescriptive sourcepiecevalues quickly with cheapactualmature search underpureterminalfeedback?',premise='Newnativecontroller validated551/552;32 independenttrain16dev, compared withold4rootstudy; notold532 completion/rerun. Same1024warmhandSEE, objectivepureterminal only, no handtunedfitness.',roots=roots,unavailable=missing,initial_profiles=profiles,opponents=['unit','random'],fixed_opponent=[0]+[90]*7+[0]+[90]*6+[0],axes=[2,3,4,5,6,7,9,10,11,12,13,14],directions=directions,direction_seed=2026104391,cap=24,nodes=1024,seed_base=2026104392,random_seed_base=2026104392,objective='truewin+32/trueloss-32;drawandunfinished0, rawphysicalmixed goals retained separately',coordinate='FixedP90K0/free12jointlog.25/roundpositiveclip32..4096/basefirststrictimprovement;24directionsnoextension',policy='warm_game',controller='native_rules',executable_sha256='c69d96c10244b65da124d66c653449bc701680f4e3da05ec48b3979ef950d2e2',fuse=2400,estimated_cost='Single2opponent*2start*49trainbatches*64cells max12544train+max384devgames; expected5-12minutes nativecost based551 plus actualjournals; no extra workersfees/longchessgames. Onecombinedinterruptiblecaller frozenwall2400s.',freeze='ALL4endpoints beforeANY development game/metric/source reference; alluniqueprices evaluatedBOTHopponents/all16dev/colors; no humanfitness/root/H/selector/stop',scope='FixedstandardShogi NoEnteringKing/material1handSEE/selectiveYaneuraou/1024warmgame resource; sourceagreement descriptive nothumanconsensus/universaloptimum; no arbitrarygeneratedrules claim')
(O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8');print(len(roots),missing)
