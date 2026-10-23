"""AUX exact truth on PRIMARY's frozen admitted H6 initial-layout support.

All physical transitions come from committed public Core. Cooperative distance
is certified on a complete finite domain; history minimax keeps remaining plies
and EVERY previously visited vertex for the explicitly admitted repeat2 rule.
No rule sampling, Player, training or policy campaign is performed.
"""
from __future__ import annotations
from collections import Counter,deque
from dataclasses import replace
from functools import lru_cache
import argparse,json,time,hashlib
from pathlib import Path

from generic_chess.core.transition import legal_successors
from generic_chess.core.actions import action_to_dict,action_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_h6_e0 import base_rule
from scripts.leaper_design import compile_rule,ruleset_from_dict,ruleset_to_dict,state_sha
from scripts.leaper_cooperative_truth import cooperative_distances
from scripts.leaper_cooperative_certificate import encode_position
from scripts.leaper_retrograde import fresh_state
from scripts.leaper_retrograde import attractor
from scripts.leaper_explorer_truth import load,save,digest
from scripts.leaper_microgames import role_stop_requested


class Cap(Exception):pass


def blocked_clock_attractor(edges,terminals,sides,blocked):
    """Scoped repeat2 history reduction; labels still need remaining clock.

    Only caller-admitted position-local moves, alternating turns, decisive
    static terminals and otherwise draw clocks/repetition are supported.
    `blocked` is the actual previous-position set INCLUDING the current root.
    Incoming nonterminal returns to it become draw; root outgoing edges remain.
    A mate arrival keeps Core precedence. This is never a GameState TT key.
    """
    if len(edges)!=len(sides)or any(s not in(0,1)for s in sides):raise ValueError('invalid turn domain')
    if any(not 0<=i<len(edges)for i in blocked):raise ValueError('blocked index outside domain')
    draw=len(edges);modified=[]
    for i,children in enumerate(edges):
        if any(not 0<=j<len(edges)or sides[j]!=1-sides[i]for j in children):raise ValueError('nonalternating/out-of-domain edge')
        modified.append(tuple(draw if j in blocked and j not in terminals else j for j in children))
    modified.append(())
    relative={i:0 if winner is None else 1 if winner==sides[i]else-1 for i,winner in terminals.items()}
    values,ranks=attractor(modified,relative|{draw:0})
    def value(i,remaining,*,arriving=False):
        if type(remaining)is not int or remaining<0:raise ValueError('invalid remaining clock')
        if arriving and i in blocked and i not in terminals:return 0
        v=values[i]
        relative=v if v and ranks[i]<=remaining else 0
        return relative if sides[i]==0 else-relative
    return value,values,ranks,modified


def admit(family,row):
    rule=ruleset_from_dict(family['rule']);template=base_rule(*family['masks'],row['placement'])
    normalized=replace(rule,initial_position=template.initial_position,initial_setup_options=())
    if ruleset_to_dict(normalized,include_metadata=True)!=ruleset_to_dict(template,include_metadata=True):
        raise ValueError('full generated H6 rule differs from admitted template')
    c=compile_rule(rule)
    if c.ruleset_fingerprint!=family['fingerprint']:raise ValueError('family fingerprint mismatch')
    return c


def history_solver(edges,terminals,sides,guard,*,cache_entries=200000,max_calls=2000000):
    calls=0
    @lru_cache(maxsize=cache_entries)
    def solve(vertex,remaining,visited):
        nonlocal calls
        if calls>=max_calls:raise Cap('HISTORY_CALL_CAP_UNKNOWN')
        calls+=1
        if calls%1024==0:guard(calls)
        # Actual Core mate/stalemate precedence precedes clock/repetition.
        if vertex in terminals:
            winner=terminals[vertex];value=0 if winner is None else 1 if winner==0 else-1
            return value,1<<(value+1)
        if remaining==0 or vertex in visited:return 0,2
        new=tuple(sorted((*visited,vertex)))
        children=[solve(j,remaining-1,new)for j in edges[vertex]]
        if not children:raise ValueError('ongoing graph vertex without legal action')
        value=(max if sides[vertex]==0 else min)(v for v,outcomes in children)
        outcomes=0
        for v,bits in children:outcomes|=bits
        return value,outcomes
    return solve,lambda:calls


