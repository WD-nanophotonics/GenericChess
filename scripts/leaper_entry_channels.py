"""Complete n3 fresh one-ply entry channels for one A22->A23/B5 pair."""
from pathlib import Path
from dataclasses import replace
from itertools import permutations
from collections import Counter
from datetime import datetime,timezone
import argparse,json,time
from scripts import leaper_design as L
from scripts.leaper_entry_initialization_law import fresh_rule
from scripts.leaper_delayed_capture_witness import snapshot
from scripts.leaper_rule_coordinates import physical_action
from generic_chess.core.attacks import is_in_check
from generic_chess.core.movegen import legal_actions_from_position
from tools.local_agent.common import write_json
from tools.local_agent import session


def candidates():
    aa=set(L.offsets(23));bb=set(L.offsets(5))
    for k,a,v,b in permutations(range(9),4):
        if max(abs(k%3-v%3),abs(k//3-v//3))<=1:continue
        if(v%3-a%3,v//3-a//3)in aa:continue
        if(k%3-b%3,k//3-b//3)in bb:continue
        yield[k,a,v,b]


def measure(existing,output):
    tick=time.perf_counter();started=datetime.now(timezone.utc).isoformat()
    write_json(output/'registration.json',dict(started_at=started,source_sha256=L.sha(Path(__file__)),
        n=3,pair=[22,23],B_mask=5,existing_return_sha256=L.sha(existing),cap_seconds=600,
        missing='UNKNOWN if interrupted; no refill or extension'))
    old=L.load(existing);reuse={(r['mask'],json.dumps(r['rule'],sort_keys=True),json.dumps(r['shared_action'],sort_keys=True)):r for r in old['rows']if r['B_present']}
    rows=[];new_apply=0;reuse_count=0;static_count=0
    for index,cells in enumerate(candidates()):
        if index%16==0 and(session.stopped()or time.perf_counter()-tick>=600):raise RuntimeError('frozen stop/cap')
        pair=[];compiled={};root_sessions={}
        for mask in(22,23):
            rule=fresh_rule(3,mask,cells);c=L.compile_rule(rule);s=L.GameSession(c)
            rawrule=L.ruleset_to_dict(rule,include_metadata=True)
            compiled[mask]=c;root_sessions[mask]=s
            branches=[]
            for a in s.legal_actions():
                raw=L.record_value(a);key=physical_action(raw,3)
                cache_key=(mask,json.dumps(rawrule,sort_keys=True),json.dumps(raw,sort_keys=True))
                if cache_key in reuse:
                    assert reuse[cache_key]['initial']==snapshot(s)
                    child=reuse[cache_key]['after'];source='REUSED exact parity-boundary action return';reuse_count+=1
                else:
                    z=L.GameSession.replay(c,s.to_record());z.submit(a);child=snapshot(z)
                    source='NEW literal Core child';new_apply+=1
                branches.append(dict(action_key=list(key),action=raw,child=child,source=source))
            pair.append(dict(mask=mask,rule=rawrule,root=snapshot(s),branches=branches))
        lower={tuple(x['action_key']):x for x in pair[0]['branches']}
        wins=[]
        for high in pair[1]['branches']:
            result=high['child']['result']
            if result['winner']!=0:continue
            key=tuple(high['action_key']);shared=key in lower
            oldstatic=None
            if not shared:
                rawboard=high['child']['state']['position']['board']
                board=tuple(None if p is None else L.Piece(p['owner'],p['base_type_id'],p['current_type_id'])for p in rawboard)
                p=replace(root_sessions[22].state.position,board=board,side_to_move=1)
                checked=is_in_check(p,1,compiled[22]);acts=legal_actions_from_position(p,compiled[22]);static_count+=1
                oldstatic=dict(position=L.record_value(p),checked=checked,legal_actions=L.record_value(acts),
                               static_mate=checked and not acts,
                               scope='Counterfactual static Position ONLY; old action illegal, no old legal GameRecord or old WDL claimed.')
            category=('shared_terminal_change'if shared else'new_entry_into_old_static_mate'if oldstatic['static_mate']else'new_action_into_old_nonmate')
            destination=high['action']['to_square'];p=pair[1]['root']['state']['position']['board'][destination['rank']*3+destination['file']]
            wins.append(dict(action_key=high['action_key'],category=category,shared=shared,
                             old_shared_child=lower[key]['child']if shared else None,old_static_post=oldstatic,
                             capture_target=None if p is None else p['current_type_id']))
        rows.append(dict(placement=cells,pair=pair,immediate_mating_actions=wins))
        write_json(output/'latest-raw-root.json',rows[-1])
    return dict(started_at=started,ended_at=datetime.now(timezone.utc).isoformat(),seconds=time.perf_counter()-tick,
                rows=rows,new_literal_Core_child_applications=new_apply,reused_exact_child_returns=reuse_count,
                new_illegal_old_action_static_frontiers=static_count,
                new_Player_queries=0,new_graph_or_solver_calls=0)


def qualify(m):
    assert {tuple(r['placement'])for r in m['rows']}==set(map(tuple,candidates()))
    assert len(m['rows'])==len({tuple(r['placement'])for r in m['rows']})
    counts=Counter();roots=0
    for row in m['rows']:
        lo,hi=row['pair'];assert [lo['mask'],hi['mask']]==[22,23]
        assert lo['root']['state']['position']['board']==hi['root']['state']['position']['board']
        for frame in(lo,hi):
            expected_keys={physical_action(a,3)for a in frame['root']['legal_actions']}
            actual_keys={tuple(c['action_key'])for c in frame['branches']}
            assert len(frame['branches'])==len(expected_keys)and actual_keys==expected_keys, 'complete legal root frontier required'
            assert frame['root']['record']['actions']==[]and frame['root']['state']['ply_count']==0
            for child in frame['branches']:
                assert physical_action(child['action'],3)==tuple(child['action_key'])
                rec=L.deserialize_game_record(json.dumps(child['child']['record']))
                assert len(rec.actions)==1 and physical_action(L.record_value(rec.actions[0]),3)==tuple(child['action_key'])
        low={tuple(c['action_key']):c for c in lo['branches']};high={tuple(c['action_key']):c for c in hi['branches']}
        measured_wins={k for k,c in high.items()if c['child']['result']['winner']==0}
        summarized={tuple(w['action_key'])for w in row['immediate_mating_actions']}
        assert summarized==measured_wins and len(row['immediate_mating_actions'])==len(measured_wins), 'complete measured winning-action summary required'
        assert low.keys()<=high.keys()
        for k in low:assert low[k]['child']['state']['position']['board']==high[k]['child']['state']['position']['board']
        if row['immediate_mating_actions']:roots+=1
        for w in row['immediate_mating_actions']:
            counts[w['category']]+=1
            assert high[tuple(w['action_key'])]['child']['result']['status']=='checkmate'
            key=tuple(w['action_key'])
            assert w['shared']==(key in low)
            if w['shared']:
                assert w['category']=='shared_terminal_change'
                assert w['old_shared_child']==low[key]['child']and w['old_static_post']is None
                assert w['old_shared_child']['result']['winner']is None
            else:
                assert w['old_shared_child']is None, 'illegal old action cannot have a legal GameRecord'
                assert w['old_static_post']is not None and 'record'not in w['old_static_post'], 'illegal old action has static Position only'
                assert w['category']==('new_entry_into_old_static_mate'if w['old_static_post']['static_mate']else'new_action_into_old_nonmate')
    named=[((5,8,3,0),('A',8,4,None),'shared_terminal_change'),
           ((2,7,0,3),('A',7,8,None),'new_entry_into_old_static_mate')]
    for cells,key,category in named:
        row=next(r for r in m['rows']if tuple(r['placement'])==cells)
        assert any(tuple(w['action_key'])==key and w['category']==category for w in row['immediate_mating_actions'])
    return dict(status='PASS',common_safe_fresh_initializers=len(m['rows']),immediate_mate_roots=roots,
                immediate_mating_action_channels=dict(counts),new_literal_Core_child_applications=m['new_literal_Core_child_applications'],
                reused_exact_child_returns=m['reused_exact_child_returns'],new_illegal_old_action_static_frontiers=m['new_illegal_old_action_static_frontiers'],
                scope='All positive and negative fresh roots retained. One-ply terminal regions, not full WDL or fork labels; new pairmu is distinct from earlier A6/A22 denominator360. Static old post on illegal action never receives an old GameRecord.',
                new_Player_queries=0,new_graph_or_solver_calls=0)



def symmetry_analysis(m):
    by={tuple(r['placement']):r for r in m['rows']}
    mappings=[]
    for reflected in(False,True):
        for turns in range(4):
            perm=[]
            for sq in range(9):
                x,y=sq%3,sq//3
                if reflected:x=2-x
                for _ in range(turns):x,y=2-y,x
                perm.append(y*3+x)
            mappings.append(perm)
    def keymap(key,perm):return(key[0],perm[key[1]],perm[key[2]],key[3])
    def boardmap(board,perm):
        out=[None]*9
        for sq,piece in enumerate(board):out[perm[sq]]=piece
        return out
    classes={};root_checks=0;child_checks=0;channel_checks=0
    for cells,row in by.items():
        images={tuple(perm[sq]for sq in cells)for perm in mappings}
        canonical=min(images)
        classes.setdefault(canonical,set()).update(images)
        assert images<=by.keys()
        for perm in mappings:
            other=by[tuple(perm[sq]for sq in cells)]
            for frame,target in zip(row['pair'],other['pair']):
                assert frame['mask']==target['mask']
                assert boardmap(frame['root']['state']['position']['board'],perm)==target['root']['state']['position']['board']
                a={keymap(tuple(c['action_key']),perm):c for c in frame['branches']}
                b={tuple(c['action_key']):c for c in target['branches']}
                assert a.keys()==b.keys();root_checks+=1
                for k,node in a.items():
                    child=node['child'];new=b[k]['child']
                    assert boardmap(child['state']['position']['board'],perm)==new['state']['position']['board']
                    assert child['result']==new['result']
                    assert child['check']==new['check']
                    child_checks+=1
            src={keymap(tuple(w['action_key']),perm):(w['category'],w['capture_target'])for w in row['immediate_mating_actions']}
            dst={tuple(w['action_key']):(w['category'],w['capture_target'])for w in other['immediate_mating_actions']}
            assert src==dst;channel_checks+=len(src)
    orbit_rows=[]
    for representative,members in sorted(classes.items()):
        flags={bool(by[cell]['immediate_mating_actions'])for cell in members}
        assert len(flags)==1
        orbit_rows.append(dict(representative=list(representative),members=[list(c)for c in sorted(members)],
                               immediate_mate=flags.pop()))
    assert len(orbit_rows)==19 and all(len(r['members'])==8 for r in orbit_rows)
    assert sum(r['immediate_mate']for r in orbit_rows)==14
    return dict(status='PASS',physical_roots=152,geometric_D4_orbits=19,orbit_sizes={'8':19},
                immediate_mate_orbits=14,negative_orbits=5,exact_physical_mu_mate_fraction='14/19 = 112/152',
                root_frame_transform_checks=root_checks,child_board_terminal_transform_checks=child_checks,
                mating_action_channel_transform_checks=channel_checks,orbits=orbit_rows,
                interpretation='Complete deterministic semantic census, not152or19 independent statistical experiments. D4permutes selected physical initializers; named setup IDs/fingerprints and Player/search/timing behavior are not asserted invariant.',
                new_Core_calls=0,new_Player_queries=0,new_graph_or_solver_calls=0)



def capture_obstruction(reg,parent,named,output):
    from datetime import timedelta
    plan=L.load(Path('.local_agent/ag-negative-obstruction-plan.json'))
    deadline=datetime.fromisoformat(plan['started_at'])+timedelta(seconds=180)
    if datetime.now(timezone.utc)>=deadline:raise RuntimeError('original180sphasecap')
    started=datetime.now(timezone.utc).isoformat();tick=time.perf_counter()
    write_json(output/'registration.json',dict(started_at=started,source_sha256=L.sha(Path(__file__)),
        original_phase_deadline=deadline.isoformat(),fixed_rule=reg['fixed_rules']['23']))
    c=L.compile_rule(L.ruleset_from_dict(reg['fixed_rules']['23']))
    negatives={tuple(r['placement'])for r in parent['rows']if not r['immediate_mating_actions']}
    roots=[]
    for row in named['rows']:
        if tuple(row['placement'])not in negatives:continue
        if datetime.now(timezone.utc)>=deadline:raise RuntimeError('original180sphasecap')
        frame=next(x for x in row['frames']if x['mask']==23);clauses=[]
        for child in frame['children']:
            node=child['node'];clause=dict(white_action=child['action_key'],white_child=node)
            if node['result']['status']!='ongoing':
                clause['kind']='terminal_nonWhiteWIN'
            else:
                board=node['state']['position']['board'];targets=[i for i,p in enumerate(board)if p and p['owner']==0 and p['current_type_id']=='A']
                assert len(targets)==1;target=targets[0]
                replies=[a for a in node['legal_actions']if a['to_square']['rank']*3+a['to_square']['file']==target]
                if not replies:clause['kind']='unresolved_no_captureA_reply'
                else:
                    raw=min(replies,key=lambda a:physical_action(a,3))
                    z=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(node['record'])))
                    z.submit(L.match_action(z,raw))
                    clause.update(kind='verified_captureA',black_reply=raw,capture_after=snapshot(z))
            clauses.append(clause)
        roots.append(dict(key=row['key'],placement=row['placement'],root=frame['root'],clauses=clauses,
                          proof_complete=all(x['kind']!='unresolved_no_captureA_reply'for x in clauses)))
        write_json(output/'latest-raw-root.json',roots[-1])
    m=dict(started_at=started,ended_at=datetime.now(timezone.utc).isoformat(),seconds=time.perf_counter()-tick,
           roots=roots,new_Player_queries=0,new_graph_or_solver_calls=0)
    write_json(output/'measurements.json',m);q=qualify_obstruction(m,parent,named)
    write_json(output/'qualification.json',q);print(json.dumps(q))


def qualify_obstruction(m,parent,named):
    negatives={tuple(r['placement'])for r in parent['rows']if not r['immediate_mating_actions']}
    assert {tuple(r['placement'])for r in m['roots']}==negatives and len(m['roots'])==40
    frames={tuple(r['placement']):next(x for x in r['frames']if x['mask']==23)for r in named['rows']}
    captures=0;unresolved=0;closed=0
    for row in m['roots']:
        source=frames[tuple(row['placement'])]
        assert row['root']==source['root']
        expected={tuple(x['action_key']):x['node']for x in source['children']}
        assert {tuple(x['white_action'])for x in row['clauses']}==set(expected)and len(row['clauses'])==len(expected)
        for clause in row['clauses']:
            node=clause['white_child'];assert node==expected[tuple(clause['white_action'])]
            if clause['kind']=='verified_captureA':
                raw=clause['black_reply'];assert raw in node['legal_actions']
                after=clause['capture_after']
                before_record=L.deserialize_game_record(json.dumps(node['record']))
                after_record=L.deserialize_game_record(json.dumps(after['record']))
                assert after_record.ruleset_fingerprint==before_record.ruleset_fingerprint and after_record.initial_setup_key==before_record.initial_setup_key, 'capture certificate prefix identity mismatch'
                assert after_record.actions[:-1]==before_record.actions and L.record_value(after_record.actions[-1])==raw, 'capture certificate prefix/action mismatch'
                assert after['state']['ply_count']==node['state']['ply_count']+1
                pieces=[p for p in after['state']['position']['board']if p and p['owner']==0]
                assert len(pieces)==1 and pieces[0]['current_type_id']=='K'
                assert after['result']['winner']!=0
                captures+=1
            elif clause['kind']=='terminal_nonWhiteWIN':
                assert node['result']['status']!='ongoing'and node['result']['winner']!=0
            else:
                assert clause['kind']=='unresolved_no_captureA_reply';unresolved+=1
        complete=all(x['kind']!='unresolved_no_captureA_reply'for x in row['clauses'])
        assert complete==row['proof_complete'];closed+=complete
    return dict(status='PASS',negative_roots=40,certified_NOT_White_WIN=closed,unresolved_roots=40-closed,
                verified_captureA_responses=captures,unresolved_white_actions=unresolved,
                complete_mu_WIN_count_interval=[112,152-closed],
                conclusion='Closed roots are NOT-WIN, never imputed DRAW. Remaining full rootWDL UNKNOWN. The bareWhiteKing cannot win under exactly these remove/no-drop/no-promotion/draw-ending rules.',
                scope='Local all-White-action response obstruction; no gamegraph, solver, Player, default or learner gate.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--reuse',type=Path);p.add_argument('--symmetry-file',type=Path);p.add_argument('--obstruction-reg',type=Path);p.add_argument('--obstruction-parent',type=Path);p.add_argument('--obstruction-named',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('NEW output required')
    a.output.mkdir(parents=True)
    if a.obstruction_reg:
        capture_obstruction(L.load(a.obstruction_reg),L.load(a.obstruction_parent),L.load(a.obstruction_named),a.output);return
    if a.symmetry_file:
        q=symmetry_analysis(L.load(a.symmetry_file));write_json(a.output/'qualification.json',q)
        print(json.dumps({k:v for k,v in q.items()if k!='orbits'}));return
    if not a.reuse:p.error('--reuse required for new measurements')
    m=measure(a.reuse,a.output);write_json(a.output/'measurements.json',m)
    q=qualify(m);write_json(a.output/'qualification.json',q);print(json.dumps(q))


if __name__=='__main__':main()
