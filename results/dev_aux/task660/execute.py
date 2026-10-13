import json,time,sys,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task660';d=json.loads((O/'declaration.json').read_bytes());start=time.monotonic()
for n in [360,364,381,509]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
from warm_adapter import ControlledEngine
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';rows=[];acks=[];qgo=0;root=d['test_root'];b=A.shogi.Board(root);f=dict(index=0,seed=2026105902,phase='artificial_boundary',initial_sfen=root,history=[],expected_sfen=root);bb,k,ch,mo=G.full_root(f);assert G.terminal(bb,k,ch,mo) is None and not bb.is_check();assert len(list(bb.legal_moves))>0
with (O/'queries.jsonl').open('w') as qj:
 for maximum in [90,1000,4096]:
  w=[0]+[maximum]*14+[0];w[1]=90;w[8]=0;e=ControlledEngine(w,qj,'warm_game');acks.append(dict(weights=w,prices=e.prices));rec=dict(weights=w,maximum=maximum,initial_sfen=root,legal_actions=len(list(bb.legal_moves)),in_check=False,terminal=None,python_material=A.material(bb,w),nonterminal_material_above_VALUE_MATE=abs(A.material(bb,w))>=32000)
  try:
   e.begin_game();rec['auxstate']=e.state(root,[]);q=e.search(root,[],64);qgo+=1;rec['actual_query']=q
   try:rec['legal_PV_moves']=V.query(q);rec['query_legality_pass']=True
   except Exception as ex:rec['PV_or_query_failure']=str(ex)
  except Exception as ex:rec['actual_failure']=str(ex);rec['transcript']=e.transcript
  finally:
   try:e.close()
   except Exception as ex:rec['close_failure']=str(ex)
  rows.append(rec);(O/'progress.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print('material_boundary',maximum,rec['python_material'],rec.get('auxstate'),rec.get('actual_failure'),flush=True)
out=dict(status='ACTUAL_MATERIAL_ENCODING_BOUNDARY_PROBED',actual_go=qgo,rows=rows,price_acks=acks,seconds=time.monotonic()-start,executable_sha256=hashlib.sha256(A.EXE.read_bytes()).hexdigest(),scope='Threeactualshortnode64go onfreshinventoryvalidnonterminaluncheckedroyalSFEN; fullsource/priceACK/readback andPV recorded. Artificialrootnotstandardopeningreachabilityproof. Atfull4096pricebox rawmaterial canexceedmate/infinite domain; actualprior136candidate conservativeenvelopes<=12152 exclude this explanationforcurrentfits. No price/rootusedasfitness ornewtraining/productdefaultchange.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('BOUNDARY_COMPLETE',qgo,round(time.monotonic()-start,3))
