import json,time,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task291';O.mkdir(exist_ok=False);T=json.loads((R/'results/dev_aux/task258/tree.json').read_bytes());D=json.loads((R/'results/dev_aux/task258/declaration.json').read_bytes());t=next(z for z in T['roots'] if z['root']=='capture-3');print('treekeys',list(t));print('declkeys',list(D));selected=[]
for a in t['actions']:
 for br in a['branches']:
  for ch in br.get('children',[]):
   if len(ch['move'])==5 and 'terminal' not in ch['leaf']:
    selected.append(dict(first=a['move'],reply=br['move'],third=ch['move'],leaf=ch['leaf']))
    if len(selected)==3:break
  if len(selected)==3:break
 if len(selected)==3:break
out=dict(task_id='291',complete=True,selection='First3 nonterminalactualBlackthirdpromotions lexicalstored258traversal; full originalsource preserved, no humanlabel/goal/outcome basedselection',source_sha256=hashlib.sha256((R/'results/dev_aux/task258/tree.json').read_bytes()).hexdigest(),root=next(f for f in D['roots'] if f['id']=='capture-3'),selected=selected,next='Freeze eachbranchparent beforepromotion, all4promotionoptions andoriginal5priceprofiles; inspectnextmate/defense atboundedsamefullhistory. No longgames.')
(O/'declaration.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))