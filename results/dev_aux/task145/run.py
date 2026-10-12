"""Frozenactual SEE threshold queries and legal target-capture oracle witness."""
import json,time,hashlib,sys,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task145';O.mkdir(exist_ok=True)
s=importlib.util.spec_from_file_location('toggle139for145',R/'results/dev_aux/task139/run.py');M=importlib.util.module_from_spec(s);s.loader.exec_module(M);A=M.A
D=json.loads((R/'results/dev_aux/task144/declaration.json').read_bytes());W=D['witness'];B=json.loads((R/'results/dev_aux/task144/build.json').read_bytes());assert B['status']=='COMPLETE'
def material(b,color,w):return sum(w[chess.piece_symbol(t).upper()]*(len(b.pieces(t,color))-len(b.pieces(t,not color))) for t in range(1,6))
def oracle(board,target,color,w,base):
 v=material(board,color,w)-base;children=[]
 for move in sorted(board.legal_moves,key=lambda x:x.uci()):
  if move.to_square==target and board.is_capture(move):
   board.push(move);score,node=oracle(board,target,color,w,base);board.pop();children.append(dict(move=move.uci(),value=score,child=node))
 alternatives=[v]+[x['value'] for x in children]
 result=(max if board.turn==color else min)(alternatives)
 return result,dict(fen=board.fen(),decline_value=v,turn=board.turn,legal_target_captures=children,value=result,scope='Restrictedcapture-on-one-target withdeclineoption; notfullchessWDL.')
def execute():
 if (O/'result.json').exists():raise FileExistsError('frozenexecution')
 binary=R/B['binary_relative'];assert hashlib.sha256(binary.read_bytes()).hexdigest()==B['binary_sha256']
 b=chess.Board(W['fen']);move=chess.Move.from_uci(W['move']);assert b.is_valid() and move in b.legal_moves;color=b.turn;base=material(b,color,W['candidate']);b.push(move);value,tree=oracle(b,move.to_square,color,W['candidate'],base);assert value==112
 started=time.monotonic();deadline=started+120;stop=lambda:A.stop_check(R);rows=[];complete=False
 try:
  for mode in (0,1,2):
   e=M.start(binary,mode,deadline,stop)
   try:
    probes,ack=M.configure(e,W['candidate'],O/'variant.ini',deadline,stop)
    e.send('position fen '+W['fen']);e.ready();answers=[]
    for threshold in W['thresholds']:
     e.send(f'devauxsee {W["move"]} {threshold}');reply=e.ready();raw=[line for line in reply if line.startswith('info string DEV_AUX SEE ')]
     if len(raw)!=1:raise ValueError('ambiguousSEEactualreply')
     tokens=raw[0].split();assert tokens[4]==W['move'] and int(tokens[5])==threshold
     answers.append(dict(threshold=threshold,actual_see_ge=bool(int(tokens[6])),candidate_target_oracle_ge=value>=threshold,raw=raw[0]))
    rows.append(dict(mode=mode,leaf_probes=probes,table_ack=ack,answers=answers))
   finally:e.close()
  complete=True
 except BaseException as ex:error=type(ex).__name__+': '+str(ex)
 out=dict(complete=complete,binary_sha256=B['binary_sha256'],witness=W,oracle_value=value,oracle_tree=tree,rows=rows,wall_seconds=time.monotonic()-started,scope='Oneactualprices-consistencycounterexample to table-onlylabel, not generalSEEcorrectness orengine-strength/learninggain. Fixedattackerorder remains, but thiswitnesshasoneattackerat eachrecapture.')
 if not complete:out['error']=error
 A.atomic_json(O/'result.json',out)
 summary=dict(complete=complete,queries=sum(len(r['answers']) for r in rows),seconds=out['wall_seconds'],oracle_value=value,modes=[dict(mode=r['mode'],mismatching_thresholds=[a['threshold'] for a in r['answers'] if a['actual_see_ge']!=a['candidate_target_oracle_ge']],answers=r['answers']) for r in rows],scope=out['scope'])
 A.atomic_json(O/'summary.json',summary);print(json.dumps(summary,indent=2));return 0 if complete else 3
if __name__=='__main__':sys.exit(execute())