def solve_family(family,source_rows,plan,whole_start):
    start=time.perf_counter();stats=Counter();complete=False
    def guard(calls=0):
        if role_stop_requested():raise Cap('USER_STOP')
        if time.perf_counter()-whole_start>=plan['whole_cap_seconds']:raise Cap('WHOLE_CAP_UNKNOWN')
        if time.perf_counter()-start>=plan['family_cap_seconds']:raise Cap('FAMILY_CAP_UNKNOWN')
        if calls>=plan['history_recursion_calls_per_family']:raise Cap('HISTORY_CALL_CAP_UNKNOWN')
    c=admit(family,source_rows[0]);positions=[];indices={};pending=deque();edges=[];actions=[];terms={};roots=[]
    def add(pos):
        if pos not in indices:
            if len(positions)>=plan['physical_vertices_per_family']:raise Cap('VERTEX_CAP_UNKNOWN')
            indices[pos]=len(positions);positions.append(pos);pending.append(pos);edges.append(None);actions.append(None)
        return indices[pos]
    for row in source_rows:
        s=GameSession.replay(c,deserialize_game_record(json.dumps(row['full_record'])))
        if (state_sha(s.state)!=row['state_sha256']or digest(row['full_state'])!=row['state_sha256']or
            s.state.ply_count!=0 or len(s.state.history)!=1 or
            len(s.state.repetition_counts)!=1 or s.state.repetition_counts[0][1]!=1 or
            s.state.terminal_status.is_terminal):raise ValueError('not exact fresh admitted H6 history')
        roots.append((row,s,add(s.state.position)))
    try:
        while pending:
            if stats['Core_vertices']%64==0:guard()
            pos=pending.popleft();i=indices[pos];s=fresh_state(pos,c)
            if s.terminal_status.is_terminal:
                terms[i]=s.terminal_status.winner;edges[i]=();actions[i]=()
            else:
                ee=[];aa=[]
                for a,ch in legal_successors(s,c):
                    ee.append(add(ch.position));aa.append(action_to_dict(a));stats['Core_edges']+=1
                if not ee:raise ValueError('ongoing Position has no successor')
                edges[i]=tuple(ee);actions[i]=tuple(aa)
            stats['Core_vertices']+=1
        complete=True
    except Cap as exc:
        return dict(family=family['family'],fingerprint=family['fingerprint'],status=str(exc),
            complete_domain=False,counts=dict(stats),pending=len(pending),rows=[],seconds=time.perf_counter()-start),None
    graph_seconds=time.perf_counter()-start
    decisive={i for i,winner in terms.items()if winner is not None}
    distances,nxt=cooperative_distances(edges,decisive)
    rows=[];path_edges=0
    # A shortest cooperative path has no repeated vertex. With a fresh prefix,
    # it therefore cannot trigger repeat2; actual Session replay still checks it.
    for source,s,index in roots:
        guard();positive=distances.get(index,7)<=6;witness=[];final_sha=None
        if positive:
            current=index
            while current not in decisive:
                j=nxt[current];offset=edges[current].index(j);action=actions[current][offset]
                witness.append(action);s.submit(action_from_dict(action));path_edges+=1
                if s.state.position!=positions[j]:raise ValueError('cooperative path target state differs')
                current=j
            if s.result.winner is None or len(witness)>6:raise ValueError('shortest path failed actual H6 terminal')
            final_sha=state_sha(s.state)
        rows.append(dict(id=source['state_sha256'],fingerprint=family['fingerprint'],
            family='H6:'+':'.join(map(str,family['masks'])),family_index=family['family'],split=family['split'],
            mu_id=digest(sorted(r['state_sha256']for r in source_rows)),record=source['full_record'],
            root_index=index,cooperative_decisive=positive,universal_draw=not positive,
            wdl_fork=None,wdl_bounds=[-1,1],action_bounds=[],
            shortest_decisive_distance=distances.get(index),cooperative_witness=witness,terminal_state_sha=final_sha))
    history_start=time.perf_counter();solver,calls=history_solver(edges,terms,[p.side_to_move for p in positions],guard,cache_entries=plan['memo_entries_per_family'],max_calls=plan['history_recursion_calls_per_family'])
    status='COMPLETE';completed=0
    try:
        for row,(source,root,index)in zip(rows,roots,strict=True):
            guard(calls());value,outcomes=solver(index,6,())
            branch=[]
            for a,j in zip(actions[index],edges[index],strict=True):
                v,bits=solver(j,5,(index,));branch.append(dict(action=a,wdl_bounds=[v,v],terminal_outcomes_bits=bits))
            if value!=max(b['wdl_bounds'][0]for b in branch):raise ValueError('H6 action/root mismatch')
            if bool(outcomes&5)!=row['cooperative_decisive']:raise ValueError('history solver/cooperative distance disagree')
            row.update(wdl_bounds=[value,value],wdl_fork=len({b['wdl_bounds'][0]for b in branch})>1,
                action_bounds=branch,terminal_outcomes_bits=outcomes)
            completed+=1
    except Cap as exc:status=str(exc)
    domain=dict(format='leaper-H6-closed-domain-v1',fingerprint=family['fingerprint'],
        positions=[encode_position(p,c.initial_position)for p in positions],edges=edges,actions=actions,
        terminals={str(i):winner for i,winner in terms.items()},
        negative_potential=[min(distances.get(i,7),7)for i in range(len(positions))],
        scope='All Core successors closed; potential0 at decisive terminals and p[i]<=1+p[j] on every edge. Fresh-root p>6 proves no decisive path inH6; shortestpositivepaths are separately actualSessionreplayed. Full visited sets used for WDL/forks.')
    return dict(family=family['family'],fingerprint=family['fingerprint'],masks=family['masks'],status=status,
        complete_domain=complete,counts=dict(stats),domain_digest=digest(domain),
        root_count=len(rows),history_roots_completed=completed,history_recursion_calls=calls(),
        memo=solver.cache_info()._asdict(),cooperative_path_edges=path_edges,
        cooperative_positive=sum(r['cooperative_decisive']for r in rows),
        fork_counts=dict(Counter(str(r['wdl_fork'])for r in rows)),
        graph_seconds=graph_seconds,history_seconds=time.perf_counter()-history_start,
        rows=rows,seconds=time.perf_counter()-start),domain


