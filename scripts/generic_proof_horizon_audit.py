"""Audit-only H views of a single paid journal and paired horizon contrasts.

Views contain exact recorded rows/receipts, never new games or inferred wins.
The original all-case journal retains global caps and physical execution order.
"""
import collections,hashlib,json,random,statistics,contextlib,io
from pathlib import Path
from scripts.generic_proof_horizons import dev_cases
from scripts.generic_proof_roles import row_role
from scripts.generic_proof_study_audit import audit as replay,quantile
from scripts.generic_proof_tail_audit import audit as tail_audit
from scripts.generic_proof_role_report import report as role_report


def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def lines(p):return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines()]
def dump(p,d):p.write_text(json.dumps(d,indent=2),encoding='utf-8')
def key(r):return (r['family'],r['proof'],r['price_index'],r['color'],r['opponent'],row_role(r),r['H'])
def case_key(t):
    f,q,i,c,o,r,h=t;return f['family'],q,i,c,o['id'],r,h


def audit(folder):
    p=Path(folder);plan=read(p/'plan.json');rows=lines(p/'run/games.jsonl')
    expected=[case_key(t) for t in dev_cases(plan,1)]
    actual=[key(r) for r in rows]
    assert len(set(actual))==len(actual) and actual==expected[:len(actual)],'paid order/identity mismatch'
    choices=lines(p/'run/choices.jsonl');acks=lines(p/'run/acks.jsonl');journal=lines(p/'run/go_journal.jsonl')
    sent=[j for j in journal if j['event']=='SENT'];intent=[j for j in journal if j['event']=='INTENT']
    assert sent==[dict(j,event='SENT') for j in intent]
    assert len(sent)==len(choices)==len(acks)
    for a,b in zip(sent,choices):
        assert all(a[k]==b[k] for k in ('state','price','command'))
    index=0;by={h:dict(rows=[],choices=[],acks=[]) for h in plan['horizons']}
    for row in rows:
        n=sum(s['decision']['source']=='EXTERNAL_SEARCH' for s in row['trajectory'])
        b=by[row['H']];b['rows'].append(row);b['choices']+=choices[index:index+n];b['acks']+=acks[index:index+n];index+=n
    assert index==len(choices),'orphan Native receipt'
    audits={}
    for h,b in by.items():
        view=p/f'audit_H{h}';view.mkdir(exist_ok=False);(view/'run').mkdir()
        hp=dict(plan,H=h,horizons=[h]);dump(view/'plan.json',hp)
        for name,data in [('games',b['rows']),('choices',b['choices']),('acks',b['acks'])]:
            (view/'run'/f'{name}.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in data),encoding='utf-8')
        dump(view/'VIEW_ONLY.json',dict(source=(p/'run').as_posix(),horizon=h,source_games_sha256=hashlib.sha256((p/'run/games.jsonl').read_bytes()).hexdigest(),new_games=0))
        with contextlib.redirect_stdout(io.StringIO()):replay(view);tail_audit(view);role_report(view)
        audits[str(h)]=read(view/'audit.json')
    lookup={key(r):r for r in rows};families=[f['family'] for f in plan['families']];rng=random.Random(2026101557)
    contrasts=[];vectors={};transitions=[]
    for h in plan['horizons']:
        values=[];missing=[]
        for family in families:
            delta=[]
            for color in (0,1):
                for op in plan['opponents']:
                    for role in plan['candidate_roles']:
                        a=lookup.get((family,True,0,color,op['id'],role,h));b=lookup.get((family,True,1,color,op['id'],role,h))
                        if a is not None and b is not None:delta.append((b['payoff'] or 0)-(a['payoff'] or 0))
            if len(delta)==4*len(plan['opponents']):values.append(statistics.mean(delta))
            else:missing.append(family)
        vectors[h]=values
        if values:
            draws=[statistics.mean(rng.choices(values,k=len(values))) for _ in range(5000)]
            contrasts.append(dict(H=h,price_delta=statistics.mean(values),family95=[quantile(draws,.025),quantile(draws,.975)],complete_families=len(values),missing_families=missing))
    interaction=None
    if all(len(v)==len(families) for v in vectors.values()) and len(plan['horizons'])==2:
        lo,hi=plan['horizons'];v=[b-a for a,b in zip(vectors[lo],vectors[hi])]
        draws=[statistics.mean(rng.choices(v,k=len(v))) for _ in range(5000)]
        interaction=dict(horizons=[lo,hi],price_delta_change=statistics.mean(v),family95=[quantile(draws,.025),quantile(draws,.975)],family_values=v)
        for price in (0,1):
            count=collections.Counter();prefixequal=0;n=0
            for k,a in lookup.items():
                if k[2]!=price or k[-1]!=lo:continue
                b=lookup[k[:-1]+(hi,)];count[str(a['payoff'])+'->'+str(b['payoff'])]+=1;n+=1
                sig=lambda r:[(s['actor'],s['decision']['action']) for s in r['trajectory'][:lo]]
                prefixequal+=sig(a)==sig(b)
            transitions.append(dict(price_index=price,n=n,outcome_changes=dict(count),equal_first_H16_paths=prefixequal))
    result=dict(status='PASS_EXACT_CASE_ORDER_PUBLIC_REPLAY_AND_NATIVE_JOURNALS',games=len(rows),planned_games=len(expected),missing=len(expected)-len(rows),actual_native_go=len(choices),horizon_contrasts=contrasts,paired_horizon_interaction=interaction,outcome_transitions=transitions,scope='Separate actual games, prior TRAIN-fixed prices, same fixed proof opponent. UNKNOWN contributes zero finite W-L events but is not draw; no infinite-WDL conclusion. Timed proof/node overshoots retained; horizon groups may differ before H16 from actual scheduling/timing.',audits=audits)
    dump(p/'horizon_audit.json',result);print(json.dumps({k:v for k,v in result.items() if k!='audits'}))

if __name__=='__main__':
    import sys;audit(sys.argv[1])
