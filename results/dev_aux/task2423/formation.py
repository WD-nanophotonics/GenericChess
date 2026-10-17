"""Verified winning-entry supply versus calls, from actual closed trajectories."""
from pathlib import Path
from collections import defaultdict,Counter
import json,time
OUT=Path('results/dev_aux/task2423')
def run():
 tick=time.perf_counter();panels=[];case=[]
 for task in(2401,2402,2413,2420):
  f=Path(f'results/dev_aux/task{task}');assert(f/'completion.json').exists();p=json.loads((f/'plan.json').read_text());games={g['slot']:g for g in map(json.loads,(f/'games.jsonl').read_text().splitlines())};decisions=list(map(json.loads,(f/'decisions.jsonl').read_text().splitlines()));by=defaultdict(list);groups={}
  for d in decisions:by[d['slot']].append(d)
  for slot,g in games.items():
   tag=(g['ratio'],g['hand_ratio'],p['opponents'][g['opponent']]['ratio']);q=groups.setdefault(tag,dict(games=0,requests=0,verified_candidate_entries=0,winning_conversions=0,unfinished_after_entry=0,ordinary_wins_no_candidate_entry=0,actual_outcomes=Counter(),normal_before_verified_entry=[]));own=[d for d in by[slot]if d['is_candidate']];entries=[d for d in own if d['source']in('VERIFIED_GRAPH_STRATEGY','VERIFIED_FULL_HISTORY_STRATEGY')];requests=[d for d in own if d['new_proof_attempt']];q['games']+=1;q['requests']+=len(requests);q['verified_candidate_entries']+=len(entries);q['winning_conversions']+=int(bool(entries)and g['outcome']=='W');q['unfinished_after_entry']+=int(bool(entries)and g['outcome']=='U');q['ordinary_wins_no_candidate_entry']+=int(not entries and g['outcome']=='W');q['actual_outcomes'][g['outcome']]+=1
   if entries:
    entry=entries[0];q['normal_before_verified_entry'].append(sum(d['source']=='FULL_SESSION_MATERIAL_SEARCH'for d in own if d['ply']<entry['ply']));assert g['outcome']in('W','U')
   if task==2402 and slot in(24,25):case.append(dict(slot=slot,price=[g['ratio'],g['hand_ratio']],outcome=g['outcome'],candidate_verified_entries=len(entries),candidate_requested_proofs=[dict(ply=d['ply'],root_record=d['root_record'],reason=d['proof_reason'],positions=d['graph_positions'])for d in requests],candidate_normal_decisions=sum(d['source']=='FULL_SESSION_MATERIAL_SEARCH'for d in own),candidate_depths=Counter(d['normal_receipt']['completed_depth']for d in own if d['normal_receipt']is not None)))
  panels.append(dict(task=task,rows=[dict(price=[tag[0],tag[1]],foe_R=tag[2],**{k:dict(v)if isinstance(v,Counter)else v for k,v in q.items()})for tag,q in sorted(groups.items())]))
 assert len(case)==2;assert case[0]['candidate_requested_proofs'][0]['root_record']==case[1]['candidate_requested_proofs'][0]['root_record'];assert all(c['candidate_verified_entries']==0 for c in case)
 result=dict(status='PASS_ACTUAL_VERIFIED_WIN_ENTRY_ACCOUNTING',panels=panels,reserve_first_matched_D3_divergence_case=case,case_inference='Bothprices requestsamefirstLOWroot atply1 andtime-out; firstactualchoice divergenceply11/latergain hasNOcandidateverifiedproofentry, selectedwinsbyordinaryactualmate. Cannotclaimthisgaincomesfrommoreprovenfavorablepositions/certifiedconversion. OFF2x2separatelymeasurescomponent; thisispost-fittraceassociationnotcausalmediation.',seconds=time.perf_counter()-tick,scope='Requestsnotwins, candidateandfoeseparated, onlyindependentlyverifiedactualwinningentrycounts. Conditionalconversionsnotindependentgamecounts/populationrate. Fixedpolicyprice/typedfeatures, no newgame/search/refit/capchange. Actualwinnerwithoutcertificate remainsactualwin, nottheoreticalproof.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('panels','reserve_first_matched_D3_divergence_case')}));print(json.dumps(panels))
if __name__=='__main__':run()
