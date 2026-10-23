"""Read and qualify retained component path/forward evidence without Player calls."""
from __future__ import annotations
import argparse,json,random,time,math
from collections import Counter,defaultdict
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_component_forward import POLICIES
from tools.local_agent.common import write_json


def qualify_game(world,row):
    c=L.compile_rule(L.ruleset_from_dict(world['rule']))
    s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(world['roots'][0]['record'])))
    assert L.record_value(s.to_record())==row['initial_record']
    assert row['policy'] in POLICIES
    rng={0:random.Random(row['seed']),1:random.Random(row['seed']+1)}
    counts=Counter();stop=Counter();depth=Counter();lost_at=None;elapsed=0
    for q in row['queries']:
        assert q['actor']==s.state.position.side_to_move and q['root_ply']==s.state.ply_count
        assert q['state_sha256']==L.state_sha(s.state)
        legal=s.legal_actions();assert q['legal_count']==len(legal)
        action=L.match_action(s,q['action']);side=q['actor'];counts['actions']+=1
        if side==1:
            assert q['policy']=='RNG' and action==legal[rng[1].randrange(len(legal))];counts['RNG_choices']+=1
        elif row['policy']=='FLOOR':
            expected,detail=L.floor(s,rng[0]);assert action==expected and q['floor']==detail;counts['FLOOR_choices']+=1
        else:
            d=q['decision'];assert q['policy']==row['policy'] and q['node_budget']==POLICIES[row['policy']]
            assert q['requested_depth']==64 and d['action']==q['action']
            assert d['qnodes']==0
            if d['termination_reason']=='root_immediate_win':
                assert d['result_ordinary_qdepth'] is None and d['completed_depth']==0
                from generic_chess.core.transition import apply_action
                literal=apply_action(s.state,action,c)
                assert literal.terminal_status.is_terminal and literal.terminal_status.winner==side
            else:assert d['result_ordinary_qdepth']==0
            assert d['runtime_depth_balanced'] and d['native_legality_operational_failures']==0
            pv=L.GameSession.replay(c,s.to_record())
            for raw in d['principal_variation']:
                pv.submit(L.match_action(pv,raw));counts['PV_plies']+=1
            counts['Player_queries']+=1
            for field in ('nodes','qnodes','native_legality_calls','native_legality_fallbacks','runtime_pushes','runtime_pops'):
                counts[field]+=d[field]
            stop[d['termination_reason']]+=1;depth[str(d['completed_depth'])]+=1
        elapsed+=q['seconds'];s.submit(action)
        aa=sum(p is not None and p.owner==0 and p.current_type_id=='A' for p in s.state.position.board)
        if lost_at is None and aa<2:lost_at=s.state.ply_count
    assert L.record_value(s.to_record())==row['final_record']
    assert L.record_value(s.state)==row['final_state'] and L.record_value(s.result)==row['terminal']
    value=None if row['censor'] or not s.state.terminal_status.is_terminal else 0 if s.result.winner is None else 1 if s.result.winner==0 else -1
    assert value==row['value']
    assert row['status']=='CLOSED' and row['seconds']>=elapsed
    return dict(counts=dict(counts),termination_counts=dict(stop),depth_counts=dict(depth),plies=s.state.ply_count,first_ordinary_loss_ply=lost_at,query_seconds=elapsed,outer_seconds=row['seconds'],value=value,terminal=row['terminal']['status'])


def analyze(reg,world,results,read_row):
    tick=time.perf_counter();assert results['status']=='CLOSED'
    assert len(results['slots'])==len(reg['seeds'])*len(reg['policies'])==reg['planned_games']
    expected={(seed,p)for seed in reg['seeds']for p in reg['policies']};assert {(x['seed'],x['policy'])for x in results['slots']}==expected
    seen=defaultdict(dict);rows=[];totals=Counter()
    for i,slot in enumerate(results['slots']):
        if slot['status']!='finished':continue
        row=read_row(slot['receipt']);assert row['seed']==slot['seed'] and row['policy']==slot['policy'] and row['value']==slot['value']
        q=qualify_game(world,row);rows.append(dict(slot=i,seed=row['seed'],policy=row['policy'],**q));totals.update(q['counts']);seen[row['seed']][row['policy']]=row['value']
        if len(rows)%20==0:print('QUALIFY',len(rows),flush=True)
    summaries={}
    for p in reg['policies']:
        group=[r for r in rows if r['policy']==p];values=[r['value']for r in group if r['value'] is not None];missing=len(reg['seeds'])-len(values)
        summaries[p]=dict(planned=len(reg['seeds']),literal_outcomes=dict(Counter(r['terminal']for r in group)),observed_values=dict(Counter(map(str,values))),missing=missing,mean_bounds=[(sum(values)-missing)/len(reg['seeds']),(sum(values)+missing)/len(reg['seeds'])],total_game_seconds=sum(r['outer_seconds']for r in group),total_query_seconds=sum(r['query_seconds']for r in group),ordinary_lost_games=sum(r['first_ordinary_loss_ply']is not None for r in group),total_nodes=sum(r['counts'].get('nodes',0)for r in group),total_plies=sum(r['plies']for r in group))
    paired={}
    for a,b in [('UNIT65536','UNIT512'),('UNIT512','FLOOR'),('UNIT65536','FLOOR')]:
        vals=[v[a]-v[b]for v in seen.values()if a in v and b in v and v[a]is not None and v[b]is not None];missing=len(reg['seeds'])-len(vals)
        paired[a+'-'+b]=dict(observed_pairs=len(vals),difference_histogram=dict(Counter(map(str,vals))),mean_bounds=[(sum(vals)-2*missing)/len(reg['seeds']),(sum(vals)+2*missing)/len(reg['seeds'])],interpretation='Finite seed panel; random streams match by seed but paths diverge. Not a forced-WDL or iid-rule effect.')
    out=dict(status='PASS',games=len(rows),planned=reg['planned_games'],totals=dict(totals),summary=summaries,paired=paired,rows=rows,seconds=time.perf_counter()-tick,scope='Zero new Player queries. Literal Core/RNG/FLOOR/PV replay, shared execution authority not independent engine. No source capsule execution or WDL inference.')
    return out

def qualify(directory,inputs,registration,output):
    reg=L.load(registration);assert L.sha(inputs)==reg['input_sha256']
    out=analyze(reg,L.load(inputs)['worlds'][1],L.load(directory/'results.json'),lambda name:L.load(directory/name))
    write_json(output,out);return out

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);ap.add_argument('--input',type=Path,required=True);ap.add_argument('--registration',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();r=qualify(a.directory,a.input,a.registration,a.output);print(json.dumps({k:v for k,v in r.items()if k!='rows'}))
