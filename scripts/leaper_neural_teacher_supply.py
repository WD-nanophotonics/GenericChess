"""Teacher-data feasibility: short versus richer ordinary leaps, paired boards.

This is not a replacement accuracy panel. No network is trained, old label is
replaced, or product rule is changed. Both paired rules must admit the same
neutral three-piece start before any solving result is observed.
"""
import argparse
from dataclasses import replace
from collections import Counter
import gzip,json,random,time
from pathlib import Path
from generic_chess.core.attacks import is_in_check
from generic_chess.core.movement import LeapAtom
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_to_dict
from generic_chess.rules.validation import RuleValidationError
from generic_chess.session.session import GameSession
from scripts.leaper_design import offsets
from scripts.leaper_neural_experiment import make_rules,canonical_group
from scripts.leaper_neural_teacher import solve_session
from scripts.research_record import record_value,write_record


def run(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    write_record(output/'plan.json',dict(question='Can richer finite leap geometry provide nontrivial exact5x5WDL support at the existing teacher budget?',
               seed=20261115,starts_per_size=256,sizes=[4,5],ordinary_leap_masks=[3,23],
               domain='two king-leap royals plus one ordinary leaper; ordinary owner0/1balanced; both royals initially unchecked under BOTH paired rules; no prefix; max8/repetition3',
               nodes_per_call=1500,batch_seconds=300,maximum_teacher_calls=1024,
               admission='same neutral physical board must be Core-legal for both geometry conditions, before labels; randomized size/owner before solving',
               decision='Only teacher-data feasibility: at least60exact decisive5x5labels with>=15in eachW/Lclass and total cost reported would justify a separately designed data source. Failure/UNKNOWN is retained, no refill, no NN or player experiment.',
               caps='300second before-pair dispatch cap plus at most two in-flight1500node calls; no extension'))
    rng=random.Random(20261115);slots=[(n,owner,k) for n in (4,5) for owner in (0,1) for k in range(128)];rng.shuffle(slots)
    seen=set();tick=time.perf_counter();rows=[];stop=None
    with gzip.open(output/'results.jsonl.gz','wt',encoding='utf-8',newline='\n') as archive:
        for slot,(size,owner,rep) in enumerate(slots):
            if time.perf_counter()-tick>=300:stop='batch_cap';break
            pair=None
            for attempt in range(500):
                cells=rng.sample(range(size*size),3);pieces=[(cells[0],0,'K'),(cells[1],1,'K'),(cells[2],owner,'A')]
                base=make_rules(size,0,pieces,max_ply=8);candidate=[]
                for mask in (3,23):
                    rules=replace(base,piece_types=tuple(replace(p,movement_atoms=tuple(LeapAtom(o) for o in offsets(mask))) if p.type_id=='A' else p for p in base.piece_types))
                    try:c=compile_ruleset(rules)
                    except RuleValidationError:break
                    s=GameSession(c)
                    if s.result.status.value!='ongoing' or any(is_in_check(s.state.position,p,c) for p in (0,1)):break
                    candidate.append((mask,rules,s))
                if len(candidate)!=2:continue
                group=canonical_group(candidate[0][1],candidate[0][2])
                if group in seen:continue
                seen.add(group);pair=candidate;break
            if pair is None:
                result=dict(slot=slot,size=size,ordinary_owner=owner,replicate=rep,status='NO_COMMON_NEUTRAL_INPUT')
            else:
                returns=[]
                for mask,rules,s in (pair if slot%2==0 else list(reversed(pair))):
                    start=time.perf_counter();teacher=solve_session(rules,s,1500)
                    returns.append(dict(mask=mask,rules=ruleset_to_dict(rules),record=record_value(s.to_record()),teacher=teacher,seconds=time.perf_counter()-start))
                result=dict(slot=slot,size=size,ordinary_owner=owner,replicate=rep,status='RETURNED',conditions=returns)
            rows.append(result);archive.write(json.dumps(result,separators=(',',':'))+'\n');archive.flush()
            if slot%64==0:print(json.dumps(dict(starts=slot+1,seconds=time.perf_counter()-tick)),flush=True)
    conditions=[]
    for size in (4,5):
        for mask in (3,23):
            subset=[x for row in rows if row['size']==size for x in row.get('conditions',[]) if x['mask']==mask]
            labels=Counter(x['teacher']['label'] or 'UNKNOWN' for x in subset)
            conditions.append(dict(size=size,mask=mask,calls=len(subset),labels=dict(labels),seconds=sum(x['seconds'] for x in subset)))
    target=next(x for x in conditions if x['size']==5 and x['mask']==23);labels=target['labels']
    passed=labels.get('WIN',0)+labels.get('LOSS',0)>=60 and min(labels.get('WIN',0),labels.get('LOSS',0))>=15
    summary=dict(status='DATA_SOURCE_FEASIBLE_FOR_NEW_DESIGN' if passed else 'NO_GO_OR_INCONCLUSIVE',seconds=time.perf_counter()-tick,starts=len(rows),not_run_starts=512-len(rows),stop=stop,conditions=conditions,
                 limitation='New teacher-source feasibility only on neutral three-piece paired starts and finite8ply games. No new NN fit, transfer/strength result or outcome-selected replacement of old panels. Changed geometry also changes branching/per-node cost; report wall cost, not just counts.')
    write_record(output/'summary.json',summary);print(json.dumps(summary),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();run(a.output)
