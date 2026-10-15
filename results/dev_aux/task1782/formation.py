"""Unconditional proof-entry and physical-win formation accounting."""
import json,collections,sys
from pathlib import Path


def analyze(task):
    p=Path(f'results/dev_aux/task{task}');plan=json.loads((p/'plan.json').read_text());sel=json.loads((p/'selection.json').read_text());rows=[json.loads(x) for x in (p/'run/games.jsonl').read_text().splitlines()];out=[]
    for index in sorted({plan['baseline_index'],sel['selected_index']}):
        data=[r for r in rows if r['phase']=='DEV' and r['proof'] and r['price_index']==index];counts=collections.Counter();inventory=collections.Counter();ranks=collections.Counter()
        for r in data:
            counts['games']+=1;counts['actual_win']+=r['payoff']==1;counts['actual_loss']+=r['payoff']==-1;counts['actual_draw']+=r['payoff']==0;counts['UNKNOWN']+=r['payoff'] is None
            entries=[s for s in r['trajectory'] if s['decision']['source']=='PROOF']
            counts['games_with_candidate_proof']+=any(s['actor'][-1]==r['color'] for s in entries)
            counts['games_with_opponent_proof']+=any(s['actor'][-1]!=r['color'] for s in entries)
            for s in entries:
                who='candidate' if s['actor'][-1]==r['color'] else 'opponent';board=s['actor'][:-1];owner=s['actor'][-1]
                inv=tuple(sum(x==piece if owner==0 else x==piece.lower() for x in board) for piece in ('R','N'))
                inventory[str((who,inv))]+=1
            tail=r.get('tail_admission')
            if tail:ranks[tail['rank']]+=1
        out.append(dict(price_index=index,price=plan['prices'][index],counts=dict(counts),proof_entry_own_R_N_inventory=dict(inventory),admitted_tail_remaining_rank=dict(ranks)))
    result=dict(task=task,cells=out,scope='All observed DEV games in each arm, never conditioned contrast on proof subset. Inventories are descriptive mechanism traces, not training rewards or causal price formulas. Missing slots, if any, remain in separate full-plan audit bounds.',actual_new_native_go=0)
    Path(f'results/dev_aux/task1782/formation_{task}.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))


if __name__=='__main__':
    for task in sys.argv[1:]:analyze(int(task))
