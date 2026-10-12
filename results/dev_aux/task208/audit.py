"""LiteralUCI PV replay and staticleaf score qualification, no claim it is search'schosenleaf."""
import json,time,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task208';P=R/'results/dev_aux/task187';sp=importlib.util.spec_from_file_location('P208',R/'results/dev_aux/task166/run.py');M=importlib.util.module_from_spec(sp);sp.loader.exec_module(M)
def execute():
 assert not (O/'analysis.json').exists();M.stop();started=time.monotonic();C=json.loads((P/'controller.json').read_bytes());count=dict(searches=0,no_scored_pv=0,illegal_pv=0,mate=0,mate_literal_checkmate=0,cp=0,cp_bound=0,cp_literal_terminal=0,cp_claim_draw=0,cp_leaf_in_check=0,cp_material_mismatch=0,cp_unbounded_nonterminal=0,cp_unbounded_nonterminal_material_mismatch=0);examples=[];complete=True
 for c in C['calls']:
  for ix,record in enumerate(c['result']['search_records']):
   if count['searches']%64==0:M.stop()
   if time.monotonic()-started>180:complete=False;break
   count['searches']+=1;pvlines=[t for t in record['uci_info'] if ' score ' in t and ' pv ' in t]
   if not pvlines:count['no_scored_pv']+=1;continue
   line=pvlines[-1];f=line.split();si=f.index('score');kind=f[si+1];sc=int(f[si+2]);pv=f[f.index('pv')+1:];b=chess.Board(record['root_fen'])
   for m in record['full_history']:b.push_uci(m)
   color=b.turn;illegal=False
   for text in pv:
    m=chess.Move.from_uci(text)
    if m not in b.legal_moves:illegal=True;break
    b.push(m)
   if illegal:count['illegal_pv']+=1
   terminal=b.outcome(claim_draw=False);claim=b.outcome(claim_draw=True);material=sum(c['weights'][k]*(len(b.pieces(i+1,color))-len(b.pieces(i+1,not color))) for i,k in enumerate('PNBRQ'));expected=int(max(-31507,min(31507,material))*100/208);bounds='lowerbound' in f or 'upperbound' in f
   if kind=='mate':count['mate']+=1;count['mate_literal_checkmate']+=b.is_checkmate();continue
   assert kind=='cp';count['cp']+=1;count['cp_bound']+=bounds;count['cp_literal_terminal']+=bool(terminal);count['cp_claim_draw']+=bool(claim and claim.winner is None);count['cp_leaf_in_check']+=b.is_check();mismatch=expected!=sc;count['cp_material_mismatch']+=mismatch
   if not bounds and not terminal and not illegal:count['cp_unbounded_nonterminal']+=1;count['cp_unbounded_nonterminal_material_mismatch']+=mismatch
   if mismatch and len(examples)<20:examples.append(dict(game=c['context']['name'],search_index=ix,weights=c['weights'],root_fen=record['root_fen'],full_history=record['full_history'],line=line,pv=pv,pv_leaf_fen=b.fen(),material=material,expected_cp=expected,reported_cp=sc,bounds=bounds,terminal=str(terminal),draw_claim=bool(claim and claim.winner is None),leaf_in_check=b.is_check()))
  if not complete:break
 out=dict(complete=complete,counts=count,mismatch_examples=examples,seconds=time.monotonic()-started,source_sha256=hashlib.sha256((P/'controller.json').read_bytes()).hexdigest(),scope='LiteralPVreplay only. Unbounded UCIlabelnotcertificateofstaticPVendpoint minimax equality: q/selectivity/TT/draw/bounds/PVtruncation maydiffer. Mismatch notenginebug/learningfailurecause. Allcurrenthistories preserved, no game rerun/teacher/selflabel training.')
 (O/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(complete=complete,counts=count,seconds=out['seconds']),indent=2))
if __name__=='__main__':execute()
