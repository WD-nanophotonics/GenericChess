"""Paid-work attribution only, no policy/WDL counterfactual or new search."""
from pathlib import Path
from collections import Counter
import json
OUT=Path('results/dev_aux/task1972')
def run():
    folders=['task1962','task1965/cohort0','task1965/cohort1','task1968','task1974'];result=[]
    for name in folders:
        folder=Path('results/dev_aux')/name
        assert json.loads((folder/'completion.json').read_text(encoding='utf-8'))['status']=='COMPLETE'
        games=[json.loads(s) for s in (folder/'games.jsonl').read_text(encoding='utf-8').splitlines()]
        moves=[json.loads(s) for s in (folder/'moves.jsonl').read_text(encoding='utf-8').splitlines()]
        cached=[m for m in moves if 'bank_hit' in m]
        totals={field:sum(m.get(field,0) for m in moves) for field in ('seconds','commit_seconds','admission_seconds','proof_seconds','verification_seconds','normal_seconds','fill_verification_seconds','bank_overhead_seconds')}
        assert not any(m['bank_hit'] for m in cached)
        phaseover={phase:sum(m[phase]>m['phase_limits'][limit] for m in moves) for phase,limit in [('proof_seconds','proof_seconds'),('verification_seconds','verification_seconds'),('normal_seconds','normal_seconds')]}
        result.append(dict(folder=name,games=len(games),moves=len(moves),actual_game_seconds=sum(x['seconds'] for x in games),totals=totals,cached_queries=len(cached),bank_hits=0,bank_stored=sum(m['bank_stored'] for m in cached),outer_elapsed_ge_requested=sum(m['seconds']>=m['phase_limits']['total_seconds'] for m in moves),max_outer_seconds=max(m['seconds'] for m in moves),phase_atomic_overruns=phaseover,Native_node_overruns=sum(m['search_nodes']>m['budget'] for m in moves),proof_reasons=dict(Counter(m['proof_reason'] for m in moves)),exit_causes=dict(Counter(m['exit_cause'] for m in moves))))
    out=dict(status='PASS_ACCOUNTING_ONLY',panels=result,source_contract='ProofMaterialPlayer explicitly retains last completed legal NORMAL action on atomic time overrun; PhasePlayer inherits that contract. Requested caps are not proof of hard atomic latency or exact Native visit counts. No new strictdeadline policy, altered currentdata or retroactivefairness claim. Current records above quantify actualoverruns.',cold_key_reason='Each physicalboardchoice increases fullGameRecord actions; each game has a new EMPTY bank. Samefullrecordkey isneverqueriedtwice, confirmedzeroactualhits. Bankadmission/fillchecks are paid. CacheOFFcouldremove overhead but is a DIFFERENT finite-timepolicy and requires a newprotocol, not a freecounterfactual speedup.',units='PNvisits/verifiervisits/NativeUCIreportednodes remain separate; no pooling withPRIMARY main+q counters.',scope='Already-paid actualrecords only, notuniform cost per game, predictedcache-free WDL, independenttimingreplication or universaloptimalbudget.')
    with (OUT/'result.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2)
    print(json.dumps(dict(status='PASS_ACCOUNTING_ONLY',panels=[{k:x[k] for k in ('folder','games','moves','actual_game_seconds','outer_elapsed_ge_requested','max_outer_seconds','bank_hits','Native_node_overruns')} for x in result])))
if __name__=='__main__':run()
