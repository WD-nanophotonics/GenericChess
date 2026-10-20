"""Outcome-blind independent evaluation of all frozen task2618 v4 models."""
from __future__ import annotations
import copy, datetime, hashlib, json, random
from pathlib import Path
import chess
from results.dev_aux.task2619.root_feasibility import generated_root, canonical, read_initial_records
from results.dev_aux.task2618.evaluate_learners import verify_training_result
from tools.local_agent.environment import require_identity
from results.dev_aux.task2392.reader import SharedDeleteStopReader
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'results/dev_aux/task2620'
ORIGINAL=ROOT/'results/dev_aux/task2618/learner-comparison-v4'


def sha(data): return hashlib.sha256(data).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def write_once(path,obj):
    with path.open('x',encoding='utf-8') as f:
        f.write(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n')


def exclusions():
    keys=set();sources=[]
    prior=read(ROOT/'results/dev_aux/task2619/root-feasibility.json')
    for row in prior['prior_source_rows']:
        if 'path' in row:
            p=ROOT/row['path'];found,n=read_initial_records(p)
            keys.update(found);sources.append(dict(path=row['path'],sha256=sha(p.read_bytes()),initial_rows=n))
        elif row.get('kind')=='reconstructed_possible_training_starts':
            a,b=row['family_range']
            for family in range(a,b):
                record=generated_root(row['generator_seed'],family)
                if record is not None: keys.add(canonical(record))
    for name in ('prospective-training-roots.json','prospective-evaluation-roots.json'):
        p=ROOT/'results/dev_aux/task2619'/name
        keys.update(canonical(row['record']) for row in read(p)['roots'])
        sources.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p.read_bytes())))
    return keys,sources


def select_roots(excluded,count=48):
    rows=[];seen=set(excluded)
    for family in range(920001,930001):
        record=generated_root(0,family)
        if record is None: continue
        key=canonical(record)
        if key in seen: continue
        seen.add(key);rows.append(dict(family=family,generator_seed=0,record=record,record_sha256=sha(key.encode())))
        if len(rows)==count: return rows
    raise ValueError('insufficient unexposed roots')



def validate_plan(plan):
    config=plan['evaluation'];families=set(map(int,config['caps_by_family']))
    if config['root_count']!=len(families): raise ValueError('root count inconsistent')
    expected={(i,seed,f,color,e) for i,seed in enumerate(plan['seeds']) for f in families
              for color in (0,1) for e in ('initial','TreeStrap','TDLeaf','WDL')}
    slots=[tuple(s) for s in config['ordered_slots']]
    if len(slots)!=len(expected) or set(slots)!=expected or config['expected_slots']!=len(slots):
        raise ValueError('incomplete paired slot cross product')
    if 'evaluation_root_selection' in plan or 'training_root_selection' in plan:
        raise ValueError('do not copy unrelated original selection metadata')


