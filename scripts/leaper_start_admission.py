"""Finite prospective developmental state pool; Core-only admission, no controller.

All geometries/layouts are retained, including terminal and forced starts. The
eligible stratum defines a conditional distribution, never a class holdout.
"""
from __future__ import annotations
import argparse, copy, gzip, hashlib, json, random, time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from scripts.research_record import record_value, write_record
from scripts.leaper_check_extension_quality import orbit, union
from scripts.leaper_pvs_quality_pilot import make_session
from generic_chess.rules.schema import compute_fingerprint, ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.semantic_executor import semantic_engine_for
from tools.local_agent import session


def stamp(): return datetime.now(timezone.utc).isoformat()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(out):
    assert not out.exists()
    out.mkdir(parents=True)
    seed = 2026102817
    source = Path('docs/research/data/leaper_root_order_quality_20261026/prepared-v2/inputs.json.gz')
    base = json.loads(gzip.decompress(source.read_bytes()))['rows'][0]['RuleSet']
    # Literal orbit pairs, not outcomes or fitted numerical values.
    pairs = [((1,0),(2,1)), ((1,1),(3,1)), ((2,0),(3,2)),
             ((2,1),(3,0)), ((1,0),(3,3)), ((1,1),(4,1)),
             ((2,2),(3,1)), ((2,0),(4,2))]
    triples = [(i, (i+3)%8, (i+5)%8) for i in range(8)]
    anchors = [(1,1), (3,1), (5,1), (3,2)]
    specification = dict(seed=seed, board_size=7, orbit_pairs=pairs,
        triples=triples, anchors=anchors, pieces_per_seat=[5,9],
        placement='Own non-anchor cells sampled without replacement from y=0..2; opponent exact rotation+owner swap; deterministic Python Random per root',
        root_seed='seed+1000*family+100*density_index+layout',
        max_ply=96, repetition_limit=4, pool_size=64,
        eligibility='Core ongoing, no initial check on either side, legal anchor moves>=2, zero actual one-ply Core WIN',
        strata='all initial anchor freedom 0/1/2+ and immediate WIN counts retained; never delete rejected roots',
        selection='First TWO eligible roots per family in density/layout order, only for a later separately frozen comparison; no refill or feature-score selection',
        scope='New DEVELOPMENT layouts/geometries from exposed primitive leaps; narrower conditional distribution, NOT holdout or all-rule coverage',
        admission_cap_seconds=120, row_cap_seconds=10,
        source_sha256=sha(source), generator_sha256=sha(__file__),
        frozen_at=stamp(), status='FROZEN_BEFORE_CORE')
    write_record(out/'specification.json', specification)
    rows=[]
    for f,triple in enumerate(triples):
        patterns=[union(orbit(*pairs[j][0]),orbit(*pairs[j][1])) for j in triple]
        for di,density in enumerate((5,9)):
            for layout,anchor in enumerate(anchors):
                rng=random.Random(seed+1000*f+100*di+layout)
                cells=[(x,y) for y in range(3) for x in range(7) if (x,y)!=anchor]
                chosen=rng.sample(cells,density-1)
                home=[('K',*anchor)]+[(('A','B','C')[j%3],*xy) for j,xy in enumerate(chosen)]
                r=copy.deepcopy(base)
                r.update(board_size=7,max_ply=96,initial_position=[[None]*7 for _ in range(7)],metadata={})
                r['piece_types']=[dict(type_id=t,name=t,movement_atoms=[dict(kind='leap',offset=list(o)) for o in offsets],is_anchor=t=='K',is_promotable=False,promotion_target_ids=[]) for t,offsets in zip(('K','A','B','C'),(union(orbit(1,0),orbit(1,1)),*patterns))]
                r['drop_allowed']={t:[[False]*49,[False]*49] for t in ('A','B','C')}
                for owner in (0,1):
                    for typ,x,y in home:
                        if owner:x,y=6-x,6-y
                        assert r['initial_position'][y][x] is None
                        r['initial_position'][y][x]=dict(owner=owner,base_type_id=typ,current_type_id=typ,promoted=False)
                fp=compute_fingerprint(ruleset_from_dict(r))
                rows.append(dict(id=f'na-f{f}-d{density}-h{layout}',family=f,density=density,layout=layout,RuleSet=r,fingerprint=fp,record=dict(schema_version=1,ruleset_fingerprint=fp,actions=[],resigned_by=None),prefix_length=0,exposure=specification['scope']))
    assert len(rows)==len({r['fingerprint'] for r in rows})==64
    write_record(out/'inputs.json',dict(rows=rows))
    write_record(out/'input-lock.json',dict(at=stamp(),input_sha256=sha(out/'inputs.json'),spec_sha256=sha(out/'specification.json'),roots=64,Core_calls=0,Player_calls=0))


