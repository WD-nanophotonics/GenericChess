"""Prospective H48 actual-outcome sensitivity; H24 remains closed unchanged."""
from pathlib import Path
from collections import Counter
import json,time
from results.dev_aux.task1956.physical_audit import audit
from results.dev_aux.task1953.audit import contrast
from results.dev_aux.task1931.audit import profile
from results.dev_aux.task1928.audit import lines,read
O=Path('results/dev_aux/task1956')
def run():
 beg=time.perf_counter();folder=Path('results/dev_aux/task1955');p=read(folder/'run-plan.json');completion=read(folder/'completion.json');rows=lines(folder/'games.jsonl');physical=audit(folder);full=completion['status']=='COMPLETE' and len(rows)==512;pr=profile(folder) if full else dict(status='PARTIAL_ISSUED_JOURNAL_PRESERVED',issued=completion['native_go'],committed=physical['actual_native']);old={mode:lines(f'results/dev_aux/task{task}/games.jsonl') for mode,task in [(False,1943),(True,1944)]};oldidx={(g['opponent_nodes'],g['family'],g['candidate_side'],g['ratio'],mode):g for mode,gs in old.items() for g in gs};ix={(g['opponent_nodes'],g['family'],g['candidate_side'],g['ratio'],g['candidate_proof']):g for g in rows};assert len(ix)==len(rows)
 prefixes=Counter();prefix_mismatches=[];trans=Counter()
 for key,g in ix.items():
  prior=oldidx[key];n=min(24,len(prior['record']['actions']));same=prior['record']['actions'][:n]==g['record']['actions'][:n];prefixes['same_first_min24']+=same;prefixes['different_first_min24']+=not same;trans[prior['outcome']+'->'+g['outcome']]+=1
  if not same:prefix_mismatches.append(dict(slot=g['slot'],opponent_nodes=g['opponent_nodes'],family=g['family'],role=g['candidate_side'],ratio=g['ratio'],proof=g['candidate_proof']))
 panels=[]
 if full:
  for opp in (512,4096):
   cells=[]
   for mode in (False,True):
    for ratio in (1.,2.):
     gs=[ix[opp,f,s,ratio,mode] for f in range(32) for s in (0,1)];cells.append(dict(proof=mode,ratio=ratio,outcomes=dict(Counter(g['outcome'] for g in gs)),net=sum(g['finite_event_score'] for g in gs),sum_game_seconds=sum(g['seconds'] for g in gs)))
   terms={'price_OFF':[(False,2.,1),(False,1.,-1)],'price_ON':[(True,2.,1),(True,1.,-1)],'proof_at1':[(True,1.,1),(False,1.,-1)],'proof_at2':[(True,2.,1),(False,2.,-1)],'interaction':[(True,2.,1),(True,1.,-1),(False,2.,-1),(False,1.,1)]}
   panels.append(dict(opponent_nodes=opp,cells=cells,effects={name:contrast(ix,opp,t) for name,t in terms.items()}))
 out=dict(status='PASS_ALL_CLOSED_H48_PHYSICAL_RECORDS' if full else 'PARTIAL_H48_NO_FULL_EFFECT_CLAIM',physical=physical,profiles=pr,full_study_complete=full,completion=completion,panels=panels,actualH24_to_H48_transitions=dict(trans),first24prefix=dict(prefixes),prefix_mismatches=prefix_mismatches,seconds=time.perf_counter()-beg,scope='ALL32sameEXPOSEDfamilies/roles/prices1,2/2fixedopponents/proofOFF,16k, H48frozenafternewpositiveH24. No newpricechoice/freshvalidation. H24neverresumed/extended. H48alsoallowsproofuntil48, plusfreshcachetrajectory: comparepolicy/resource/horizon sensitivity, NOTpureobservation-onlycausalcontrast. Actualcommonprefixmismatches retained, notforcedequal. Everyphysicalruleterminalonly; UNKNOWNdistinct andpartial/missingnever treatedcomplete. Actualrulemaxply96 unchanged. No population/fullChess/humanvalueclaim.')
 (O/'horizon-result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(status=out['status'],complete=full,physical_games=physical['games'],prefixes=dict(prefixes),transitions=dict(trans),price_effects=[dict(opponent_nodes=x['opponent_nodes'],effects={k:{j:v[j] for j in ['mean','family95']} for k,v in x['effects'].items()}) for x in panels],seconds=out['seconds'])))
if __name__=='__main__':run()
