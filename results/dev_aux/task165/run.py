"""Predeclaredlegalnoncheckingpromotion readbacks, oldcheckedwitness unchanged."""
import json,time,hashlib,sys,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task165';O.mkdir(exist_ok=True)
D=dict(task_id='165',question='Can actualmaterialpromotion readback be measured on legalnonchecking geometry, withoutforcingillegalturn?',fen='7r/6P1/1k6/8/8/8/8/6K1 w - - 0 1',moves=['g7h8n','g7h8b','g7h8r','g7h8q'],weights=dict(P=208,K=0,N=2000,B=52,R=396,Q=510),modes=[0,3],deadline_seconds=120,expected_promotion_capture_gains=dict(n=2188,b=240,r=584,q=698),scope='Newlegalfixture relocateskings beforeoutputs; originalTask153in-checktracesremainUNAVAILABLE. Measurespricecount semantics, notWDL orpromotionpolicygain; sourceSEE0specialshortcut unchanged.',cost='10evalrequests+40singlepiecequalificationprobes, no go/training, expected<2s. Sequentialafteractivegamebatch.')
def execute():
 if (O/'result.json').exists():raise FileExistsError('frozen')
 (O/'declaration.json').write_text(json.dumps(D,indent=2),encoding='utf-8')
 spec=importlib.util.spec_from_file_location('M165',R/'results/dev_aux/task139/run.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M);A=M.A;binary=R/'.local_agent/alignment-order/fairy-order-toggle.exe'
 assert hashlib.sha256(binary.read_bytes()).hexdigest()=='c378f0b3fc9f99d48e3089294a7c6adf5d5215bcac070200424d0d24f4d4b460'
 started=time.monotonic();deadline=started+120;stop=lambda:A.stop_check(R);root=chess.Board(D['fen']);assert root.is_valid() and not root.is_check();rows=[]
 def trace(e,b):
  assert b.is_valid() and not b.is_check();w=D['weights'];expected=sum(w[chess.piece_symbol(t).upper()]*(len(b.pieces(t,True))-len(b.pieces(t,False))) for t in range(1,6))
  e.send('position fen '+b.fen());e.send('eval');reply=e.ready();lines=[x for x in reply if x.startswith('Final evaluation')];assert len(lines)==1 and 'none' not in lines[0];measured=float(lines[0].split()[2]);assert abs(measured-expected/208)<=.011
  return dict(fen=b.fen(),expected_material=expected,measured_white_pawns=measured,raw=lines[0])
 for mode in D['modes']:
  e=M.start(binary,mode,deadline,stop)
  try:
   probes,ack=M.configure(e,D['weights'],O/'variant.ini',deadline,stop);before=trace(e,root)
   for move in D['moves']:
    board=root.copy();m=chess.Move.from_uci(move);assert m in board.legal_moves;board.push(m);after=trace(e,board)
    gain=after['expected_material']-before['expected_material'];assert gain==D['expected_promotion_capture_gains'][move[-1]]
    rows.append(dict(mode=mode,move=move,before=before,after=after,gain=gain,price_probes=probes,table_ack=ack))
  finally:e.close()
 result=dict(complete=True,rows=rows,actual_eval_requests=10,singlepiece_probe_calls=10,seconds=time.monotonic()-started,scope=D['scope'])
 A.atomic_json(O/'result.json',result);print(json.dumps(dict(complete=True,eval_requests=10,singlepiece_probe_calls=10,seconds=result['seconds'],gains=[r['gain'] for r in rows])))
if __name__=='__main__':execute()
