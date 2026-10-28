"""Independent AUX reader of the frozen exact-static-cost packet (no search).

Literal member/source checks, source-declared raw/enriched identities and Core
replay validate finite claims. Recorded wall/CPU remain producer observations.
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, math, subprocess
from collections import Counter
from pathlib import Path, PurePosixPath
from datetime import datetime
SOURCE='009a827138cb1f49ba1e84c3f8a092c7400a260f'
BASE='docs/research/data/leaper_static_eval_20261029/'
def sha(b): return hashlib.sha256(b).hexdigest()
def git(path): return subprocess.check_output(['git','show',SOURCE+':'+path])
def encode(v): return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def save(path,v): path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((json.dumps(v,indent=2,allow_nan=False)+'\n').encode())
def archive(source):
    mb=(source/'manifest.json').read_bytes();assert mb==git(BASE+'manifest.json')
    m=json.loads(mb);b=(source/'bundle.json.gz').read_bytes();assert sha(b)==m['bundle_sha256'];raw=gzip.decompress(b);assert sha(raw)==m['bundle_raw_sha256'];d=json.loads(raw)
    declared={x['path']:x for x in m['members']};assert len(declared)==len(m['members'])==150
    actual={x['path']:x for x in d['members']};assert len(actual)==len(d['members'])==150 and set(actual)==set(declared)
    result={}
    for path,row in actual.items():
        p=PurePosixPath(path);assert not p.is_absolute() and '..' not in p.parts
        assert set(row)==set(declared[path])|{'text'}
        assert {k:v for k,v in row.items() if k!='text'}==declared[path]
        body=row['text'].encode('utf8');assert sha(body)==row['sha256'] and len(body)==row['bytes'];result[path]=body
    return result,{'source':SOURCE,'manifest_sha256':sha(mb),'gzip_sha256':sha(b),'raw_sha256':sha(raw),'literal_members':len(result)}
def untimed(x):
    return {k:v for k,v in x.items() if not k.endswith('_seconds') and k not in ('time_to_first_legal_action','time_to_first_completed_iteration')}
def finite(v): return type(v) in (int,float) and math.isfinite(v) and v>=0

def bound_inputs(output):
    expected=json.loads(gzip.decompress(git('docs/research/data/leaper_check_extension_20261028/resource/inputs.json.gz')))
    if (output/'inputs.json').exists():assert encode(json.loads((output/'inputs.json').read_bytes()))==encode({'rows':expected['rows']}),'stale or changed derived inputs'
    return expected['rows']

def bind_call_families(rows,roots):
    family={r['id']:r['family'] for r in roots};assert len(family)==len(roots)
    for r in rows:assert type(r['family']) is int and r['family']==family[r['id']],'family annotation is not frozen input family'

def check_raw(members,prefix,count,cold=False):
    rows=json.loads(members[prefix+'/queries.json']);assert len(rows)==count
    extra='Core_verified' if cold else 'Core_undo_action_PV';width=2 if cold else 3
    for slot,row in enumerate(rows):
        assert type(row['slot']) is int and row['slot']==slot and row[extra] is True
        raw=json.loads(members[f'{prefix}/query-{slot:0{width}d}.json']);assert set(row)==set(raw)|{extra}
        assert {k:v for k,v in row.items() if k!=extra}==raw
        assert all(finite(row[k]) for k in ('wall_seconds','cpu_seconds'))
        assert datetime.fromisoformat(row['started_at'])<=datetime.fromisoformat(row['ended_at'])
        assert row['caller_deadline'] is False
        stats=row['decision'] if cold else row['stats'];assert stats['runtime_pushes']==stats['runtime_pops'];assert stats['native_legality_fallbacks']==stats['native_legality_operational_failures']==0
        if cold:assert stats['runtime_depth_balanced'] and not stats['evaluation_profile_cache_hit'] and row['constructor_seconds']<=row['wall_seconds']
    return rows

def check_groups(rows,plan,reported,cold=False):
    ids=plan['ids'] if cold else plan['cost_ids'];assert len(rows)==4*len(ids)
    groups=[]
    for idx,rid in enumerate(ids):
        g=rows[idx*4:idx*4+4];assert [r['id'] for r in g]==[rid]*4;assert len({r['family'] for r in g})==1
        if cold:
            assert all(type(r['on']) is bool for r in g) and [r['on'] for r in g]==[False,True,True,False]
            assert len({encode(untimed(r['decision'])) for r in g})==1
        else:
            assert [r['mode'] for r in g]==['OFF','ON','ON','OFF']
            assert len({encode([r['result'],untimed(r['stats'])]) for r in g})==1
        for r in g:
            metric=r['mask_metrics'] if cold else r['memo'];on=r['on'] if cold else r['mode']=='ON'
            if on:
                assert metric['fallback_calls']==metric['reference_checks']==0
                assert metric['fast_calls']==metric['requests']==(r['decision'] if cold else r['stats'])['evaluation_calls']
            else:assert metric is None
        groups.append(dict(id=rid,family=g[0]['family'],parity=True,wall_OFF=g[0]['wall_seconds']+g[3]['wall_seconds'],wall_ON=g[1]['wall_seconds']+g[2]['wall_seconds'],cpu_OFF=g[0]['cpu_seconds']+g[3]['cpu_seconds'],cpu_ON=g[1]['cpu_seconds']+g[2]['cpu_seconds']))
    families={}
    for x in groups:
        v=families.setdefault(str(x['family']),[0.,0.]);v[0]+=x['cpu_ON'];v[1]+=x['cpu_OFF']
    wall=sum(x['wall_ON'] for x in groups)/sum(x['wall_OFF'] for x in groups);cpu=sum(x['cpu_ON'] for x in groups)/sum(x['cpu_OFF'] for x in groups)
    zeros=[x['id'] for x in groups if x['cpu_OFF']==0];faster=sum(a<b for a,b in families.values());eligible=not zeros
    assert reported['groups']==len(groups) and reported['eligible']==eligible
    assert reported['family_cpu']==families and reported['faster_families']==faster
    assert reported['wall_ratio']==wall and reported['cpu_ratio']==cpu
    status='NO_GO_OR_INCONCLUSIVE_LIFECYCLE' if cold else 'NO_GO_OR_INCONCLUSIVE_COST';assert not eligible and reported['status']==status
    return dict(groups=groups,wall_ratio=wall,cpu_ratio=cpu,zero_OFF_CPU_groups=zeros,family_cpu=families,faster_families=faster,original_gate=status)

def source_bindings(members):
    bindings=[]
    for p in ('mask-evaluator/frozen.json','cold-lifecycle/frozen.json','static-memo/frozen.json'):
        plan=json.loads(members[p])
        for name,expected in plan['sources'].items():
            path=name.replace('\\','/');path='/'.join(x for x in path.split('/') if x)
            b=git(path);variants={'git_LF':sha(b)}
            if path.endswith('.py'):variants['reconstructed_CRLF']=sha(b.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
            matches=[k for k,v in variants.items() if v==expected]
            bindings.append(dict(plan=p,path=path,declared_sha256=expected,git_sha256=sha(b),matches=matches))
    assert all(x['matches'] for x in bindings),'source hash does not match source bytes or explicitly reconstructed CRLF'
    return bindings

def run(source,output):
    members,binding=archive(source);get=lambda n:json.loads(members[n]);sources=source_bindings(members)
    root=check_raw(members,'mask-evaluator',51);cold=check_raw(members,'cold-lifecycle',48,True);memo=check_raw(members,'static-memo',3)
    assert [r['mode'] for r in root[:3]]==['OFF','SHADOW','OFF'];assert len({encode([r['result'],untimed(r['stats'])]) for r in root[:3]})==1
    metric=root[1]['memo'];assert metric['reference_checks']==metric['fast_calls']==metric['requests']==17414 and metric['fallback_calls']==0
    rootcheck=check_groups(root[3:],get('mask-evaluator/frozen.json'),get('mask-evaluator/cost-assessment.json'))
    coldcheck=check_groups(cold,get('cold-lifecycle/frozen.json'),get('cold-lifecycle/assessment.json'),True)
    assert [r['mode'] for r in memo]==['OFF','SHADOW','OFF'];assert len({encode([r['result'],untimed(r['stats'])]) for r in memo})==1
    mc=memo[1]['memo'];ma=get('static-memo/census-assessment.json');hit=mc['hits']/mc['requests'];assert hit==ma['hit_rate'] and hit<get('static-memo/frozen.json')['minimum_shadow_hit_rate'] and ma['eligible'] is False
    # Source-bound inputs supply literal full rules and histories; no producer execution.
    rows=bound_inputs(output);bind_call_families(root[3:]+cold,rows)
    assert [r['id'] for r in rows]==get('cold-lifecycle/frozen.json')['ids']
    save(output/'archive.json',binding);save(output/'source-bindings.json',sources);save(output/'cost-arithmetic.json',dict(root=rootcheck,cold=coldcheck,memo_hit_fraction=hit,scope='Producer recorded timings only; no remeasurement, CI, generalization, slot refill or changed gates.'))
    save(output/'inputs.json',{'rows':rows});return binding,rootcheck,coldcheck

def verify_core_and_tables(source,output):
    """Only published actual roots, actions and PVs; no new search or label."""
    from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
    from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
    from generic_chess.session.session import GameSession
    from generic_chess.session.serialization import deserialize_game_record
    from generic_chess.core.movement import LeapAtom
    from generic_chess.ai.evaluation.config import EvaluationConfig
    from generic_chess.ai.evaluation.cache import EvaluationProfileCache
    from generic_chess.ai.evaluation.evaluator import Evaluator
    from scripts.leaper_mask_evaluator import PureLeaperMaskEvaluator
    from scripts.verify_published_boolean_returns import diagnostic_action
    from scripts.research_record import record_value
    assert Path('scripts/leaper_mask_evaluator.py').read_bytes().replace(b'\r\n',b'\n')==git('scripts/leaper_mask_evaluator.py')
    members,_=archive(source);get=lambda n:json.loads(members[n]);roots=bound_inputs(output)
    census=json.loads(gzip.decompress(git('docs/research/data/leaper_check_extension_20261028/initial/inputs.json.gz')))['rows'][get('mask-evaluator/frozen.json')['census_index']]
    rows={};bridges=0;unions=0;raw_equality=0;profiles=[]
    for phase,rs in [('cost',roots),('census',[census])]:
        for row in rs:
            rule=ruleset_from_dict(row['RuleSet']);assert compute_fingerprint(rule)==row['fingerprint'];c=compile_legacy_ruleset_for_semantic_execution(rule);s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])))
            cfg=EvaluationConfig();profile,_=EvaluationProfileCache(use_disk=False).get_or_build(c,cfg);base=Evaluator(c,profile,cfg);mask=PureLeaperMaskEvaluator(c,base)
            assert not base._zones
            for typ in c.piece_types:
                assert all(isinstance(a,LeapAtom) for a in typ.movement_atoms)
                for owner in (0,1):
                    for index in range(c.board_size**2):
                        targets=set().union(*c.leap_targets[typ.type_id][owner][index]);assert targets==set(c.empty_mobility[typ.type_id][owner][index]);bridges+=1;unions+=len(targets)
            assert mask.evaluate(s.state)==base.evaluate(s.state);raw_equality+=1
            rows[(phase,row['id'])]=(c,s,base,mask);profiles.append({'phase':phase,'id':row['id'],'fingerprint':c.ruleset_fingerprint,'config':record_value(cfg),'profile':record_value(profile)})
    steps=0;actions=0;immediate=0;replayed=[]
    for prefix,cold in [('mask-evaluator',False),('cold-lifecycle',True)]:
        for q in get(prefix+'/queries.json'):
            phase='census' if prefix=='mask-evaluator' and q['slot']<3 else 'cost';c,s,base,mask=rows[(phase,q['id'])];d=q['decision'] if cold else None
            action=d['action'] if cold else q['result'][0];pv=d['principal_variation'] if cold else q['result'][2];reason=d['termination_reason'] if cold else q['result'][3]
            before=record_value(s.to_record());a=diagnostic_action(action,c.ruleset_fingerprint);assert a in s.legal_actions();actions+=1
            check=GameSession.replay(c,s.to_record());check.submit(a)
            if reason=='root_immediate_win':assert check.state.terminal_status.is_terminal and check.state.terminal_status.winner==s.state.position.side_to_move;immediate+=1
            check=GameSession.replay(c,s.to_record())
            for value in pv:
                check.submit(diagnostic_action(value,c.ruleset_fingerprint));steps+=1
                assert mask.evaluate(check.state)==base.evaluate(check.state);raw_equality+=1
            assert record_value(s.to_record())==before
            replayed.append({'phase':prefix,'slot':q['slot'],'id':q['id'],'PV_steps':len(pv),'reason':reason})
    result=dict(source=SOURCE,literal_calls=len(replayed),Core_legal_root_actions=actions,Core_legal_PV_steps=steps,selected_actual_root_wins=immediate,complete_target_table_rows=bridges,table_destination_memberships=unions,raw_reference_value_equalities=raw_equality,scope='Full-source rules/history replay and raw exact static comparisons only. No historical TT/internal tree/performance/binary reproduction. Repeated PVs count repeated receipt checks, not distinct independent states or new truth labels.')
    save(output/'Core-and-tables.json',result);save(output/'profiles.json',profiles);save(output/'replayed-returns.json',replayed);return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--phase',choices=['packet','static'],default='packet');a=p.parse_args();
    if a.phase=='static':print(json.dumps(verify_core_and_tables(a.source,a.output),indent=2));return
    b,r,c=run(a.source,a.output);print(json.dumps(dict(archive=b,root_wall_ratio=r['wall_ratio'],cold_wall_ratio=c['wall_ratio'],root_zero_CPU=r['zero_OFF_CPU_groups'],cold_zero_CPU=c['zero_OFF_CPU_groups']),indent=2))
if __name__=='__main__':main()
