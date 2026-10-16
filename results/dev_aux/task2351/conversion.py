"""Closed transfer: actual terminal types, proof calls, accepted-and-converted entries."""
from pathlib import Path
from collections import defaultdict,Counter
import json,time
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2351')
def run():
 t=time.perf_counter();stop=EvidenceStopReader(Path.cwd());read=lambda p:json.loads(Path(p).read_text());assert read('results/dev_aux/task2332/task2331-audit.json')['status']=='PASS_FULL_ACTUAL_RECORDS_PHASES_CERTIFICATES_SINGLEAXIS_CONTRACT';games=list(map(json.loads,Path('results/dev_aux/task2331/games.jsonl').read_text().splitlines()));decisions=defaultdict(list)
 for d in map(json.loads,Path('results/dev_aux/task2331/decisions.jsonl').read_text().splitlines()):decisions[d['slot']].append(d)
 prices={};entries=[];pairs=defaultdict(dict)
 for price in(1.,2.):
  stop();selected=[g for g in games if g['ratio']==price];attempts=[];admitted=[];unique=set();terminal=Counter();normalwins=0
  for g in selected:
   terminal[g['actual_status']]+=1;own=[d for d in decisions[g['slot']]if d['is_candidate']];attempts.extend(d for d in own if d['new_proof_attempt']);proof=[d for d in own if d['source']in('VERIFIED_GRAPH_STRATEGY','VERIFIED_FULL_HISTORY_STRATEGY')];assert not proof or g['outcome']=='W';normalwins+=g['outcome']=='W'and not proof;pairs[(g['root'],g['opponent'],g['candidate_color'])][price]=dict(game=g,candidate_proof=bool(proof))
   for d in proof:
    before=sum(x['source']=='FULL_SESSION_MATERIAL_SEARCH'for x in own if x['ply']<d['ply']);token=(d['root_state_sha'],json.dumps(d['root_record'],sort_keys=True));unique.add(token);admitted.append(d);entries.append(dict(price=price,slot=g['slot'],family=g['root'],opponent=g['opponent'],color=g['candidate_color'],proof_ply=d['ply'],own_material_decisions_before=before,actual_outcome=g['outcome']))
  prices[str(price)]=dict(actual_games=len(selected),terminal_statuses=dict(terminal),candidate_new_proof_attempts=len(attempts),candidate_proof_admissions=len(admitted),unique_fullhistory_admissions=len(unique),admitted_and_actual_won=len(admitted),actual_wins_without_candidate_proof=normalwins,actual_wins=sum(g['outcome']=='W'for g in selected),actual_losses=sum(g['outcome']=='L'for g in selected),draws=sum(g['outcome']=='D'for g in selected))
 gains=[]
 for key,pair in pairs.items():
  a,b=pair[1.],pair[2.];delta=b['game']['reward']-a['game']['reward']
  if delta>0:gains.append(dict(family=key[0],opponent=key[1],color=key[2],delta=delta,outcomes=[a['game']['outcome'],b['game']['outcome']],candidate_proof=[a['candidate_proof'],b['candidate_proof']]))
 result=dict(status='PASS_ACTUAL_TERMINALS_AND_PROVEN_CONVERSION_ACCOUNTING',prices=prices,entries=entries,positive_pairs=gains,all_admissions_after_material=all(e['own_material_decisions_before']>0 for e in entries),positive_pairs_with_extra_candidate_proof=sum(not g['candidate_proof'][0]and g['candidate_proof'][1]for g in gains),seconds=time.perf_counter()-t,scope='ALLclosed128actualfiniteSessiongames andindependentlycheckedpositivecertificates. Callsnotproofs; acceptedANDactualconvertedseparate, uniquefullhistoryentriesnotindependentfamilies. Moreadmittedproofs doesNOTestablishmoreunderlyingWINstates becauseunprovedentriesUNKNOWN. Timeorder/associationnotcausalmediation. MAX_PLYisdeclaredexperimentalruleterminalDRAW, notinfiniteChess/ShogiWDL orongoinghorizonimputation; unfinishedwouldstayU. Samefixedasymmetriccandidate/foeproofconfigurationacrossprices, notequalcomputealgorithmcomparison.')
 with(OUT/'result.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k not in('entries','positive_pairs')}))
if __name__=='__main__':run()