def run(input_path,plan_path,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False);source=load(input_path);plan=load(plan_path)
    start=time.perf_counter();families=[];allrows=[];rules={};unstarted=[]
    for family in source['families']:
        if family['status']=='MU_UNAVAILABLE':continue
        if time.perf_counter()-start>=plan['whole_cap_seconds']or role_stop_requested():unstarted.append(family['family']);continue
        rows=[r for r in source['rows']if r['family']==family['family']]
        result,domain=solve_family(family,rows,plan,start);families.append(result)
        save(output/f"family{family['family']}.json.gz",result)
        if domain is not None:save(output/f"domain{family['family']}.json.gz",domain)
        if result['rows']:
            allrows.extend(result['rows']);rules[family['fingerprint']]=family['rule']
        print(json.dumps({k:v for k,v in result.items()if k not in('rows',)}),flush=True)
    truth=dict(format='leaper-H6-initial-truth-v1',rules=rules,roots=allrows,
        source_digest=digest(source),mu='Exact PRIMARY admitted fresh initial support; no replacement for unavailablefamily0, no initially refused stalemate imputation.',
        scope='Finite H6/repeat2 exact visited-set history values on verified Core domains. Exposedmovementprimitives/12frozenfamilies, not populationcalibration/strength or old128plytruth.')
    save(output/'truth.json.gz',truth)
    summary=dict(status='CLOSED',source_digest=digest(source),plan=plan,families=[{k:v for k,v in f.items()if k!='rows'}for f in families],
        unstarted=unstarted,unavailable=[f['family']for f in source['families']if f['status']=='MU_UNAVAILABLE'],
        roots=len(allrows),wdl_known=sum(r['wdl_bounds'][0]==r['wdl_bounds'][1]for r in allrows),
        cooperative_counts=dict(Counter(str(r['cooperative_decisive'])for r in allrows)),fork_counts=dict(Counter(str(r['wdl_fork'])for r in allrows)),
        truth_digest=digest(truth),seconds=time.perf_counter()-start)
    save(output/'summary.json',summary);print(json.dumps(summary),flush=True);return truth,summary


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--input',required=True);cli.add_argument('--plan',required=True);cli.add_argument('--output',required=True)
    a=cli.parse_args();run(a.input,a.plan,a.output)
