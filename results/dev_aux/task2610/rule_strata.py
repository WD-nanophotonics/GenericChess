from pathlib import Path
from collections import Counter
import json
root=Path('results/dev_aux')
def read(d):
    plan=json.loads((d/'eval-plan.json').read_text())
    games=[json.loads(x) for x in (d/'eval-games.jsonl').read_text().splitlines()]
    out={}
    for g in games:
        r,s,f,c,e,_=g['slot']
        out[(r,s,f,c,e)]=g['reward']
    return plan,out
data=[('task2609',*read(root/'task2609')),('task2610',*read(root/'task2610/attempt-2'))]
items=[]
for label,plan,out in data:
    for rule in plan['rules']:
        wdl={}
        for endpoint in ('initial','TD95','LocalLambda'):
            c=Counter(out[k] for k in out if k[0]==rule and k[4]==endpoint)
            wdl[endpoint]={('UNKNOWN' if x is None else {-1:'LOSS',0:'DRAW',1:'WIN'}[x]):n for x,n in c.items()}
        diffs=[]; unknown=0
        for (r,s,f,c,e),a in out.items():
            if r!=rule or e!='LocalLambda': continue
            b=out[(r,s,f,c,'TD95')]
            if a is None or b is None:
                diffs.append((-2,2)); unknown+=1
            else: diffs.append((a-b,a-b))
        items.append({'panel':label,'rule':rule,'wdl':wdl,'ll_minus_td95':{
            'pairs':len(diffs),'unknown_pairs':unknown,
            'mean_bound':[sum(x for x,_ in diffs)/len(diffs),sum(y for _,y in diffs)/len(diffs)]}})
p=root/'task2610/rule-strata.json'
p.write_text(json.dumps(items,indent=2)+'\n',encoding='utf-8')
report=root/'task2610/REPORT.md'
text=report.read_text(encoding='utf-8')
marker='## Scope and preserved limitations'
lines=['## Per-rule outcome and UNKNOWN profile','',
       'These exact rule strata are descriptive: each panel contributes 128 paired root/seed/color slots per rule, and are not independent rule samples. The high UNKNOWN concentration is visible in rule271003 and explains much of the width there.','',
       '| Panel | Rule | Initial W/D/L/U | TD95 W/D/L/U | LocalLambda W/D/L/U | LL − TD95 bound |',
       '|---|---:|---:|---:|---:|---:|']
for x in items:
    def fmt(endpoint):
        w=x['wdl'][endpoint]
        return '/'.join(str(w.get(k,0)) for k in ('WIN','DRAW','LOSS','UNKNOWN'))
    b=x['ll_minus_td95']['mean_bound']
    lines.append(f"| {x['panel']} | {x['rule']} | {fmt('initial')} | {fmt('TD95')} | {fmt('LocalLambda')} | [{b[0]:+.3f}, {b[1]:+.3f}] (U {x['ll_minus_td95']['unknown_pairs']}) |")
assert marker in text
text=text.replace(marker,'\n'.join(lines)+'\n\n'+marker)
report.write_text(text,encoding='utf-8')
print(json.dumps(items,indent=2))
