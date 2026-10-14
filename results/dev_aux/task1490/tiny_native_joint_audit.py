from pathlib import Path
import json,importlib.util,collections
R=Path.cwd();O=R/'results/dev_aux/task1527';O.mkdir(exist_ok=False);study=json.loads((R/'results/dev_aux/task1521/study.json').read_bytes());G=R/'results/dev_aux/task1495';states=list(map(tuple,json.loads((G/'states.json').read_bytes())));values=json.loads((G/'values.json').read_bytes())['value'];edges={x['id']:dict(x['moves']) for x in map(json.loads,(G/'edges.jsonl').read_text().splitlines())};sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1490/tiny_rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T);rows=[]
for tid,phase in [(1522,'TRAIN'),(1524,'DEV')]:
 P=R/f'results/dev_aux/task{tid}';result=json.loads((P/'result.json').read_bytes());assert result['status']=='COMPLETE' and result['all_owned_engines_closed'];families=[f for f in study['families'] if f['phase']==phase];ps=study['R_grid'] if phase=='TRAIN' else study['DEV_all_grid'];gs=[json.loads(x) for x in (P/'choices.jsonl').read_text().splitlines()];assert [(x['node_budget'],x['leafR'],x['family'],x['state_id']) for x in gs]==[(b,p,f['family'],i) for b in study['nodes'] for p in ps for f in families for i in f['state_ids']];count=collections.Counter()
 for x in gs:
  sid=x['state_id'];price=x['leafR'];assert x['leafN']==720 and x['nativeR']==price and x['position']=='position fen '+T.fen(states[sid]) and x['command']==f"go nodes {x['node_budget']}";j=edges[sid][x['move']];assert j==x['child_id'] and x['root_WDL']==values[sid] and x['chosen_WDL']==-values[j] and x['regret']==values[sid]+values[j];count['labels']+=1
  for line in x['uci_info']:
   fs=line.split()
   if 'tbhits' in fs:assert int(fs[fs.index('tbhits')+1])==0
   if 'pv' in fs:
    s=states[sid]
    for u in fs[fs.index('pv')+1:]:ll=dict(T.moves(s));assert u in ll;s=ll[u];count['literal_PVmoves']+=1
 acks=[a for block in result['acks'] for a in block if 'DEV_AUX alignment ' in a or 'DEV_AUX leafRNBP ' in a];assert len(acks)==24
 for ix,price in enumerate(ps*3):
  aline=acks[2*ix];fields=aline.split();assert fields[:5]==['info','string','DEV_AUX','alignment','3'];vv={int(f.split(':')[0]):list(map(int,f.split(':')[1:])) for f in fields[5:]};assert vv=={1:[720,720],2:[720,720],3:[720,720],4:[price,price],5:[1664,1664]}
  assert acks[2*ix+1]==f'info string DEV_AUX leafRNBP {price} 720 720 720 nativeP 720 nativeR {price} nativeN 720 nativeB 720 captureP 720 captureR {price} captureN 720 captureB 720'
 rows.append({'task':tid,'phase':phase,'counts':dict(count),'actual_atomic_and_native_alignment_acks':len(acks)})
(O/'result.json').write_text(json.dumps({'status':'PASS_ALL_NATIVE_JOINT_CHOICES_PV_TRUE_LABELS_AND_ALIGNMENT','rows':rows,'scope':study['scope'],'new_go':0},indent=2));print(rows)
