"""Freeze new mode0/3 learning with freshseeds and unchangedcheapobjective."""
from pathlib import Path
import json,hashlib,importlib.util,random,chess
R=Path.cwd();O=R/'results/dev_aux/task152';O.mkdir(exist_ok=True)
if (O/'declaration.json').exists():raise FileExistsError('frozen')
spec=importlib.util.spec_from_file_location('G152',R/'results/dev_aux/task104/short_game.py');G=importlib.util.module_from_spec(spec);spec.loader.exec_module(G)
old=R/'results/dev_aux/task140';d=json.loads((old/'declaration.json').read_bytes());build=json.loads((R/'results/dev_aux/task147/build.json').read_bytes())
d.update(task_id='152',question='Does repairedcandidateprice treatment enable quickmaterial learning under a newselectiontrajectory?',new_premise='Mode3 candidateMG/EGtables+fiveSEErecaptureconstants+priceorderedstandardattackerclasses. Oldmode1/3fixedweightdeployment cannotjudge mode3relearning. Samec378binary0vs3isolates jointpricehandling, fixedmargins/otherSEEapproxremain.',start_seeds=[303,304,305],alignment_arms=[0,3],seed_alignment_order=[[303,0],[303,3],[304,3],[304,0],[305,0],[305,3]],binary_relative=build['binary_relative'],binary_sha256=build['binary_sha256'],qualification_result_sha256='PENDING32ROOTQUALIFICATION',train_opening_seeds=[2007000,2007191],train_random_seeds=[2107000,2107191],heldout_opening_seeds=list(range(2009000,2009008)),heldout_random_seeds=list(range(2109000,2109008)),scope='Freshstarts/openingseeds within exposedmethodfamily; samebinary0/3. StandardChessonly, expertsearchpriors/fixedmargins andgeometricSEEapproxremain; nohumanfit orproductdefaultchange.',cost='7104fixedslots estimated12-20minutes,1800sinclusivefuse; singleownedengine, noextra workers/fee, no expectedhour projectrun.',source_method_declaration_sha256=hashlib.sha256((old/'declaration.json').read_bytes()).hexdigest())
fixtures={}
for phase in ('train','heldout'):
 for i in range(192 if phase=='train' else 8):
  seed=(2007000 if phase=='train' else 2009000)+i
  try:moves=G.opening(seed,plies=24);terminal=False;termination=None
  except ValueError:
   b=chess.Board();rng=random.Random(seed);moves=[]
   for _ in range(24):
    if b.is_game_over(claim_draw=False):break
    move=rng.choice(sorted(b.legal_moves,key=lambda x:x.uci()));b.push(move);moves.append(move.uci())
   assert b.is_game_over(claim_draw=False);terminal=True;termination=b.outcome(claim_draw=False).termination.name
  fixtures[str(seed)]=dict(seed=seed,moves=moves,terminal=terminal,termination=termination,phase=phase)
(O/'fixtures.json').write_text(json.dumps(fixtures,indent=2),encoding='utf-8');d['fixtures_sha256']=hashlib.sha256((O/'fixtures.json').read_bytes()).hexdigest();d['terminal_input_seeds']=[k for k,v in fixtures.items() if v['terminal']]
# Freeze before anynewengine outcome.
(O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
source=(old/'run.py').read_text(encoding='utf-8')
source=source.replace("O=R/'results/dev_aux/task140'","O=R/'results/dev_aux/task152'")
source=source.replace("binary=R/'.local_agent/alignment-build/fairy-toggle.exe'","binary=R/D['binary_relative']")
for a,b in [('1007000','2007000'),('1009000','2009000'),('1107000','2107000'),('1109000','2109000')]:source=source.replace(a,b)
robust=(R/'results/dev_aux/task142/run.py').read_text(encoding='utf-8')
a=robust.index(' def stop():');b=robust.index(' stop();assert',a);block=robust[a:b].replace(".local_agent/alignment-build/flag-read-recovery.jsonl",".local_agent/material-mode3/flag-read-recovery.jsonl")
source=source.replace(' stop=lambda:A.stop_check(R);stop();',block+' stop();',1)
source=source.replace("D=json.loads((O/'declaration.json').read_bytes());F=","D=json.loads((O/'declaration.json').read_bytes());assert json.loads((O/'qualification.json').read_bytes())['complete'];F=",1)
(O/'run.py').write_text(source,encoding='utf-8')
print(json.dumps(dict(frozen=True,starts=d['start_seeds'],modes=d['alignment_arms'],slots=d['total_slots'],terminalinputs=d['terminal_input_seeds'],binary=build['binary_sha256'])))
