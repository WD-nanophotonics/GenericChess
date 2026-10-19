"""Dot 1792407xxx-thread advice (103a): per rule/foe absolute W/D/L/U of C0, W0, C100 and DIRECTLY paired
W0 - C100 full bounds, both NEW-rule panels. Existing records only; U kept as [-1,1]."""
from pathlib import Path
import json,itertools,collections
from results.dev_aux.task2586.analyze import contrast
PANELS={'task2587':dict(C0='Cold@0',W0='Warm@0',C100='Cold@100k'),'task2586':dict(C0='initial',W0='OldRulesMean',C100='Fixed@100k')}
def run():
 out=[]
 for task,lab in PANELS.items():
  E=Path(f'results/dev_aux/{task}/eval');ep=json.loads((E/'eval-plan.json').read_text());rows={tuple(g['slot']):g for g in map(json.loads,(E/'eval-games.jsonl').open())}
  for gs,o in itertools.product(ep['rules'],ep['foes']):
   S=[s for s in ep['slots']if s[0]==gs and s[5]==o];absw={}
   for k,m in lab.items():
    c=collections.Counter()
    for s in S:
     if s[4]==m:g=rows[tuple(s)];c['U'if g['reward']is None else'W'if g['reward']>0 else'L'if g['reward']<0 else'D']+=1
    absw[k]=dict(c)
   out.append(dict(panel=task,rule=gs,foe=o,absolute=absw,W0_minus_C100=contrast(rows,S,lab['W0'],lab['C100'])['bounds']))
 neg=sum(r['W0_minus_C100'][1]<0 for r in out);pos=sum(r['W0_minus_C100'][0]>0 for r in out)
 res=dict(status='EXISTING_RECORDS_ONLY',rows=out,cells=len(out),W0_minus_C100_strictly_negative=neg,strictly_positive=pos,undetermined=len(out)-neg-pos,practical_question='Is zero-training OldRulesMean worth using instead of trained cold@100k?')
 Path('results/dev_aux/task2587/direct-w0-c100.json').write_text(json.dumps(res,indent=2))
 for r in out:print(r['panel'],r['rule'],r['foe'][:7],'C0',r['absolute']['C0'],'W0',r['absolute']['W0'],'C100',r['absolute']['C100'],'W0-C100',[round(x,3)for x in r['W0_minus_C100']])
 print('neg',neg,'pos',pos,'undetermined',len(out)-neg-pos,'of',len(out))
if __name__=='__main__':run()
