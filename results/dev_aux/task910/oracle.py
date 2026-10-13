from pathlib import Path
import json,time,sys,os
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task911';O.mkdir(exist_ok=False);p=json.loads((R/'results/dev_aux/task910/plan.json').read_bytes());begin=time.monotonic();global_deadline=begin+600
sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
class Budget(Exception):pass
rows=[]
with (O/'cases.jsonl').open('w',encoding='utf-8') as j:
 for root in p['roots']:
  for attacker in p['attacker_colors']:
   t=time.monotonic();deadline=min(t+10,global_deadline);b=C.Board(root['initial_sfen']);nodes=0;terminal_nodes=0;horizon_nodes=0;memo={};states=[' '.join(b.sfen().split()[:3])];movers=[];checks=[]
   def visit(depth):
    global nodes,terminal_nodes,horizon_nodes
    nodes+=1
    if nodes>p['node_cap'] or time.monotonic()>=deadline:raise Budget()
    term=V.terminal(b,states,movers,checks)
    if term:
     terminal_nodes+=1;return term['winner']==attacker
    if depth==0:horizon_nodes+=1;return False
    key=(tuple(states),tuple(movers),tuple(checks),depth)
    if key in memo:return memo[key]
    actor=b.turn;legal=sorted(list(b.legal_moves),key=C.move_to_usi);result=False if actor==attacker else True
    for m in legal:
     movers.append(actor);b.push(m);checks.append(bool(b.is_check()));states.append(' '.join(b.sfen().split()[:3]))
     try:v=visit(depth-1)
     finally:states.pop();checks.pop();b.pop();movers.pop()
     if actor==attacker and v:result=True;break
     if actor!=attacker and not v:result=False;break
    memo[key]=result;return result
   try:found=visit(p['horizon']);status='PROVED_FORCE_WIN_WITHIN6' if found else 'EXHAUSTED_NO_FORCE_WIN_WITHIN6'
   except Budget:found=None;status='UNKNOWN_BUDGET'
   assert b.sfen()==root['initial_sfen'] and len(states)==1 and not movers and not checks
   row=dict(root=root,attacker=attacker,status=status,nodes=nodes,terminal_nodes=terminal_nodes,horizon_nodes=horizon_nodes,memo_entries=len(memo),seconds=time.monotonic()-t);rows.append(row);j.write(json.dumps(row)+'\n');j.flush();os.fsync(j.fileno());print(root['variant'],root['seed'],attacker,status,nodes,round(row['seconds'],3),flush=True)
   if time.monotonic()>=global_deadline:break
  if time.monotonic()>=global_deadline:break
result=dict(status='FINITE_FORCE_ORACLE_CASES_PRESERVED',cases=len(rows),expected_cases=len(p['roots'])*2,nodes=sum(r['nodes'] for r in rows),seconds=time.monotonic()-begin,counts={s:sum(r['status']==s for r in rows) for s in ['PROVED_FORCE_WIN_WITHIN6','EXHAUSTED_NO_FORCE_WIN_WITHIN6','UNKNOWN_BUDGET']},new_go=0,scope=p['semantics']);(O/'result.json').write_text(json.dumps(result,indent=2));print(result)
