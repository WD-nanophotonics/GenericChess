import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,importlib.util,random,time,re,statistics
R=Path.cwd();O=R/'results/dev_aux/task1716';rng=random.Random(2026699600);cases=[]
for width,task in [(4,1678),(8,1703)]:
 rows=[json.loads(l) for l in (R/f'results/dev_aux/task{task}/choices.jsonl').open()]
 for x in rng.sample(rows,16):cases.append({'width':width,'source_task':task,'choice':x})
(O/'frozen_cases.json').write_text(json.dumps({'status':'FROZEN_QUERY_PAIRS_BEFORE_QUERY','cases':cases,'seconds_cap':180,'max_actual_go':64,'source_evidence':'uci.cpp383ucinewgameSearchclear andleafcommand417Searchclear; search.cpp164clear doesnotreadEvalPieceValue. Reducedpath retainsONEcoldclear perquery, pricechangeusesleafcommand, samepriceusesucinewgame.','interpretation':'Pairedcounterbalancedprotocolmicrocontrol, nolearning/strength/equaltimegenericsearchclaim; actualrawexcepttime,nps mustmatch botharmsandoldsource.'},indent=2))
(O/'variant.ini').write_text((R/'results/dev_aux/task1675/variant.ini').read_text()+'\n'+(R/'results/dev_aux/task1688/variant.ini').read_text(),encoding='ascii')
sp=importlib.util.spec_from_file_location('P',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P);start=time.monotonic();deadline=start+180;e=None;error=None;records=[];current=None;currentwidth=None
clean=lambda raw:[re.sub(r'\b(?:time|nps) \d+','TIME_OR_NPS',x) for x in raw]
try:
 e=P.M.start(R/'.local_agent/leaf-rnbp-46/fairy-leaf-rnb.exe',3,deadline,P.stop)
 for n,v in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(O/'variant.ini'))]:e.send(f'setoption name {n} value {v}');e.ready()
 for i,case in enumerate(cases):
  x=case['choice'];width=case['width'];p=tuple(x['price'])
  if width!=currentwidth:e.send('setoption name UCI_Variant value '+('aux_pawn' if width==4 else 'aux_pawn8'));e.ready();current=None;currentwidth=width
  for arm in (['ORIGINAL','ONE_CLEAR'] if i%2==0 else ['ONE_CLEAR','ORIGINAL']):
   P.stop();assert time.monotonic()<deadline;t=time.monotonic();clear_count=0
   if arm=='ORIGINAL' or p!=current:
    e.send('devauxleafrnbp '+' '.join(map(str,p)));ack=e.ready();assert 'info string DEV_AUX leafRNBP '+' '.join(map(str,p))+' nativeP 720 nativeR 720 nativeN 720 nativeB 720 captureP 720 captureR 720 captureN 720 captureB 720' in ack;current=p;clear_count+=1
   if arm=='ORIGINAL' or clear_count==0:e.send('ucinewgame');e.ready();clear_count+=1
   e.send('position fen '+x['fen']);e.send(x['command']);raw=e.until(lambda z:z.startswith('bestmove '));e.ready();elapsed=time.monotonic()-t;assert raw[-1].split()[1]==x['move'] and clean(raw[:-1])==clean(x['uci_info']);records.append({'case':i,'width':width,'arm':arm,'price':p,'state':x['state'],'command':x['command'],'actual_clear_commands':clear_count,'seconds':elapsed,'raw':raw})
except BaseException as ex:error=type(ex).__name__+':'+str(ex)
finally:
 if e:e.close()
(O/'records.json').write_text(json.dumps(records));paired=[]
for i in range(32):
 pp={x['arm']:x for x in records if x['case']==i}
 if len(pp)==2:paired.append({'case':i,'old':pp['ORIGINAL']['seconds'],'one':pp['ONE_CLEAR']['seconds'],'ratio':pp['ONE_CLEAR']['seconds']/pp['ORIGINAL']['seconds']})
out={'status':'PASS_ALL32_COUNTERBALANCED_QUERYPAIRS_OLD_EQUALS_ONECLEAR_EQUALS_SAVED_SOURCE' if error is None else 'PARTIAL_PRESERVED','error':error,'actual_go':len(records),'actual_clear_commands':{a:sum(x['actual_clear_commands'] for x in records if x['arm']==a) for a in ['ORIGINAL','ONE_CLEAR']},'seconds':time.monotonic()-start,'paired':paired,'paired_ratio_median':statistics.median(x['ratio'] for x in paired) if paired else None,'exit_code':e.p.poll() if e else None,'scope':'Exactgo/info/moveexcepttime,nps on32frozenmixed4/8queries64/4096.2to1Searchclearperquery removesobservedredundantreset; tinysharedmachineelapsedratiosdescriptive, noendtoendtraininggainmeasured/futureallinputguarantee. Noexistingfrozenproducerchanged.'};(O/'result.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='paired'})
