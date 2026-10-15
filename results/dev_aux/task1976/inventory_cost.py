"""Paid PN cost by literal inventory; actual paths already independently audited."""
from pathlib import Path
from collections import Counter,defaultdict
import json
OUT=Path('results/dev_aux/task1976')
def run():
    panels=[]
    for name in ('task1962','task1965/cohort0','task1965/cohort1','task1968','task1974'):
        folder=Path('results/dev_aux')/name;p=json.loads((folder/'run-plan.json').read_text(encoding='utf-8'));assert json.loads((folder/'completion.json').read_text(encoding='utf-8'))['status']=='COMPLETE'
        roots=json.loads(Path(p['roots']).read_text(encoding='utf-8'))['roots'];games=[json.loads(x) for x in (folder/'games.jsonl').read_text(encoding='utf-8').splitlines()];moves=[json.loads(x) for x in (folder/'moves.jsonl').read_text(encoding='utf-8').splitlines()];by_slot=defaultdict(list)
        for m in moves:by_slot[m['slot']].append(m)
        groups={};total=0.
        for game in games:
            raw=roots[game['family']]['root'];board=list(raw[:16]);side=raw[16]
            for m in by_slot[game['slot']]:
                assert m['side']==side
                r=sum(v.upper()=='R' for v in board);n=sum(v.upper()=='N' for v in board);key=f'R{r}_N{n}'
                if m['proof_nodes']:
                    g=groups.setdefault(key,dict(queries=0,proof_nodes=0,proof_seconds=0.,proof_adoptions=0));g['queries']+=1;g['proof_nodes']+=m['proof_nodes'];g['proof_seconds']+=m['proof_seconds'];g['proof_adoptions']+=m['source']=='PROOF';total+=m['proof_seconds']
                a=m['choice'];assert a['kind']=='board' and a['promotion_target_id'] is None
                start=a['from'][0]+4*a['from'][1];end=a['to'][0]+4*a['to'][1]
                assert board[start]!='.' and int(board[start].islower())==side
                board[end]=board[start];board[start]='.';side=1-side
        low=sum(groups.get(k,{}).get('proof_seconds',0.) for k in ('R0_N0','R0_N1'))
        panels.append(dict(folder=name,groups=groups,total_actual_PN_seconds=total,KK_or_KKN_actual_PN_seconds=low,fraction=low/total if total else 0))
    result=dict(status='PASS_PAID_INVENTORY_ACCOUNTING',panels=panels,scope='No newsearch/Native/proof or proof-filteradoption. Closed4x4KRNcapture-remove paths only; allactualmovelegality/publichistory already independentlyaudited. KK/KKNcategory isNOT automatically a certifiednoWINdomain under arbitrary rules/history. Historical62censusfilter has an EXACTdifferentfingerprint guard; currentrules requirefulltransition/terminal/historyequivalence qualification before anytransport. Costfraction isNOT a guaranteedcache-free speedup or WDLinvariance.')
    with (OUT/'result.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps(dict(status=result['status'],panels=[{k:x[k] for k in ('folder','total_actual_PN_seconds','KK_or_KKN_actual_PN_seconds','fraction')} for x in panels])))
if __name__=='__main__':run()
