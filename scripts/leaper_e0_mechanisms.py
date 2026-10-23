"""Explain frozen E0 false predictions using retained complete policy records.

No new queries, root screening, exact-WDL calls or adaptive probability fitting.
"""
import argparse,json
from collections import Counter
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_e0 import full_rule_code


def first_difference(a,b):
    for x,y in zip(a['queries'],b['queries']):
        assert x['state_sha256']==y['state_sha256']
        if x['action']!=y['action']:return {'ply':x['root_ply'],'actor':x['actor'],'state_sha256':x['state_sha256'],'completed_depths':[x.get('decision',{}).get('completed_depth'),y.get('decision',{}).get('completed_depth')],'actions':[x['action'],y['action']]}
    return None


def analyze(d):
    a=L.load(d/'e0-analysis.json');r=L.load(d/'results.json');assert r['status']=='CLOSED';ws=L.load(d/'inputs.json')['worlds'];ss={(s['world'],s['role'],s['pair'].split('_vs_')[0]):s for s in r['slots']};rows=[];counts=Counter()
    for pred in a['world_predictions']:
        world=pred['world'];w=ws[world]
        for z in [z for z in a['role_interactions'] if z['world']==world]:
            role=z['role'];gg={p:L.load(d/ss[world,role,p]['receipt']) for p in ('S3','S4','U3','U4')};first={p:next((q for q in g['queries'] if q['actor']==role),None) for p,g in gg.items()};present=[q for q in first.values() if q]
            if present:assert len(present)==4 and len({q['state_sha256'] for q in present})==1
            acts={p:None if q is None else q['action'] for p,q in first.items()};same=all(v==acts['S3'] for v in acts.values());nonzero=z['complete'] and z['interaction']!=[0,0]
            counts[('same_all4_first' if same else 'different_first')+('_nonzeroI' if nonzero else '_zero_or_UNKNOWNI')]+=1
            differences={name:first_difference(gg[x],gg[y]) for name,x,y in [('priceD3','S3','U3'),('priceD4','S4','U4'),('staticDepth','S3','S4'),('unitDepth','U3','U4')]}
            row={'world':world,'full_rule_code':list(full_rule_code(w)),'layout':w['placement_index'],'prefix':w['prefix_index'],'role':role,'original_prediction_classification':pred['classification'],'interaction':z['interaction'],'cells':z['cells'],'same_all_four_first_candidate_actions':same,'first_candidate_actions':acts,'first_candidate_state_sha256':present[0]['state_sha256'] if present else None,'first_divergences':differences,'game_sha256':{p:L.sha(d/ss[world,role,p]['receipt']) for p in gg}};rows.append(row)
    out={'status':'PASS','counts':dict(counts),'rows':rows,'FN_examples':[x for x in rows if x['original_prediction_classification']=='FN' and x['interaction']!=[0,0]],'FP_examples':[x for x in rows if x['original_prediction_classification']=='FP'],'new_Player_calls':0,'scope':'Posthoc explanation of finite policy predictions. Firstcandidate actions compared at SAMEactual candidate history, includingfixedreferencefirstmove; original E0 feature saw onlyworldinitialside. This doesnotrefit the ongoing E1 model or establish minimax/structuraltruth. Matching first action is not wholepolicy equality.'};L.write_record(d/'e0-mechanisms.json',out);print({'counts':out['counts'],'FN':[{k:x[k] for k in ('world','full_rule_code','layout','prefix','role','interaction','same_all_four_first_candidate_actions','cells')} for x in out['FN_examples']]},flush=True)


def main():
 p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();analyze(a.output)
if __name__=='__main__':main()