def audit(prepared,out):
    out.mkdir(parents=True,exist_ok=True)
    spec=json.loads((prepared/'specification.json').read_bytes())
    lock=json.loads((prepared/'input-lock.json').read_bytes())
    assert sha(prepared/'inputs.json')==lock['input_sha256']
    assert sha(prepared/'specification.json')==lock['spec_sha256']
    amendment=prepared/'compiler-rejection-amendment.json'
    assert sha(__file__)==(json.loads(amendment.read_bytes())['amended_generator_sha256'] if amendment.exists() else spec['generator_sha256'])
    rows=json.loads((prepared/'inputs.json').read_bytes())['rows'];results=[]
    prior=json.loads((out/'rows.json').read_bytes()) if (out/'rows.json').exists() else []
    prior=[x for x in prior if x['status']!='NOT_RUN']
    for x in prior:
        if x['status']=='FAILED' and x.get('error_type')=='RuleValidationError' and '[INITIAL_ANCHOR_ATTACKED]' in x.get('error',''):
            x.update(original_status='FAILED',status='REJECTED_COMPILER',reasons=['initial_check_rejected_by_compiler'])
    assert all(x['status'] in ('AUDITED','REJECTED_COMPILER') for x in prior)
    tick=time.perf_counter();halt=None
    from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
    from generic_chess.core.search_runtime import _plain_leaper_hash_patterns
    for row in rows:
        if len(results)<len(prior):
            old=prior[len(results)];assert old['case_id']==row['id'];results.append(old);continue
        begin=stamp();rt=time.perf_counter();x=dict(case_id=row['id'],family=row['family'],density=row['density'],layout=row['layout'],status='NOT_RUN',eligible=False)
        if time.perf_counter()-tick+spec['row_cap_seconds']>=spec['admission_cap_seconds']:halt=halt or 'batch_reserve'
        for n in ('rollout','advisor','slack'):
            flags=json.loads((Path('.local_agent')/(n+'.json')).read_bytes())
            if any(flags.get(k,False) for k in ('stopped','stop_requested','research_stopped','user_paused')):halt='scoped_stop'
        if not halt:
            try:
                rules=ruleset_from_dict(row['RuleSet']);assert compute_fingerprint(rules)==row['fingerprint']
                c=compile_legacy_ruleset_for_semantic_execution(rules)
                s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])))
                assert _plain_leaper_hash_patterns(c) is not None
                engine=semantic_engine_for(c);actor=s.state.position.side_to_move
                checks=[engine.in_check(s.state.position,p) for p in (0,1)]
                legal=s.legal_actions();anchor=[a for a in legal if getattr(a,'actor_type_id',None)=='K']
                wins=[];terminals=[]
                for a in legal:
                    if time.perf_counter()-rt>spec['row_cap_seconds']:raise TimeoutError('row cap; no retry')
                    child=GameSession.replay(c,s.to_record());child.submit(a)
                    term=child.state.terminal_status
                    if term.is_terminal:terminals.append(dict(action=record_value(a),terminal=record_value(term)))
                    if term.is_terminal and term.winner==actor:wins.append(record_value(a))
                reasons=[]
                if s.state.terminal_status.is_terminal:reasons.append('initial_terminal')
                if any(checks):reasons.append('initial_check')
                if len(anchor)<2:reasons.append('anchor_freedom_below2')
                if wins:reasons.append('one_ply_Core_WIN')
                x.update(status='AUDITED',eligible=not reasons,reasons=reasons,initial_terminal=record_value(s.state.terminal_status),checks=checks,legal_count=len(legal),anchor_actions=record_value(anchor),anchor_freedom=len(anchor),one_ply_wins=wins,one_ply_terminals=terminals)
            except Exception as e:
                x.update(status='FAILED',error_type=type(e).__name__,error=str(e))
                if type(e).__name__=='RuleValidationError' and '[INITIAL_ANCHOR_ATTACKED]' in str(e):
                    x.update(status='REJECTED_COMPILER',reasons=['initial_check_rejected_by_compiler'])
                else:halt='semantic_or_budget_failure'
        else:x['reason']=halt
        x.update(started_at=begin,ended_at=stamp(),wall_seconds=time.perf_counter()-rt)
        results.append(x);write_record(out/'rows.json',results)
        if x['status']!='NOT_RUN' and begin<x['ended_at']:
            session.record_work(begin,x['ended_at'],'validation',str(out/'rows.json')+':'+row['id'])
    selected=[]
    for f in range(8):selected.extend([x['case_id'] for x in results if x['family']==f and x['eligible']][:2])
    summary=dict(at=stamp(),statuses=dict(Counter(x['status'] for x in results)),eligible=sum(x['eligible'] for x in results),selected=selected,selected_counts=dict(Counter(x['family'] for x in results if x['case_id'] in selected)),strata=dict(Counter(str(min(2,x['anchor_freedom'])) for x in results if 'anchor_freedom' in x)),halt=halt,input_sha256=lock['input_sha256'],scope=spec['scope'],Player_calls=0,game_calls=0)
    write_record(out/'summary.json',summary);print(json.dumps(summary),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','audit']);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.mode=='prepare':prepare(a.prepared)
    else:audit(a.prepared,a.output)
