import json,time,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task210';sp=importlib.util.spec_from_file_location('P210',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P);M=P.M;D=json.loads((O/'declaration.json').read_bytes())
def execute():
 assert not (O/'result.json').exists();P.stop();binary=R/'.local_agent/alignment-order/fairy-order-toggle.exe';assert hashlib.sha256(binary.read_bytes()).hexdigest()==D['binary_sha256'];started=time.monotonic();deadline=started+60;rows=[];e=M.start(binary,3,deadline,P.stop)
 try:
  for c in D['cases']:
   probes,ack=M.configure(e,c['weights'],O/'variant.ini',deadline,P.stop);b=chess.Board(c['root_fen'])
   for m in c['full_history']+c['pv']:b.push_uci(m)
   assert b.fen()==c['pv_leaf_fen'] and not b.is_check();white=sum(c['weights'][k]*(len(b.pieces(i+1,True))-len(b.pieces(i+1,False))) for i,k in enumerate('PNBRQ'));e.send('position fen '+c['root_fen']+' moves '+' '.join(c['full_history']+c['pv']));e.send('eval');reply=e.ready();lines=[s for s in reply if s.startswith('Final evaluation')];assert len(lines)==1;measured=float(lines[0].split()[2]);assert abs(measured-white/208)<=.011;rows.append(dict(case=c,raw_eval=reply,measured_white_pawns=measured,expected_white_pawns=white/208,price_probes=probes,table_ack=ack))
 finally:e.close()
 out=dict(complete=True,cases=len(rows),actual_price_probes=20,actual_literal_leaf_evals=4,root_go_queries=0,new_games=0,rows=rows,seconds=time.monotonic()-started,binary_sha256=D['binary_sha256'],scope='Actualleafevalmatchespurematerial; previouslyreportedrootcp differs. ShowsliteralPVendpoint alone notrootvalue/TDtarget certificate, no specificqpruningcause orenginebug proof.');P.A.atomic_json(O/'result.json',out);print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2))
if __name__=='__main__':execute()
