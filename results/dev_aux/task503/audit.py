import json,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task503';rows=[]
for task,newdir,base in [(477,'yaneura29','yaneura26'),(482,'yaneura30','yaneura27'),(491,'yaneura31','yaneura27')]:
 folder=R/f'results/dev_aux/task{task}';d=json.loads((folder/'declaration.json').read_text(encoding='utf-8'));summary=json.loads((folder/'build_summary.json').read_text(encoding='utf-8'));S=R/'.local_agent'/newdir/'source';B=R/'.local_agent'/base/'source';verified=[]
 for f in d['source_files']:
  rel=f['path'];orig=(B/rel).read_bytes();assert hashlib.sha256(orig).hexdigest()==f['sha256'];actual=(S/rel).read_bytes()
  if rel!=d['changed_only']:assert actual==orig
  verified.append(rel)
 text=(S/d['changed_only']).read_text(encoding='utf-8');old=(B/d['changed_only']).read_text(encoding='utf-8')
 if task==477:
  for p in d['patches']:text=text.replace(p['patch'], '')
  # Logger inserted immediately before each original anchor; no predicate edits.
  assert text==old
 elif task==482:
  for p in reversed(d['patches']):text=text.replace(p['patch'],p['old'])
  assert text==old and d['guard_disabled_exact_original']
 else:
  for c in reversed(d['changes']):
   assert text.count(c['new'])==c.get('multiplicity',1);text=text.replace(c['new'],c['old'])
  assert text==old
 assert hashlib.sha256((S/d['changed_only']).read_bytes()).hexdigest()==d['patched_source_sha256'];cached=summary['reused_object_hashes'];assert len(cached)==38;originbuild=json.loads((R/'.local_agent'/base/'build.json').read_text(encoding='utf-8'));lookup={x.get('source'):x for x in originbuild['steps'] if x.get('source')}
 for x in cached:
  origin=Path(lookup[x['source']]['args'][-1]);new=R/'.local_agent'/newdir/'objects'/origin.name;assert hashlib.sha256(origin.read_bytes()).hexdigest()==x['object_sha256'] and new.read_bytes()==origin.read_bytes()
 rows.append(dict(task=task,source_files=len(verified),changed_only=d['changed_only'],base_search_sha256=hashlib.sha256((B/d['changed_only']).read_bytes()).hexdigest(),new_search_sha256=d['patched_source_sha256'],exact_patch_reversal=True,unchanged_source_objects=38,changed_unit_compiled=1,link_commands=1,executable_sha256=summary['executable_sha256'],scope='Exactsource/guard/log patch reversal andcachedobjectclosure pins, oneunit compiled+link; not reproduction onanothercompiler/machine or arbitraryoptions proof.'))
out=dict(status='PASS_SOURCE_OBJECT_CLOSURE',rows=rows,new_go=0,scope='477loggingoriginalsource retained,482disabledguard exactbase,491allsourcechanges reverseexactlytohand-base. Headers/other211-file closure unchanged;38reused objects exactprovenance. Actualbehaviour qualification separately478/492.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(out)
