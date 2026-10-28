"""Attach independently generated one-step terminal facts to saved evidence."""
import json,argparse,copy
from pathlib import Path
from collections import Counter
from generic_chess.core.actions import action_to_dict
from scripts.verify_published_new_family_games import load,digest,diagnostic_action
from scripts.analyze_new_family_evidence import fold
from scripts.research_record import write_record

def augment(old,census,source):
 d=copy.deepcopy(old);games={g['game_id']:g for g in load(source/'results/games.json.gz')};added=0
 for key,row in census['contexts'].items():
  g=games[row['representative_game']];rec=copy.deepcopy(g['final_record']);rec['actions']=rec['actions'][:row['ply']]
  assert digest(json.dumps(rec,sort_keys=True,separators=(',',':')).encode())==key
  assert d['nodes'][key]['legal']==row['legal_count'] and d['nodes'][key]['actor']==row['actor']
  for fact in row['terminal_actions']:
   ch=copy.deepcopy(rec);ch['actions'].append(action_to_dict(diagnostic_action(fact['action'],g['fingerprint'])));child=digest(json.dumps(ch,sort_keys=True,separators=(',',':')).encode())
   n=dict(actor=1-row['actor'],legal=0,terminal=fact['terminal'],ply=row['ply']+1);assert d['nodes'].setdefault(child,n)==n
   d['edges'].append(dict(parent=key,action=json.dumps(fact['action'],sort_keys=True,separators=(',',':')),child=child));added+=1
 bounds,out=fold(d['nodes'],d['edges']);d['bounds']=bounds
 counts=Counter();newqs=[]
 for q in d['queries']:
  pb=bounds[q['parent']];cb=bounds[q['child']];actor=d['nodes'][q['parent']]['actor']
  rb=[max(0,pb[0]-cb[1]),pb[1]-cb[0]] if actor==0 else [max(0,cb[0]-pb[1]),cb[1]-pb[0]]
  if q['forced']:rb=[0,0]
  newqs.append(dict(q,parent_bounds=pb,child_bounds=cb,regret_bounds=rb));counts[str(rb)]+=1
 summary=dict(original_nodes=len(old['nodes']),augmented_nodes=len(d['nodes']),terminal_fact_occurrences=added,new_distinct_edges=sum(len(v) for v in out.values())-old['distinct_edges'],bounds_histogram=dict(Counter(str(x) for x in bounds.values())),tightened_old_nodes=sum(bounds[k]!=v for k,v in old['bounds'].items()),query_regret_bounds=dict(counts),strict_errors=[q for q in newqs if q['regret_bounds'][0]>0],zero_regret_exposures=sum(q['regret_bounds']==[0,0] for q in newqs))
 d.update(queries=newqs,augmentation=summary,scope='Original saved forest plus COMPLETE one-step terminal census on fixed NEWactualgame decisions. Missing ongoing alternatives stayUNKNOWN; no deeper graph expansion or Player/solver/game.')
 return d
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--derived',type=Path,required=True);p.add_argument('--census',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=augment(load(a.derived),load(a.census),a.source);write_record(a.output,r);print(json.dumps(r['augmentation'],indent=2))
