"""One fixed supported opponent setting; paired development feedback, never Elo claim."""
import sys,json,time,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'.local_agent/certificate_source/python-chess')]
import chess,chess.engine
import scripts.chess_development as d
p=Path(__file__).parent;mode=sys.argv[1];assert mode in ('price','original');decl=json.loads((p/'declaration.json').read_bytes());out=p/(mode+'.json');active=p/(mode+'-active.json');assert not out.exists()
config=ROOT/'.local_agent/mature-search/material-variants.ini';ref=ROOT/'.local_agent/stockfish-reference/stockfish/stockfish-windows-x86-64.exe';binary=ROOT/decl['binaries'][mode]['path'];sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(binary)==decl['binaries'][mode]['sha256'] and sha(ref)==decl['reference_sha256'] and sha(config)==decl['config_sha256'] and sha(ROOT/'scripts/chess_development.py')==decl['adapter_sha256']
suite=json.loads((ROOT/'.local_agent/mature-openings/suite.json').read_bytes());assert sha(ROOT/'.local_agent/mature-openings/suite.json')==decl['suite_sha256']
class Player(d.UciMaterial):
 def choose(self):
  move,row=super().choose();row.update(leaf_mode=mode,leaf_binary_sha256=decl['binaries'][mode]['sha256'],requested_seconds=1);return move,row
def stopcheck():
 for n in ('rollout','advisor','slack'):
  v=json.loads((ROOT/'.local_agent'/(n+'.json')).read_bytes())
  if v.get('user_paused') or v.get('stopped'):raise KeyboardInterrupt('User stop retained')
cost={k:dict(writes=0,bytes=0,seconds=0.) for k in ('active','cohort')}
def save(kind,value):
 t=time.perf_counter();target=active if kind=='active' else out;d.write_record(target,value,indent=None);cost[kind]['writes']+=1;cost[kind]['bytes']+=target.stat().st_size;cost[kind]['seconds']+=time.perf_counter()-t
c=d.compile_ruleset_for_execution(d.build_western_chess_ruleset());report=dict(declaration=decl,mode=mode,games=[],complete=False);start=time.perf_counter();save('cohort',report)
try:
 for case in suite['cases']:
  for policy in d.POLICIES:
   for color in (0,1):
    stopcheck()
    with chess.engine.SimpleEngine.popen_uci([str(binary),'load',str(config)],timeout=15) as e,chess.engine.SimpleEngine.popen_uci(str(ref),timeout=15) as other:
     e.configure({'Threads':1,'Hash':16,'Use NNUE':False});other.configure({'Threads':1,'Hash':16,'UCI_LimitStrength':True,'UCI_Elo':decl['opponent_setting']})
     local=Player(e,case['fen'],policy,1);external=d.UciOpponent(other,case['fen'],50000)
     tags=dict(id=case['id'],table=policy,candidate_color=color,mode=mode)
     def progress(g):save('active',dict(**tags,**g));stopcheck()
     g=d.play_game(case['fen'],c,policy if color==0 else 'uci_reference','uci_reference' if color==0 else policy,d.SearchLimits(max_depth=2,max_nodes=2048,max_time_seconds=1),160,progress,external=external,local_external=local,prefix=case['opening_uci']);report['games'].append(dict(**tags,**g));save('cohort',report);print(mode,len(report['games']),g['end'],g['winner'],g['plies_played'],flush=True)
 report['complete']=True
finally:report.update(wall_seconds=time.perf_counter()-start,recording_cost_before_final_save={k:dict(v) for k,v in cost.items()});save('cohort',report)
d.write_record(active,dict(complete=report['complete'],games=len(report['games'])),indent=None)
