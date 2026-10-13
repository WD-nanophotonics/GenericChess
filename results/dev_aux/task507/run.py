import sys,json,time,random,os,hashlib,re
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task507';assert not(O/'result.json').exists();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));sys.path.insert(0,str(R/'results/dev_aux/task381'));import adapter as A;import run as G;import audit as V
d=json.loads((O/'declaration.json').read_text(encoding='utf-8'));d['seed_base']=d['random_seed_base'];A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];PHASES=[];current={}
class GameEngine(A.Engine):
 def __init__(self,w,journal,policy):self.policy=policy;self.calls=0;super().__init__(w,journal)
 def search(self,initial,history,nodes=1024):
  t0=time.perf_counter();ready=[]
  if self.policy=='cold_per_query':self.send('isready');ready=self.until(lambda x:x=='readyok')
  t1=time.perf_counter();self.position(initial,history);self.send('auxstate');state=self.until(lambda x:x.startswith('info string auxstate '))[-1];t2=time.perf_counter();t=time.monotonic();cmd=f'go nodes {nodes}';self.send(cmd);lines=self.until(lambda x:x.startswith('bestmove '));t3=time.perf_counter();q=dict(initial_sfen=initial,history=list(history),weights=self.w,nodes_limit=nodes,cold_isready=ready,state=state,command=cmd,lines=lines,bestmove=lines[-1].split()[1],seconds=time.monotonic()-t,reset_policy=self.policy,query_index_in_game=self.calls);self.calls+=1
  if self.journal:self.journal.write(json.dumps(q)+'\n');self.journal.flush();os.fsync(self.journal.fileno())
  PHASES.append(dict(**current,cold_ready=t1-t0,state_position=t2-t1,go_roundtrip=t3-t2,whole_search_call=time.perf_counter()-t0));return q
src=(R/'results/dev_aux/task410/run_random.py').read_text(encoding='utf-8');src=src[src.index('def random_game('):src.index('arm=sys.argv[1]')];src=src.replace('out=dict(weights=w', 'out=dict(reset_policy=policy,weights=w');exec(compile(src,'actual_warm_game_random','exec'));t0=time.perf_counter();rows=[];acks=[];startups=[];case=0
with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
 for p in d['initial_profiles']:
  for f in d['roots']:
   for color in (0,1):
    order=d['policies'] if case%2==0 else list(reversed(d['policies']))
    for policy in order:
     G.stop();assert time.perf_counter()-t0<180;current=dict(case=case,family=p['name'],root_seed=f['seed'],color=color,policy=policy);st=time.perf_counter();ec=GameEngine(p['weights'],qj,policy);startups.append(dict(**current,wall=time.perf_counter()-st));acks.append(dict(**current,weights=ec.w,prices=ec.prices,constructor_ready=True,constructor_scope='freshgame process, no crossgame/price TT/history'));st=time.perf_counter()
     try:g=random_game(ec,p['weights'],f,color,gj,t0+180)
     finally:ec.close()
     rows.append(dict(**current,goal=g['goal'],termination=g['termination'],plies=len(g['actions']),go=len(g['queries']),game_wall=g['seconds'],producer_game_close_wall=time.perf_counter()-st,source=dict(file='results/dev_aux/task507/games.jsonl',line=len(rows)+1)))
    case+=1
summary=[]
for policy in d['policies']:
 rs=[x for x in rows if x['policy']==policy];ph=[x for x in PHASES if x['policy']==policy];summary.append(dict(policy=policy,games=len(rs),go=sum(x['go'] for x in rs),total_plies=sum(x['plies'] for x in rs),wins=sum(x['termination']['winner']==x['color'] for x in rs),mean_goal=str(sum(Fraction(x['goal']) for x in rs)/len(rs)),game_wall_sum=sum(x['game_wall'] for x in rs),startup_wall_sum=sum(x['wall'] for x in startups if x['policy']==policy),cold_ready_wall_sum=sum(x['cold_ready'] for x in ph),go_roundtrip_wall_sum=sum(x['go_roundtrip'] for x in ph)))
out=dict(status='PASS_COMPLETED_PILOT',new_games=len(rows),actual_go=len(PHASES),rows=rows,summary=summary,query_phases=PHASES,startups=startups,price_acks=acks,seconds=time.perf_counter()-t0,scope=d['scope']);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(status=out['status'],games=len(rows),actual_go=len(PHASES),summary=summary,seconds=out['seconds']),ensure_ascii=True))
