"""Forward portrait of saved Leaper games. No new Player decisions."""
from __future__ import annotations
import argparse,json,random,time
from collections import Counter,defaultdict
from pathlib import Path
from scripts.leaper_design import load,write_record,record_value,compile_rule,ruleset_from_dict,GameSession,state_sha,match_action,legal_successors

def role_summary(planned, role):
    cells=[x for x in planned if x['role']==role]
    if not cells:return {'planned':0,'utility_bounds':None,'mean':None}
    bounds=[sum(x['utility'][i] for x in cells)/len(cells) for i in (0,1)]
    return {'planned':len(cells),'utility_bounds':bounds,
            'mean':bounds[0] if bounds[0]==bounds[1] else None}

def analyze(d):
    tick=time.perf_counter();r=load(d/('recovered-results.json' if (d/'recovered-results.json').exists() else 'results.json'));assert r['status']=='CLOSED'
    inputs=load(d/'inputs.json');rows=[];summ=[]
    for slot in r['slots']:
        if slot['status']!='finished':continue
        row=load(d/slot['receipt']);c=compile_rule(ruleset_from_dict(inputs['worlds'][slot['world']]['rule']));s=GameSession(c)
        captures={0:[],1:[]};counts=[];positions=set();states=set();depths=Counter();reasons=Counter();sources=Counter();nodes=qnodes=0;win_available=win_chosen=0;danger_chosen=safe_available=0;ab_roots=0;diag_seconds=0.0
        for q in row['queries']:
            assert q['state_sha256']==state_sha(s.state);states.add(q['state_sha256'])
            physical=tuple((p.owner,p.base_type_id,p.current_type_id,p.promoted) if p else None for p in s.state.position.board)+(s.state.position.side_to_move,);positions.add(physical)
            count=lambda st:sum(p is not None and p.current_type_id!='K' for p in st.position.board)
            before=count(s.state);action=match_action(s,q['action']);a=s.state.position.side_to_move
            if 'decision' in q:
                ab_roots+=1;dec=q['decision'];depths[str(dec['completed_depth'])]+=1;reasons[dec['termination_reason']]+=1;sources[dec.get('result_source','unspecified')]+=1;nodes+=dec['nodes'];qnodes+=dec['qnodes']
                # Complete root children only. Nonwinning children are NOT WDL labels.
                dt=time.perf_counter();children=list(legal_successors(s.state,c));winning=[ac for ac,ch in children if ch.terminal_status.is_terminal and ch.terminal_status.winner==a]
                if winning:
                    win_available+=1;win_chosen+=action in winning
                # One-ply opponent reply witnesses; a safe child is not a forced draw/win.
                dangerous=[];safe=[]
                for ac,ch in children:
                    if ch.terminal_status.is_terminal:bad=ch.terminal_status.winner==1-a
                    else:bad=any(gc.terminal_status.is_terminal and gc.terminal_status.winner==1-a for _,gc in legal_successors(ch,c))
                    (dangerous if bad else safe).append(ac)
                if action in dangerous:danger_chosen+=1;safe_available+=bool(safe)
                diag_seconds+=time.perf_counter()-dt
            s.submit(action);after=count(s.state)
            if after<before:captures[a].append(s.state.ply_count)
            counts.append({'ply':s.state.ply_count,'ordinary_count':after,'signed_count_actor0':sum((1 if p.owner==0 else -1) for p in s.state.position.board if p and p.current_type_id!='K')})
        assert record_value(s.state)==row['final_state']
        rows.append({'slot':slot['slot'],'world':slot['world'],'pair':slot['pair'],'role':slot['role'],'repeat':slot['repeat'],'terminal':row['terminal'],'utility':row['utility'],
            'plies':s.state.ply_count,'queries':len(row['queries']),'legal_counts':[q['legal_count'] for q in row['queries']],
            'unique_physical_positions':len(positions),'unique_full_states':len(states),'full_state_count':len(row['queries']),
            'first_capture_ply':min((p for values in captures.values() for p in values),default=None),'captures_by_actor':captures,
            'counts_at_16_32_64_128':[v for v in counts if v['ply'] in (16,32,64,128)],
            'AB_roots':ab_roots,'AB_nodes':nodes,'AB_qnodes':qnodes,'AB_completed_depths':dict(depths),'AB_stop_reasons':dict(reasons),'AB_sources':dict(sources),
            'AB_immediate_win_available':win_available,'AB_immediate_win_chosen':win_chosen,'AB_danger_chosen':danger_chosen,'AB_danger_despite_safe_child':safe_available,
            'root_reply_diagnostic_seconds':diag_seconds,'policy_seconds':sum(q['seconds'] for q in row['queries'])})
    for w in range(len(inputs['worlds'])):
        for pair in r.get('registration',load(d/'registration.json'))['pairs']:
            members=[x for x in rows if x['world']==w and x['pair']==pair];planned=[x for x in r['slots'] if x['world']==w and x['pair']==pair]
            terms=Counter(x['terminal']['status'] for x in members);known=Counter(x['utility'][0] for x in members if x['utility'][0]==x['utility'][1]);n=len(planned)
            low=sum(x['utility'][0] for x in planned)/n;high=sum(x['utility'][1] for x in planned)/n
            summ.append({'world':w,'masks':inputs['worlds'][w]['masks'],'pair':pair,'planned':n,'retained':len(members),'signed_utility_bounds':[low,high],'known_outcomes':dict(known),'terminals':dict(terms),'role_means':{str(a):role_summary(planned,a)['mean'] for a in (0,1)},'role_utility':{str(a):role_summary(planned,a) for a in (0,1)}})
    out={'status':'CLOSED','rows':rows,'summary':summ,'seconds':time.perf_counter()-tick,
         'scope':'Metadata-selected fixed-opening pilot. Full state/physical-position counts distinguish repetition, not independent sample sizes. Exact immediate-win and immediate-reply witnesses use shared Core, not full WDL. No population CI, game-quality scalar, training gate or default.'}
    write_record(d/'portrait.json',out);print('PORTRAIT',len(rows),out['seconds'],flush=True)
