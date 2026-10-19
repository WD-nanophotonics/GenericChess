from pathlib import Path
import json
root=Path('results/dev_aux')
def load(p):
    plan=json.loads((p/'eval-plan.json').read_text())
    games=[json.loads(x) for x in (p/'eval-games.jsonl').read_text().splitlines()]
    out={}
    for g in games:
        r,s,f,c,e,_=g['slot']
        out[(r,s,f,c,e)]=g['reward']
    return plan,out
panels=[('task2609',*load(root/'task2609')),('task2610',*load(root/'task2610/attempt-2'))]
def bound(out,seed,left,right):
    ds=[]; unknown=0
    for (r,s,f,c,e),a in out.items():
        if s!=seed or e!=left: continue
        b=out[(r,s,f,c,right)]
        if a is None or b is None:
            ds.append((-2,2)); unknown+=1
        else: ds.append((a-b,a-b))
    n=len(ds)
    return {'pairs':n,'unknown_pairs':unknown,'mean_bound':[sum(x for x,_ in ds)/n,sum(y for _,y in ds)/n]}
table=[]
for name,plan,out in panels:
    for seed in plan['seeds']:
        table.append({'panel':name,'seed':seed,
          'TD95-initial':bound(out,seed,'TD95','initial'),
          'LocalLambda-initial':bound(out,seed,'LocalLambda','initial'),
          'LocalLambda-TD95':bound(out,seed,'LocalLambda','TD95')})
p=root/'task2610/seed-strata.json'
p.write_text(json.dumps(table,indent=2)+'\n',encoding='utf-8')
lines=['','## Seed-stratified descriptive bounds','',
       'Each seed contributes 128 paired root/color strata. The bounds below remain deterministic finite-panel UNKNOWN bounds; these four model seeds were crossed over all roots and are not independent replicates.','',
       '| Panel | Seed | TD95 − init | LocalLambda − init | LocalLambda − TD95 |',
       '|---|---:|---:|---:|---:|']
for row in table:
    def f(key):
        x=row[key]
        return f"[{x['mean_bound'][0]:+.3f}, {x['mean_bound'][1]:+.3f}] (U {x['unknown_pairs']})"
    lines.append(f"| {row['panel']} | {row['seed']} | {f('TD95-initial')} | {f('LocalLambda-initial')} | {f('LocalLambda-TD95')} |")
report=root/'task2610/REPORT.md'
text=report.read_text(encoding='utf-8')
marker='## Scope and preserved limitations'
assert marker in text
text=text.replace(marker,'\n'.join(lines)+'\n\n'+marker)
report.write_text(text,encoding='utf-8')
print(json.dumps(table,indent=2))
