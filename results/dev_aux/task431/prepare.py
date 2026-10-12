from pathlib import Path
import json,hashlib
R=Path.cwd();s=(R/'results/dev_aux/task417/prepare.py').read_text(encoding='utf-8');s=s.replace('task417','task431').replace('2026102910','2026103010').replace('2026102914','2026103014').replace('2026102980','2026103080').replace('2026102984','2026103084').replace('2026102991','2026103091').replace('2026102992','2026103092')
# Execute the prior generator with explicitly changed freshseed premise; then replace future-study conditions BEFORE ANY new go.
exec(compile(s,'task431/newroots','exec'));O=R/'results/dev_aux/task431';d=json.loads((O/'declaration.json').read_text(encoding='utf-8'));d.update(question='Does learning under matched8192 ratherthan1024 improve transfer, instead of optimizingshallow search errors?',arms=['random1024','random8192'],train_opponent='uniform legal indexedperturn random',training_node_budgets=[1024,8192],development_environments=['unit','random'],development_node_budgets=[1024,8192],freeze='BOTHbudget ALL2starts endpoints beforeANYdevelopment; ALL2initials+4endpoints inALL4node/opponent environments, no endpoint/node/H selector',selection='same24fixedjointdirections/log.25/strictgain/49vectorsmax perstart perbudget; originalgoal,cap24; no extraschedule/gain/goal/epoch/human selection',estimated_cost='newpairedrandomfit~2.4+3min from430workcurve; ALL192logicalcrossdev ~1min; allactualpricefirst/lastcoldqualification ~1min; totalexpected<10min/1800sfuseTOTAL,1worker. ConsultDotfirstifsingleprojectrunestimateever>1h.',qualification='allNEWactualfitpricevectors first&lastactualqueries compareold25/reuse26 atdeclarednodebudget, fullprices/PV/history/journal. No retiming/refittingoldresults.',status='INPUTS_FROZEN_ONLY; no newtraining/go/endpoints/development yet; nextsegment mustreadownsession/stops before launch')
(O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
# Independent generation and direction audit fromcshogi, no outcomes.
import cshogi as C,random,sys
sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
for f in d['roots']:
 b=C.Board(f['initial_sfen']);rng=random.Random(f['seed']);states=[' '.join(b.sfen().split()[:3])];movers=[];checks=[]
 for u in f['history']:
  assert V.terminal(b,states,movers,checks) is None;legal=sorted(C.move_to_usi(m) for m in b.legal_moves);assert rng.choice(legal)==u;m=b.move_from_usi(u);assert b.is_legal(m);movers.append(b.turn);b.push(m);checks.append(bool(b.is_check()));states.append(' '.join(b.sfen().split()[:3]))
 assert b.sfen()==f['expected_sfen'] and V.terminal(b,states,movers,checks) is None
rng=random.Random(d['direction_seed']);assert d['directions']=={p['name']:[[rng.choice([-1,1]) for a in d['axes']] for _ in range(24)] for p in d['initial_profiles']}
out=dict(status='PASS_INPUTS_ONLY',roots=8,prefix_plies=320,directions=48,new_go=0,new_games=0,declaration_sha256=hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest());(O/'input_audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(out)