def verify_packet(packet):
    """Replay a published technical packet without writing/unpacking source paths."""
    import gzip,hashlib
    from generic_chess.session.serialization import deserialize_game_record
    tick=time.perf_counter();blob=packet.read_bytes();data=json.loads(gzip.decompress(blob));games=plies=pvs=returns=rng_checks=floor_checks=0
    for item in data['games']:
        raw=item['game'];c=compile_rule(ruleset_from_dict(item['rule']));s=GameSession.replay(c,deserialize_game_record(json.dumps(raw['initial_record'])))
        streams={int(a):random.Random(v) for a,v in raw['rng_seeds'].items()}
        for q in raw['queries']:
            returns+=1;assert q['state_sha256']==state_sha(s.state)
            if q['action'] is None:
                assert q is raw['queries'][-1] and raw['censor']=='no_action';continue
            a=match_action(s,q['action']);actor=s.state.position.side_to_move;assert actor==q['actor'];legal=s.legal_actions();assert len(legal)==q['legal_count']
            if q['policy']=='RNG':
                assert a==legal[streams[actor].randrange(len(legal))];rng_checks+=1
            if q['policy']=='FLOOR':
                children=list(legal_successors(s.state,c));wins=[v for v,ch in children if ch.terminal_status.is_terminal and ch.terminal_status.winner==actor]
                expected=wins[0] if wins else children[streams[actor].randrange(len(children))][0]
                assert a==expected;floor_checks+=1
            if 'decision' in q:
                probe=GameSession.replay(c,s.to_record())
                for v in q['decision']['principal_variation']:probe.submit(match_action(probe,v));pvs+=1
            s.submit(a);plies+=1
        assert record_value(s.to_record())==raw['final_record'];assert record_value(s.state)==raw['final_state'];assert record_value(s.result)==raw['terminal']
        from scripts.leaper_design import outcome_value
        value=outcome_value(s.result,raw['role'],raw['censor']);assert raw['utility']==([value,value] if value is not None else [-1,1]);games+=1
    out={'status':'PASS','games':games,'history_plies':plies,'controller_turn_receipts':returns,'AB_returns':sum('decision' in q for item in data['games'] for q in item['game']['queries']),'literal_PV_edges':pvs,'RNG_stream_checks':rng_checks,'FLOOR_policy_checks':floor_checks,'compressed_sha256':hashlib.sha256(blob).hexdigest(),'seconds':time.perf_counter()-tick,'scope':'Shared production Core and strict serialization. Not independent engine/game-WDL oracle; scientific inference and source/privacy review remain separate.'}
    print(json.dumps(out),flush=True);return out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--packet',type=Path);p.add_argument('--receipt',type=Path);a=p.parse_args()
    if a.packet:
        result=verify_packet(a.packet)
        if a.receipt:write_record(a.receipt,result)
    elif a.output:analyze(a.output)
    else:p.error('supply --output for saved-run portrait or --packet for read-only packet verification')
