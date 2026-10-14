from pathlib import Path
import json,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1451'
selection=json.loads((R/'results/dev_aux/task1444/selection.json').read_bytes());primary=selection['primary'];assert primary==[3407,720]
rows=[]
for label,file,nodes,cap in [('low','dev_manifest.json',512,180),('high','dev_high_manifest.json',4096,400)]:
 p=R/'results/dev_aux/task1444'/file;d=json.loads(p.read_bytes())
 assert d['root_range']==[32,96] and d['root_count']==64 and d['expected_games']==768 and d['nodes']==nodes and d['max_seconds']==cap
 assert {(x['leafR'],x['leafB']) for x in d['profiles'].values()}=={(720,720),(1728,720),(3407,720)}
 d['scope']='Frozen64 DEV, TRAIN32 mixedglobal(3407,720), uniform720/720 and fixedprior1728/720; primary selectedvsuniform at512, higher4096 bridge secondary; noDEVpricefit. Manifest canonicalactualinputs/resourceauthority.'
 (O/(label+'_manifest.json')).write_text(json.dumps(d,indent=2));rows.append(dict(label=label,old_manifest_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),actual_changes='scope textonly beforeexecution; allprofiles/input/budget fixedunchanged'))
out=dict(status='PREEXECUTION_LOW_HIGH_DEV_METADATA_CORRECTION',rows=rows,selection_note='task1444 sourcecopied textual16TRAIN/16DEV/old1440labels stale; actuallen32,means/32,bootstrap32,rootrange32:96andprofiles720/1728/3407 verified. Preserveexecutedselectsource/JSON; normalizedmetadatahere, no alteredprice/dataorclock. Futuregenerator/selectioncopiedmetadataneedparameterize, not furthercopy staleestimates.')
(O/'normalization.json').write_text(json.dumps(out,indent=2));print('CANONICAL_DEV64_LOW_HIGH_FROZEN')
