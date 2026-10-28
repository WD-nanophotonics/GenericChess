"""Independent AUX consumer of the pinned admitted-extension packet; Core replay only.

No producer, Player, search, solver, new game or additional truth-label generation.
Recorded time/counters are checked for consistency, not independently observed.
"""
from __future__ import annotations
import argparse, ast, copy, gzip, hashlib, json, math, random, sys, time
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.research_record import record_value
from generic_chess.rules.schema import ruleset_from_dict, compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.verify_published_boolean_returns import diagnostic_action
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.config import EvaluationConfig, MATE_SCORE

SOURCE='e9d4f253bf96ce302cdcd8ded86bf049802ac301'
MANIFEST_SHA='36c98cd387bdd29ab1171f234686a6328970459e28e7daa10ca57cf9a37c7ea5'

def digest(raw): return hashlib.sha256(raw).hexdigest()
def source_bytes(path):
    path=Path(path)
    if not path.exists(): path=Path(str(path)+'.gz')
    b=path.read_bytes()
    return gzip.decompress(b) if path.suffix=='.gz' else b
def load(path): return json.loads(source_bytes(path))
def encoded(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def record_hash(s): return digest(encoded(record_value(s.to_record())))
def finite(x): return type(x) in (int,float) and math.isfinite(x) and x>=0

def verify_archives(source):
    b=(source/'manifest.json').read_bytes(); assert digest(b)==MANIFEST_SHA
    manifest=json.loads(b); rows=manifest['members']; assert len(rows)==64
    assert len({x['path'] for x in rows})==64
    checks=[]
    for row in rows:
        name=row['path']; assert not Path(name).is_absolute() and '..' not in Path(name).parts
        raw=(source/name).read_bytes(); assert digest(raw)==row['sha256'],name
        decoded=gzip.decompress(raw)
        assert digest(decoded)==row['raw_sha256'] and len(decoded)==row['raw_bytes'],name
        # If an extraction also exists it must be the same frozen source, not a silent override.
        expanded=(source/name).with_suffix('')
        if expanded.exists(): assert expanded.read_bytes()==decoded,name
        checks.append({'path':name,'compressed_sha256':digest(raw),'raw_sha256':digest(decoded),'raw_bytes':len(decoded)})
    return {'source':SOURCE,'manifest_sha256':MANIFEST_SHA,'pairs':checks,'status':'PASS'}

def validate_call(q, expected_on, profile):
    assert type(expected_on) is bool and type(q['on']) is bool and q['on']==expected_on
    assert q['status']=='RETURNED' and type(q['seat']) is int and q['seat'] in (0,1)
    assert type(q['ply_before']) is int and q['ply_before']>=0
    assert encoded(q['actual_tuning'])==encoded(record_value(SearchTuning(use_one_check_extension=expected_on)))
    assert encoded(q['evaluation_profile'])==encoded(profile)
    limits=q['limits']
    expected={'max_depth':64,'max_nodes':500000,'quiescence_max_depth':4,'quiescence_hard_max_depth':8,'quiescence_max_nodes':None,'deterministic':True}
    assert set(limits)==set(expected)|{'max_time_seconds'}
    for k,v in expected.items(): assert limits[k]==v and type(limits[k]) is type(v),k
    assert q['requested_service_seconds']==1.5
    for k in ['construction_packing_seconds','service_wall_seconds','cpu_seconds']: assert finite(q[k]),k
    assert finite(limits['max_time_seconds']) and 0<limits['max_time_seconds']<=1.5
    assert abs(limits['max_time_seconds']+q['construction_packing_seconds']-1.5)<=1e-9
    assert q['construction_packing_seconds']<=q['service_wall_seconds']
    assert type(q['caller_deadline_observed']) is bool
    assert type(q['timing_eligible']) is bool and q['timing_eligible']==(q['service_wall_seconds']<=1.65)
    assert q['provider_present'] is True and q['provider_delta']['availability'].get('declines',0)==0
    d=q['decision']
    assert type(d['score']) is int and type(d['completed_depth']) is int
    assert d['choice_kind']=='ACTION' and d['declaration'] is None
    assert d['runtime_depth_balanced'] is True and d['runtime_pushes']==d['runtime_pops']
    assert d['native_legality_fallbacks']==d['native_legality_operational_failures']==0
    assert d['pvs_null_window_searches']==d['pvs_researches']==0
    for name in ['main_check_extensions','main_extension_max_path','main_search_max_ply']:
        assert type(d[name]) is int and d[name]>=0,name
    assert d['main_extension_max_path']<=int(expected_on)
    if not expected_on: assert d['main_check_extensions']==d['main_extension_max_path']==d['main_search_max_ply']==0
    if d['result_source']=='main_iteration':
        assert d['completed_depth']>=1
        assert d['result_ordinary_qdepth']==(0 if d['completed_depth']==1 else 4)
        assert d['result_check_hard_qdepth']==8
    elif d['result_source']=='root_immediate_win':
        assert d['completed_depth']==0 and d['score']==MATE_SCORE-1
    else:
        # A fallback would need a separately reviewed contract, not a numeric label.
        raise AssertionError('unqualified return source: '+d['result_source'])

def raw_return(qid, returns):
    row=returns[qid]; text=row['original_utf8']; assert digest(text.encode())==row['sha256']
    q=json.loads(text); assert q['query_id']==qid
    return q

def verify_return(q, session, compiled, expected_on, profile):
    validate_call(q,expected_on,profile)
    assert not session.state.terminal_status.is_terminal
    assert q['record_before_sha256']==record_hash(session)
    assert q['seat']==session.state.position.side_to_move and q['ply_before']==session.state.ply_count
    a=diagnostic_action(q['decision']['action'],compiled.ruleset_fingerprint)
    assert a in session.legal_actions()
    pv=q['decision']['principal_variation'];assert not pv or pv[0]==q['decision']['action']
    branch=GameSession.replay(compiled,session.to_record())
    for literal in pv:
        assert not branch.state.terminal_status.is_terminal
        branch.submit(diagnostic_action(literal,compiled.ruleset_fingerprint))
    if q['decision']['result_source']=='root_immediate_win':
        child=GameSession.replay(compiled,session.to_record()); child.submit(a)
        assert child.state.terminal_status.is_terminal and child.state.terminal_status.winner==q['seat']
    return a,len(pv)

def endpoints(games):
    assert len(games)==30 and [g['game_id'] for g in games]==list(range(30))
    families=defaultdict(list);outcomes=Counter();pairs=[]
    for i in range(0,30,2):
        a,b=games[i:i+2]
        assert a['case_id']==b['case_id'] and a['initial_record']==b['initial_record'] and (a['on_seat'],b['on_seat'])==((0,1) if i//2%2==0 else (1,0))
        pairs.append({'case_id':a['case_id'],'family':a['family'],'points':sum(.5 if g['Core_terminal']['winner'] is None else int(g['Core_terminal']['winner']==g['on_seat']) for g in (a,b))})
    for g in games:
        assert g['status']=='TERMINAL' and g['timing_eligible'] is True
        winner=g['Core_terminal']['winner'];assert winner is None or type(winner) is int and winner in (0,1)
        point=.5 if winner is None else int(winner==g['on_seat'])
        families[g['family']].append(point);outcomes['DRAW' if winner is None else 'ON_WIN' if point else 'ON_LOSS']+=1
    assert set(families)==set(range(8))
    per={str(f):{'games':len(x),'points':sum(x),'fraction':sum(x)/len(x)} for f,x in sorted(families.items())}
    points=sum(x['points'] for x in per.values());positive=sum(x['fraction']>.5 for x in per.values())
    return {'outcomes':dict(outcomes),'points':points,'raw_fraction':points/30,'equal_family_fraction':sum(x['fraction'] for x in per.values())/8,'positive_families':positive,'families':per,'pairs':pairs,'frozen_gate_passed':positive>=5 and points>=.55*30,'scope':'Finite conditional DEVELOPMENT endpoint; no IID/population CI or matched-state speed claim.'}

def qualification_schedule(quals, root_ids):
    assert len(root_ids)==15 and len(set(root_ids))==15
    assert len(quals)==30 and [q['slot'] for q in quals]==list(range(30))
    for slot,q in enumerate(quals):
        rid=root_ids[slot//2];on=((False,True) if slot//2%2==0 else (True,False))[slot%2]
        assert q['case_id']==rid and q['on'] is on and q['status']=='RETURNED' and q['query_id']==f'q{slot:04d}'
        assert q['accepted_goal']=='legal_same_service_return'

def check_submission(raw, embedded, actual_after_hash):
    assert 'record_after_sha256' not in raw
    assert set(embedded)-set(raw)=={'record_after_sha256','pv_legal','root_unchanged'}
    assert all(embedded[k]==v for k,v in raw.items())
    assert embedded['root_unchanged'] is embedded['pv_legal'] is True
    assert embedded['record_after_sha256']==actual_after_hash

def verify_packet(source, output):
    started=time.perf_counter();archives=verify_archives(source)
    roots=load(source/'comparison-prepared/inputs.json')['rows']; plan=load(source/'comparison-plan.json')
    frozen=load(source/'comparison-run/frozen.json'); returns=load(source/'comparison-run/returns.json')
    quals=load(source/'comparison-run/qualification.json');games=load(source/'comparison-run/games.json')
    assert frozen['plan']==plan and frozen['input_sha256']==plan['input_sha256']
    assert digest(source_bytes(source/'comparison-prepared/inputs.json'))==plan['input_sha256']
    assert [r['id'] for r in roots]==plan['root_ids'] and len(roots)==15 and len(set(plan['root_ids']))==15
    assert plan['planned_roots']==15 and plan['planned_games']==30 and plan['default_enabled'] is False
    assert plan['service_seconds_per_call']==1.5 and plan['PVS'] is False
    assert plan['first_iteration_Q']==0 and plan['later_Q']==4 and plan['Q_hard']==8
    assert set(frozen['sources'])==set(plan['sources']) and len(frozen['sources'])==9
    for name,text in frozen['sources'].items(): assert digest(text.encode())==plan['sources'][name],name
    rootmap={}; profiles={};compiled={}
    for root in roots:
        rules=ruleset_from_dict(root['RuleSet']); assert compute_fingerprint(rules)==root['fingerprint']
        c=compile_legacy_ruleset_for_semantic_execution(rules);compiled[root['id']]=c;rootmap[root['id']]=root
        profiles[root['id']]=record_value(build_ruleset_profile(c,EvaluationConfig()))
    seen=set();pvcount=0;game_moves=0;summaryrows=[];counts=Counter();cost=defaultdict(Counter)
    def consume(qid,root,s,on):
        nonlocal pvcount
        assert qid not in seen;seen.add(qid);q=raw_return(qid,returns)
        a,n=verify_return(q,s,compiled[root['id']],on,profiles[root['id']]);pvcount+=n
        return q,a
    qualification_schedule(quals,plan['root_ids'])
    for slot,q in enumerate(quals):
        rid=plan['root_ids'][slot//2];on=((False,True) if slot//2%2==0 else (True,False))[slot%2]
        assert q['case_id']==rid and q['on'] is on and q['status']=='RETURNED' and q['query_id']==f'q{slot:04d}'
        assert q['accepted_goal']=='legal_same_service_return'
        r=rootmap[rid];s=GameSession.replay(compiled[rid],deserialize_game_record(json.dumps(r['record'])))
        raw,a=consume(q['query_id'],r,s,on);assert raw['decision']==q['decision'] and raw['timing_eligible'] is True
    qualification_pv=pvcount
    assert len(games)==30
    for index,g in enumerate(games):
        rid=plan['root_ids'][index//2];r=rootmap[rid];c=compiled[rid]
        assert g['game_id']==index and g['case_id']==rid and g['on_seat']==(((0,1) if index//2%2==0 else (1,0))[index%2])
        for field in ['family','layout','fingerprint']: assert g[field]==r[field]
        assert g['initial_record']==r['record']
        s=GameSession.replay(c,deserialize_game_record(json.dumps(r['record'])))
        for embedded in g['queries']:
            q,a=consume(embedded['query_id'],r,s,s.state.position.side_to_move==g['on_seat'])
            d=q['decision'];counts['source:'+d['result_source']]+=1;counts['reason:'+d['termination_reason']]+=1
            arm='ON' if q['on'] else 'OFF';counts[arm]+=1
            for field in ['service_wall_seconds','cpu_seconds']: cost[arm][field]+=q[field]
            cost[arm]['extensions']+=d['main_check_extensions']
            s.submit(a);game_moves+=1;check_submission(q,embedded,record_hash(s))
        assert record_value(s.to_record())==g['final_record']
        assert record_value(s.state.terminal_status)==g['Core_terminal'] and record_value(s.result)==g['Session_result']
        assert s.state.terminal_status.is_terminal and g['status']=='TERMINAL'
        assert g['timing_eligible']==all(q['timing_eligible'] for q in g['queries'])
        summaryrows.append({'game_id':index,'case_id':rid,'family':r['family'],'on_seat':g['on_seat'],'moves':len(g['queries']),'final_record_sha256':record_hash(s),'terminal':record_value(s.state.terminal_status)})
    assert seen==set(returns) and len(seen)==2160 and game_moves==2130
    result={'source':SOURCE,'archive_pairs':len(archives['pairs']),'declared_source_capsules':9,'profiles_recomputed':len(profiles),'raw_returns':len(seen),'game_moves':game_moves,'qualification_pv':qualification_pv,'game_pv':pvcount-qualification_pv,'total_pv':pvcount,'counts':dict(counts),'recorded_cost':dict(cost),'games':summaryrows,'endpoint':endpoints(games),'independent_replay_seconds':time.perf_counter()-started,'status':'PASS','limits':'Core replay, archive and recorded-contract acceptance only. No independent search execution, historic binary reproduction, timing observation, TT trace, strict error label, strength or speedup.'}
    output.mkdir(parents=True,exist_ok=True);(output/'packet.json').write_text(json.dumps(result,indent=2)+'\n');(output/'archives.json').write_text(json.dumps(archives,indent=2)+'\n')
    return result

def declared_pool_rows(spec, base):
    """Literal specification reconstruction; never import or execute the producer."""
    def orbit(a,b):
        return {(x*sa,y*sb) for x,y in ((a,b),(b,a)) for sa in (-1,1) for sb in (-1,1)}
    def union(*parts): return sorted(set().union(*parts))
    assert spec['seed']==2026102817 and spec['board_size']==7
    assert spec['pieces_per_seat']==[5,9] and spec['max_ply']==96 and spec['repetition_limit']==4
    assert spec['triples']==[[i,(i+3)%8,(i+5)%8] for i in range(8)]
    assert spec['anchors']==[[1,1],[3,1],[5,1],[3,2]] and spec['pool_size']==64
    rows=[]
    for family,triple in enumerate(spec['triples']):
        patterns=[union(*(orbit(*pair) for pair in spec['orbit_pairs'][j])) for j in triple]
        for di,density in enumerate(spec['pieces_per_seat']):
            for layout,anchor_list in enumerate(spec['anchors']):
                anchor=tuple(anchor_list); rng=random.Random(spec['seed']+1000*family+100*di+layout)
                cells=[(x,y) for y in range(3) for x in range(7) if (x,y)!=anchor]
                chosen=rng.sample(cells,density-1)
                home=[('K',*anchor)]+[(('A','B','C')[j%3],*xy) for j,xy in enumerate(chosen)]
                rule=copy.deepcopy(base)
                rule.update(board_size=7,max_ply=96,initial_position=[[None]*7 for _ in range(7)],metadata={})
                rule['piece_types']=[dict(type_id=t,name=t,movement_atoms=[dict(kind='leap',offset=list(o)) for o in offsets],is_anchor=t=='K',is_promotable=False,promotion_target_ids=[]) for t,offsets in zip(('K','A','B','C'),(union(orbit(1,0),orbit(1,1)),*patterns))]
                rule['drop_allowed']={t:[[False]*49,[False]*49] for t in ('A','B','C')}
                for owner in (0,1):
                    for kind,x,y in home:
                        if owner: x,y=6-x,6-y
                        assert rule['initial_position'][y][x] is None
                        rule['initial_position'][y][x]=dict(owner=owner,base_type_id=kind,current_type_id=kind,promoted=False)
                fp=compute_fingerprint(ruleset_from_dict(rule))
                rows.append(dict(id=f'na-f{family}-d{density}-h{layout}',family=family,density=density,layout=layout,RuleSet=rule,fingerprint=fp,record=dict(schema_version=1,ruleset_fingerprint=fp,actions=[],resigned_by=None),prefix_length=0,exposure=spec['scope']))
    return rows

def verify_admission(source, output):
    from generic_chess.rules.validation import RuleValidationError
    from generic_chess.core.semantic_executor import semantic_engine_for
    from generic_chess.core.search_runtime import _plain_leaper_hash_patterns
    began=time.perf_counter();spec=load(source/'prepared/specification.json');lock=load(source/'prepared/input-lock.json')
    rows=load(source/'prepared/inputs.json')['rows'];old=load(source/'audit/rows-original-partial.json');audit=load(source/'audit/rows.json')
    assert digest(source_bytes(source/'prepared/inputs.json'))==lock['input_sha256']
    assert digest(source_bytes(source/'prepared/specification.json'))==lock['spec_sha256']
    assert lock['roots']==64 and lock['Core_calls']==lock['Player_calls']==0
    basebytes=(source/'base-inputs.json.gz').read_bytes();assert digest(basebytes)==spec['source_sha256']
    base=json.loads(gzip.decompress(basebytes))['rows'][0]['RuleSet']
    assert rows==declared_pool_rows(spec,base) and len({r['fingerprint'] for r in rows})==64
    snapshot=load(source/'current-source-snapshots.json')['leaper_start_admission']
    original=source_bytes(source/'generator-before-amendment-hash-reconstruction.py')
    amendment=load(source/'prepared/compiler-rejection-amendment.json')
    assert digest(original)==spec['generator_sha256'] and digest(snapshot.encode())==amendment['amended_generator_sha256']
    def prepare_ast(text):
        return ast.dump(next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='prepare'))
    assert prepare_ast(original.decode())==prepare_ast(snapshot)
    assert len(old)==9 and old[:7]==audit[:7]
    assert old[7]['status']=='FAILED' and audit[7]['original_status']=='FAILED'
    assert audit[7]['error']==old[7]['error'] and old[8]['status']=='NOT_RUN'
    assert len(audit)==64 and [x['case_id'] for x in audit]==[r['id'] for r in rows]
    statuses=Counter();strata=Counter();issues=Counter();child_count=0;selected=[];observations=[]
    for root,saved in zip(rows,audit):
        for k in ['family','density','layout']: assert saved[k]==root[k]
        rule=ruleset_from_dict(root['RuleSet']);assert compute_fingerprint(rule)==root['fingerprint']
        try: c=compile_legacy_ruleset_for_semantic_execution(rule)
        except RuleValidationError as e:
            assert saved['status']=='REJECTED_COMPILER' and saved['eligible'] is False
            assert str(e)==saved['error'] and saved['error_type']=='RuleValidationError'
            codes=[i.code for i in e.issues]
            assert codes.count('INITIAL_ANCHOR_ATTACKED')==2 and set(codes)<= {'INITIAL_ANCHOR_ATTACKED','INITIAL_NO_LEGAL_MOVE'}
            issues.update(codes);assert saved['reasons']==['initial_check_rejected_by_compiler']
            assert not {'anchor_freedom','legal_count','anchor_actions','one_ply_wins'}&saved.keys()
            statuses['REJECTED_COMPILER']+=1
            observations.append({'case_id':root['id'],'family':root['family'],'density':root['density'],'eligible':False,'status':'REJECTED_COMPILER','anchor_freedom':None,'issues':codes})
            continue
        assert _plain_leaper_hash_patterns(c) is not None
        session=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])))
        engine=semantic_engine_for(c);checks=[engine.in_check(session.state.position,seat) for seat in (0,1)]
        legal=session.legal_actions();anchor=[record_value(a) for a in legal if a.actor_type_id=='K']
        terminals=[];wins=[]
        for action in legal:
            child=GameSession.replay(c,session.to_record());child.submit(action);child_count+=1
            terminal=child.state.terminal_status
            if terminal.is_terminal: terminals.append({'action':record_value(action),'terminal':record_value(terminal)})
            if terminal.is_terminal and terminal.winner==session.state.position.side_to_move: wins.append(record_value(action))
        reasons=[]
        if session.state.terminal_status.is_terminal: reasons.append('initial_terminal')
        if any(checks): reasons.append('initial_check')
        if len(anchor)<2: reasons.append('anchor_freedom_below2')
        if wins: reasons.append('one_ply_Core_WIN')
        assert saved['status']=='AUDITED' and saved['initial_terminal']==record_value(session.state.terminal_status)
        assert saved['checks']==checks and saved['anchor_actions']==anchor and saved['anchor_freedom']==len(anchor)
        assert saved['legal_count']==len(legal) and saved['one_ply_wins']==wins and saved['one_ply_terminals']==terminals
        assert saved['eligible']==(not reasons) and saved['reasons']==reasons
        statuses['AUDITED']+=1;strata[str(min(2,len(anchor)))]+=1
        observations.append({'case_id':root['id'],'family':root['family'],'density':root['density'],'eligible':not reasons,'status':'AUDITED','anchor_freedom':len(anchor),'legal_count':len(legal),'reasons':reasons})
    for family in range(8): selected.extend([r['case_id'] for r in observations if r['family']==family and r['eligible']][:2])
    summary=load(source/'audit/summary.json');actual=load(source/'comparison-prepared/inputs.json')['rows']
    assert summary['selected']==selected==[r['id'] for r in actual]
    assert actual==[r for rid in selected for r in rows if r['id']==rid]
    assert dict(statuses)==summary['statuses'] and dict(strata)==summary['strata']
    assert sum(x['eligible'] for x in observations)==summary['eligible']==36
    result={'source':SOURCE,'pool':64,'literal_geometry_layout_rows':64,'status':dict(statuses),'compiler_issues':dict(issues),'valid_anchor_strata':dict(strata),'eligible':36,'selected':selected,'selected_density':dict(Counter(r['density'] for r in actual)),'child_transitions':child_count,'rows':observations,'reused_prior_audits':7,'amendment_prepare_AST_unchanged':True,'reconstructed_original_source_hash':digest(original),'original_capture_limit':'Original pre-amendment source bytes were reconstructed later by producer; hash matches frozen specification, not a contemporaneous capture claim.','independent_seconds':time.perf_counter()-began}
    output.mkdir(parents=True,exist_ok=True);(output/'admission.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--phase',choices=['packet','admission'],default='packet');a=ap.parse_args()
    result=(verify_packet if a.phase=='packet' else verify_admission)(a.source,a.output);print(json.dumps({k:v for k,v in result.items() if k not in ['games','rows']},indent=2))
if __name__=='__main__': main()
