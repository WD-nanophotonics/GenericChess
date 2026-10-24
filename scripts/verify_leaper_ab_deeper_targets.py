"""Data-only replay of deeper-target episodes and their paid resource curves."""
from pathlib import Path
from collections import Counter,defaultdict
from math import isclose
import argparse,json,time
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import write
from scripts.verify_leaper_ab_learning import verify_uniform_game


def paired_bounds(slots,pairs):
    expected=defaultdict(set)
    for slot in slots:
        if slot['phase']=='eval':expected[(slot['group'],slot['root'],slot['role'])].add(slot['arm'])
    comparisons=[]
    for key,names in expected.items():
        arms=pairs.get(key,{});base=arms.get('Unit');u=None if base is None else base['utility']
        for name in sorted(names-{'Unit'}):
            r=arms.get(name);v=None if r is None else r['utility']
            lo=(v if v is not None else-1)-(u if u is not None else 1)
            hi=(v if v is not None else 1)-(u if u is not None else-1)
            comparisons.append(dict(key=key,arm=name,difference=None if lo!=hi else lo,lower=lo,upper=hi,identical_record=None if r is None or base is None else r['final_record']==base['final_record']))
    return comparisons


def verify(directory,output):
    began=time.perf_counter();load=lambda n:json.loads((directory/n).read_bytes())
    cfg=load('plan.json');result=load('result.json');models=cfg['initial_models'];totals=Counter();rows=[];pairs=defaultdict(dict)
    expected_slots=cfg['slots'];seen=[]
    for entry in result['rows']:
        slot=entry['slot'];row=load(f"game-{slot['id']:03d}.json")
        assert slot==expected_slots[len(seen)] and row['slot']==slot
        assert entry=={k:row[k]for k in('slot','before','after','result','utility')}
        key=slot.get('model_key',slot['arm'])
        assert row['before']==models[key]
        counts=verify_uniform_game(cfg['worlds'][slot['group']],row);totals.update(counts)
        if slot['phase']=='train':models[key]=row['after']
        depths=Counter();reasons=Counter();target=Counter();attempts=Counter();seconds=0.
        for event in row['events']:
            if event['kind']!='candidate':continue
            r=event['receipt'];depths[r['completed_depth']]+=1;reasons[r['reason']]+=1;seconds+=r['seconds']
            assert r['completed_depth']<=slot['depth']
            assert r['nodes']<=cfg['search']['nodes']
            assert all(a['depth']<=slot['depth']for a in r['attempts'])
            attempts.update('completed'if a['complete']else'incomplete'for a in r['attempts'])
            if not r['complete']:target['incomplete_UNKNOWN']+=1
            elif r['pv_terminal']:target['literal_terminal']+=1
            else:
                target['material']+=1
                target['free_B']+=int(r['pv_phi'][1]!=0)
        if slot['phase']=='eval':pairs[(slot['group'],slot['root'],slot['role'])][slot['arm']]=row
        rows.append(dict(slot=slot,counts=counts,completed_depth=dict(depths),reasons=dict(reasons),targets=dict(target),attempts=dict(attempts),query_seconds=seconds,
            game_seconds=row['result']['seconds'],outcome=row['result']['outcome'],utility=row['utility'],before=row['before'],after=row['after']))
        seen.append(slot)
    assert result['unstarted']==expected_slots[len(seen):] and models==result['models']
    comparisons=paired_bounds(expected_slots,pairs)
    out=dict(verified=True,producer_sha256=cfg['producer_sha256'],rows=rows,counts=dict(totals),models=models,comparisons=comparisons,unstarted=result['unstarted'],seconds=time.perf_counter()-began,
        scope='Actual complete histories, legal seeded Uniform stream, public returned PVs and independent TD arithmetic. Requested depth is not completed depth; elapsed and paid nodes are distinct. No new Player or training, no population/independent-rule claim; censored tails UNKNOWN.')
    write(output,out);return out


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();r=verify(a.directory,a.output);print(r['counts'],r['seconds'])
