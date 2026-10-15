import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,importlib.util,time,hashlib,re
R=Path.cwd();O=R/'results/dev_aux/task1707';plan=json.loads((R/'results/dev_aux/task1702/plan.json').read_bytes());C4=tuple(json.loads((R/'results/dev_aux/task1678/selection.json').read_bytes())['selected']['POOLED']);C8=tuple(json.loads((R/'results/dev_aux/task1703/selection.json').read_bytes())['selected']['POOLED']);profiles=sorted({(720,720,720,720),C4,C8});base=(R/'results/dev_aux/task1688/variant.ini').read_text();names={p:'aux_align_'+str(p[0])+'_'+str(p[3]) for p in profiles};ini=base
for p in profiles:
 v=f'p:{p[3]} n:{p[1]} b:{p[2]} r:{p[0]} q:1664';ini+=f'\n[{names[p]}:aux_pawn8]\npieceValueMg = {v}\npieceValueEg = {v}\n'
(O/'variant.ini').write_text(ini,encoding='ascii');(O/'plan.json').write_text(json.dumps({'status':'FROZEN_ALIGNED_TABLES_FEASIBILITY_BEFORE_QUERIES','profiles':profiles,'names':{str(k):v for k,v in names.items()},'candidate_sources':['task1678/selection.json','task1703/selection.json'],'source_refs':['alignment-order/source/psqt.cpp:206-208,310-316','leaf-rnbp-46/source/uci.cpp:407-438'],'question':'Canexistingvariantconfig alignleaf/native/SEE-capture tables whilekeepingqualifiedrules? Existingstudies variedONLYEvalPieceValue; futureglobalpriceclaimneedsactualtransportvalidation.','seconds_cap':180,'expected_seconds':10,'max_go':32,'max_perft':96,'humanfit':False,'no_build':True},indent=2))
def mod(n,path):
 sp=importlib.util.spec_from_file_location(n,R/path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
T=mod('T','results/dev_aux/task1688/rules.py');P=mod('P','results/dev_aux/task166/run.py');choices=[json.loads(l) for l in (R/'results/dev_aux/task1703/choices.jsonl').open()];cases=choices[:32];unit=[x for x in choices if x['price']==[720,720,720,720]][:32];start=time.monotonic();e=None;error=None;acks=[];perft=[];replay=[];deadline=start+180
try:
 e=P.M.start(R/'.local_agent/leaf-rnbp-46/fairy-leaf-rnb.exe',3,deadline,P.stop)
 for n,v in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(O/'variant.ini'))]:e.send(f'setoption name {n} value {v}');e.ready()
 for p in profiles:
  e.send('setoption name UCI_Variant value '+names[p]);a=e.ready();assert any(z.startswith('info string variant '+names[p]+' files 8 ranks 8 ') for z in a);e.send('devauxleafrnbp '+' '.join(map(str,p)));a=e.ready();expected='info string DEV_AUX leafRNBP '+' '.join(map(str,p))+f' nativeP {p[3]} nativeR {p[0]} nativeN {p[1]} nativeB {p[2]} captureP {p[3]} captureR {p[0]} captureN {p[1]} captureB {p[2]}';assert expected in a,a;acks.append({'price':p,'variant':names[p],'ack':a})
  for x in cases:
   P.stop();assert time.monotonic()<deadline;s=tuple(x['state']);e.send('position fen '+T.fen(s));e.send('go perft 1');raw=e.until(lambda l:'Nodes searched:' in l,max_lines=300);moves=sorted(m.group(1) for l in raw if(m:=re.fullmatch(r'([a-h][1-8][a-h][1-8][rnb]?):\s*\d+',l.strip())));assert moves==[u for u,t in T.moves(s)];perft.append({'price':p,'state':s,'raw':raw})
 e.send('setoption name UCI_Variant value '+names[(720,720,720,720)]);e.ready();e.send('devauxleafrnbp 720 720 720 720');e.ready()
 for x in unit:
  P.stop();assert time.monotonic()<deadline;e.send('ucinewgame');e.ready();e.send('position fen '+x['fen']);e.send(x['command']);raw=e.until(lambda l:l.startswith('bestmove '));e.ready();assert raw[-1].split()[1]==x['move'];clean=lambda a:[re.sub(r'\b(?:time|nps) \d+','TIME_OR_NPS',l) for l in a];assert clean(raw[:-1])==clean(x['uci_info']);replay.append({'prior':x,'raw':raw})
except BaseException as ex:error=type(ex).__name__+':'+str(ex)
finally:
 if e:e.close()
(O/'acks.json').write_text(json.dumps(acks,indent=2));(O/'perft.json').write_text(json.dumps(perft));(O/'unit_replay.json').write_text(json.dumps(replay));out={'status':'PASS_ALIGNED_LEAF_NATIVE_CAPTURE_TABLES_RULES_AND_UNIT_PROTOCOL' if error is None else 'FAIL_PRESERVED','error':error,'actual_go':len(replay),'actual_perft':len(perft),'price_ACKs':len(acks),'seconds':time.monotonic()-start,'exit_code':e.p.poll() if e else None,'profiles':profiles,'scope':'ConfigalignsactualEvalPieceValue,PieceValue,CapturePieceValue; noNNUE/othersearchthresholdretuning.96sameformalfrontiers/32unitcoldqueries rawexcepttime,nps exact. Notlearningresult oruniversalinvarianceproof.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