def register():
    require_identity()
    out=OUT/'run-002'
    if out.exists(): raise FileExistsError('write-once experiment; do not replace or top-up')
    original_raw=(ORIGINAL/'plan.json').read_bytes();original=json.loads(original_raw)
    training_raw=(ORIGINAL/'training-result.json').read_bytes();training=json.loads(training_raw)
    verify_training_result(original,training,sha(original_raw))
    for name,digest in original['source_sha256'].items():
        if sha((ROOT/name).read_bytes())!=digest: raise ValueError('immutable source changed: '+name)
    if any((ORIGINAL/n).exists() for n in ('evaluation-started.json','evaluation-result.json')):
        raise ValueError('old evaluation exposure changed; reconsider protocol')
    excluded,prior_sources=exclusions();roots=select_roots(excluded)
    rng=random.Random(2620001)
    families=[r['family'] for r in roots];rng.shuffle(families)
    caps={str(f):20000 if i<len(families)//2 else 40000 for i,f in enumerate(families)}
    seeds=original['seeds'];endpoints=['initial','TreeStrap','TDLeaf','WDL']
    slots=[]
    blocks=[(i,seed,f,color) for i,seed in enumerate(seeds) for f in families for color in (0,1)]
    rng.shuffle(blocks)
    for i,seed,f,color in blocks:
        order=list(endpoints);rng.shuffle(order)
        slots.extend([i,seed,f,color,e] for e in order)
    roots_doc=dict(roots=roots,excluded_exact_records=len(excluded),prior_source_pins=prior_sources,
        claim='Exact full-history start disjointness only; no descendant/population independence; no outcome selection.')
    roots_raw=(json.dumps(roots_doc,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
    cost=read(ROOT/'results/dev_aux/task2618/feasibility.json')
    src=cost['evaluation_source'];cost_path=ROOT/src['path']
    cost_result=read(cost_path)
    if cost_result['expected']!=src['slots'] or cost_result['actual']!=src['slots']:
        raise ValueError('cost source incomplete')
    session=read(ROOT/'.local_agent/session.json')
    prep_started=datetime.datetime.fromisoformat(session['started_at'])
    preparation_seconds=(datetime.datetime.now(datetime.timezone.utc)-prep_started).total_seconds()
    estimate=preparation_seconds+src['seconds']*len(slots)/src['slots']*1.25+600
    if estimate>=7200: raise ValueError('Chat assessment required before this >=120minute experiment')
    session=read(ROOT/'.local_agent/session.json')
    if session['state']!='active': raise ValueError('active owned research segment required')
    pins=dict(original['source_sha256'])
    for relative in ('results/dev_aux/task2620/evaluate.py','results/dev_aux/task2620/protocol.py',
                     'results/dev_aux/task2620/launch.py','results/dev_aux/task2619/root_feasibility.py',
                     'results/dev_aux/task2618/analyze_learners.py','tools/local_agent/environment.py'):
        pins[relative]=sha((ROOT/relative).read_bytes())
    plan={name:copy.deepcopy(original[name]) for name in ('seeds','methods','nodes_per_seed_method_arm','fixed_foe_weights','evaluation','python_chess_version')}
    plan.update(task='DEV_AUX2620',kind='NEW_INDEPENDENT_FIXED_MODEL_EVALUATION',
        session_id=session['id'],preparation_started_at=session['started_at'],registered_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        source_sha256=pins,training_plan_path=(ORIGINAL/'plan.json').relative_to(ROOT).as_posix(),
        training_plan_sha256=sha(original_raw),training_result_sha256=sha(training_raw),
        evaluation_root_manifest_sha256=sha(roots_raw),all_in_hard_cap_seconds=6600,
        feasibility=dict(estimate_seconds=estimate,preparation_seconds=preparation_seconds,cost_source=src,cost_source_sha256=sha(cost_path.read_bytes()),
                         extrapolation='1.5x slots; same20k/40k caps;25percent execution margin, actual preparation plus600s audit reserve'),
        closure='Original task2618 training complete; its session-bound evaluation remains unstarted; no old cap/slot/source modified.',
        current_registration_is_not_fresh_training=True)
    config=plan['evaluation'];config.update(root_count=48,expected_slots=len(slots),ordered_slots=slots,
        caps_by_family=caps,hard_cap_seconds=4500,cap_assignment_order=families,cap_randomization_seed=2620001)
    SharedDeleteStopReader(ROOT)()
    validate_plan(plan)
    out.mkdir()
    (out/'training-result.json').write_bytes(training_raw)
    (out/'evaluation-root-manifest.json').write_bytes(roots_raw)
    write_once(out/'plan.json',plan)
    write_once(out/'registration.json',dict(status='REGISTERED_PRE_EVALUATION',plan_sha256=sha((out/'plan.json').read_bytes()),
        training_result_sha256=sha(training_raw),evaluated_outcomes_used_for_selection=False,
        source_sha256=pins,session_id=session['id']))
    return dict(status='REGISTERED_PRE_EVALUATION',roots=len(roots),slots=len(slots),
        excluded=len(excluded),estimate_minutes=estimate/60,all_in_cap_minutes=110,
        plan_sha256=sha((out/'plan.json').read_bytes()))


if __name__=='__main__': print(json.dumps(register(),indent=2,sort_keys=True))
