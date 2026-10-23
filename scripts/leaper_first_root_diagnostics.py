"""First-root agreement versus complete-game budget effect in CLOSED records.

This describes full fixed-budget policies. It does NOT test an adaptive per-turn
agreement gate, claim WDL, train a predictor, or create new Player queries.
"""
import argparse
from pathlib import Path
from collections import Counter,defaultdict
from scripts import leaper_design as L
from scripts.leaper_budget_calibration import interval_sub


def analyze(d):
    r=L.load(d/'results.json');assert r['status']=='CLOSED';ww=L.load(d/'inputs.json')['worlds'];ss={(s['world'],s['pair']):s for s in r['slots']};rows=[];counts=Counter();groups=defaultdict(Counter);witnesses=[]
    for w in ww:
        for role,pair in ((0,'HL'),(1,'LH')):
            low,high=ss[w['world'],'LL'],ss[w['world'],pair]
            if not low.get('receipt')or not high.get('receipt'):
                counts['missing_physical_record']+=1;continue
            a,b=L.load(d/low['receipt']),L.load(d/high['receipt']);assert a['initial_record']==b['initial_record']==w['initial_record']
            gain=interval_sub(high['utility'],low['utility'])if role==0 else interval_sub(low['utility'],high['utility']);known=gain[0]==gain[1]
            qa=next((q for q in a['queries']if q['actor']==role),None);qb=next((q for q in b['queries']if q['actor']==role),None)
            stable=None;first=None
            if qa and qb:
                assert qa['state_sha256']==qb['state_sha256'],'diagnose mismatched initial candidate control before interpreting'
                stable=qa['action']==qb['action']
            elif known:
                assert qa is None and qb is None and gain==[0,0],'unchanged pre-candidate reference must match'
                counts['no_candidate_query_zero_gain']+=1
            if known and gain[0]!=0:
                for x,y in zip(a['queries'],b['queries']):
                    assert x['state_sha256']==y['state_sha256']
                    if x['action']!=y['action']:
                        first={'ply':x['root_ply'],'actor':x['actor'],'state_sha256':x['state_sha256'],'actions':[x['action'],y['action']],'completed_depths':[x['decision']['completed_depth'],y['decision']['completed_depth']]};break
                assert first is not None and first['actor']==role,'first divergence must belong to budget-changed actor'
            row={'world':w['world'],'code':w['code_world'],'placement':w['placement_index'],'role':role,'same_first_candidate_action':stable,'gain':[str(x)for x in gain],'known':known,'first_divergence':first,'low_game_sha256':L.sha(d/low['receipt']),'high_game_sha256':L.sha(d/high['receipt'])};rows.append(row)
            if stable is not None and known:
                sign='negative'if gain[0]<0 else'positive'if gain[0]>0 else'zero';groups['same'if stable else'changed'][sign]+=1
                if stable and gain[0]!=0:witnesses.append(row)
    out={'status':'PASS','role_contrasts_derived_NOT_new_games':len(rows),'counts':dict(counts),'known_only_descriptive_groups':{k:dict(v)for k,v in groups.items()},'same_first_action_nonzero_full_game_effects':len(witnesses),'examples':witnesses[:8],'rows':rows,'new_Player_calls':0,'scope':'Actual source-bound complete-history controls. Same first chosen action does not identify the utility of an entire lower-budget policy. This is NOT a test/refutation of a per-turn adaptive agreement gate; TT histories and later actions may change. Shared LL records across roles are derived reuse, not independent executions.'}
    L.write_record(d/'first-root-agreement-versus-full-game.json',out);print({k:out[k]for k in ('role_contrasts_derived_NOT_new_games','counts','known_only_descriptive_groups','same_first_action_nonzero_full_game_effects')},flush=True)


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();analyze(a.output)
if __name__=='__main__':main()
