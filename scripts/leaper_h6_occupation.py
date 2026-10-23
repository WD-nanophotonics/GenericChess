"""Exact analytical uniform-policy occupation on already certified H6 domains."""
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
from collections import Counter
import time,json,argparse
from scripts.leaper_explorer_truth import load,save,digest
from scripts.leaper_h6_initial_truth import history_solver,Cap,admit
from scripts.leaper_microgames import role_stop_requested
from scripts.leaper_cooperative_certificate import decode_position

ZERO=(F(0),)*6


def occupation_solver(edges,terms,sides,guard,*,cache_entries=50000,max_calls=2000000,policy_by_side=('UNIFORM','UNIFORM')):
    if len(policy_by_side)!=2 or any(p not in('UNIFORM','FLOOR')for p in policy_by_side):raise ValueError('unsupported analytical policy')
    solve,wdl_calls=history_solver(edges,terms,sides,guard,max_calls=max_calls)
    calls=0
    @lru_cache(maxsize=cache_entries)
    def visit(i,remaining,prior):
        nonlocal calls
        if calls>=max_calls:raise Cap('OCCUPATION_CALL_CAP_UNKNOWN')
        calls+=1
        if calls%1024==0:guard(calls)
        if i in terms or remaining==0 or i in prior:
            winner=terms.get(i)if i in terms else None
            value=0 if winner is None else 1 if winner==0 else-1
            return tuple(F(int(k==value))for k in(-1,0,1)),F(0),F(0),F(0),ZERO,ZERO
        seen=tuple(sorted((*prior,i)));children=[];vs=[]
        for j in edges[i]:
            children.append(visit(j,remaining-1,seen));vs.append(solve(j,remaining-1,seen)[0])
        value=(max if sides[i]==0 else min)(vs);bad=[v!=value for v in vs];fork=len(set(vs))>1
        immediate=[k for k,j in enumerate(edges[i])if j in terms and terms[j]==sides[i]]
        if policy_by_side[sides[i]]=='FLOOR'and immediate:
            # Any selected immediate win has the same terminal outcome and
            # zero future occupation; tie identity cannot change these laws.
            selected=immediate[:1];children=[children[k]for k in selected];bad=[bad[k]for k in selected]
        n=len(children);mean=lambda xs:sum(xs,F(0))/n
        probs=tuple(mean(ch[0][k]for ch in children)for k in range(3))
        decisions=1+mean(ch[1]for ch in children)
        forks=int(fork)+mean(ch[2]for ch in children)
        losses=F(sum(bad),n)+mean(ch[3]for ch in children)
        first_fork=(F(1),*ZERO[:5])if fork else(F(0),*(mean(ch[4][k]for ch in children)for k in range(5)))
        first_loss=(F(sum(bad),n),*(sum((ch[5][k]for b,ch in zip(bad,children)if not b),F(0))/n for k in range(5)))
        return probs,decisions,forks,losses,tuple(first_fork),tuple(first_loss)
    return visit,lambda:(calls,wdl_calls())


def compare_pair_policies(directory,adjacency,plan):
    """Same common mu, uniform seat0 and either uniform or FLOOR seat1."""
    directory=Path(directory);inputs=load(directory/'inputs.json.gz');truth=load(directory/'truth.json.gz')
    by={r['id']:r for r in truth['roots']};start=time.perf_counter();rows=[];summary=[]
    for pair in adjacency['pairs']:
        for family,key in[(pair['left_family'],'left_id'),(pair['right_family'],'right_id')]:
            f=next(f for f in inputs['families']if f['family']==family);source=next(r for r in inputs['rows']if r['family']==family);c=admit(f,source)
            d=load(directory/f'domain{family}.json.gz');positions=[decode_position(p,c.initial_position)for p in d['positions']]
            terms={int(i):w for i,w in d['terminals'].items()}
            def guard(calls=0):
                if role_stop_requested():raise Cap('USER_STOP')
                if time.perf_counter()-start>=plan['whole_cap_seconds']:raise Cap('PAIR_POLICY_CAP_UNKNOWN')
            for opponent in('UNIFORM','FLOOR'):
                visit,calls=occupation_solver(d['edges'],terms,[p.side_to_move for p in positions],guard,
                    max_calls=plan['history_calls_per_mode'],policy_by_side=('UNIFORM',opponent))
                selected=[]
                for root in pair['rows']:
                    guard();v=visit(by[root[key]]['root_index'],6,())
                    item=dict(id=root[key],family=family,opponent=opponent,uniform_terminal_LDW=list(map(str,v[0])),
                        expected_decisions=str(v[1]),expected_fork_visits=str(v[2]),expected_guarantee_lowering_decisions=str(v[3]),
                        first_fork_ply_mass=list(map(str,v[4])),first_lowering_ply_mass=list(map(str,v[5])))
                    rows.append(item);selected.append(item)
                n=len(selected);mean=lambda name:sum(F(r[name])for r in selected)/n
                summary.append(dict(family=family,opponent=opponent,roots=n,
                    uniform_terminal_LDW=[str(sum(F(r['uniform_terminal_LDW'][k])for r in selected)/n)for k in range(3)],
                    expected_decisions=str(mean('expected_decisions')),expected_fork_visits=str(mean('expected_fork_visits')),
                    expected_guarantee_lowering_decisions=str(mean('expected_guarantee_lowering_decisions')),history_calls=calls()))
    paired=[]
    for pair in adjacency['pairs']:
        for opponent in('UNIFORM','FLOOR'):
            by={r['id']:r for r in rows if r['opponent']==opponent};gains=[]
            for root in pair['rows']:
                utility=lambda r:F(r['uniform_terminal_LDW'][2])-F(r['uniform_terminal_LDW'][0])
                gains.append(dict(left_id=root['left_id'],right_id=root['right_id'],gain=str(utility(by[root['right_id']])-utility(by[root['left_id']]))))
            paired.append(dict(opponent=opponent,mean_U0_gain=str(sum(F(r['gain'])for r in gains)/len(gains)),
                gain_signs=dict(Counter('positive'if F(r['gain'])>0 else'negative'if F(r['gain'])<0 else'zero'for r in gains)),rows=gains))
    return dict(format='leaper-H6-pair-analytical-opponent-policy-v1',adjacency_digest=digest(adjacency),truth_digest=digest(truth),
        plan=plan,rows=rows,summary=summary,paired_gain_by_opponent=paired,seconds=time.perf_counter()-start,
        scope='Same128admitted fullhistory starts perrule. Seat0uniform,seat1uniform orliteralimmediateWINotherwiseuniform(FLOOR). Exactanalytic law,no newPlayer orsampledpolicygames,training,rule/layout selection orstrengthgeneralization.')


def summarize_pair_onsets(laws, adjacency):
    """Zero-query descriptive first-event laws on the original paired mu.

    Subgroups use the already exposed direct-root escape flag, never a new
    rule/layout selection or a changed headline. Even/odd plies are actors0/1
    because these admitted histories start with seat0 and strictly alternate.
    """
    results=[]
    for pair in adjacency['pairs']:
        roots=pair['rows'];n=len(roots)
        if not n:raise ValueError('empty paired onset support')
        for tag,side in [('left_family','left_id'),('right_family','right_id')]:
            family=pair[tag]
            for opponent in ('UNIFORM','FLOOR'):
                source=[r for r in laws['rows']if r['family']==family and r['opponent']==opponent]
                rows={r['id']:r for r in source}
                if len(rows)!=len(source)or set(rows)!={r[side]for r in roots}:
                    raise ValueError('onset laws do not match paired support')
                for group in ('all','direct_escape','other'):
                    chosen=[r for r in roots if group=='all'or bool(r['new_best_escapes'])==(group=='direct_escape')]
                    if not chosen:continue
                    selected=[rows[r[side]]for r in chosen];mass={}
                    for row in selected:
                        fork=list(map(F,row['first_fork_ply_mass']));lower=list(map(F,row['first_lowering_ply_mass']))
                        if len(fork)!=6 or len(lower)!=6 or any(v<0 for v in fork+lower)or sum(fork)>1 or sum(lower)>1:
                            raise ValueError('invalid first-event law')
                        if any(sum(lower[:k])>sum(fork[:k])for k in range(1,7)):
                            raise ValueError('lowering cannot precede a fork')
                        if F(row['expected_fork_visits'])<sum(fork)or F(row['expected_guarantee_lowering_decisions'])<sum(lower):
                            raise ValueError('first event exceeds expected visits')
                    avg=lambda key,k:sum(F(r[key][k])for r in selected)/len(selected)
                    for key in ('first_fork_ply_mass','first_lowering_ply_mass'):
                        vv=[avg(key,k)for k in range(6)];ever=sum(vv)
                        mass[key]=dict(by_ply=list(map(str,vv)),by_actor=[str(sum(vv[a::2]))for a in(0,1)],
                            ever=str(ever),never=str(1-ever),conditional_mean_ply=str(sum(k*v for k,v in enumerate(vv))/ever)if ever else None)
                    decisions=sum(F(r['expected_decisions'])for r in selected)/len(selected)
                    visits=sum(F(r['expected_fork_visits'])for r in selected)/len(selected)
                    lowering=sum(F(r['expected_guarantee_lowering_decisions'])for r in selected)/len(selected)
                    results.append(dict(family=family,opponent=opponent,group=group,roots=len(selected),mu_weight=str(F(len(selected),n)),
                        expected_decisions=str(decisions),expected_fork_visits=str(visits),decision_weighted_fork_rate=str(visits/decisions),
                        expected_lowering=str(lowering),decision_weighted_lowering_rate=str(lowering/decisions),**mass))
    return dict(format='leaper-saved-pair-first-onsets-v1',laws_digest=digest(laws),adjacency_digest=digest(adjacency),rows=results,
        scope='Zero new solver,Player,Core orsampledgame calls. Original common128freshhistories,exposed16directescape versus112other subgroup. Firsteventprobability/time/actor and decisionweightedvisits are distinct; subgroups are descriptive, not selected newmu or independent validation.')


def supplied_first_fork_prefix(certificate, worlds, *, last_ply=4, seconds=60, max_edges=50000):
    """Complete literal shallow-prefix control; no whole-H64 cap refill.

    At most five plies of this admitted roster cannot reach a third visit
    (physical cycles require at least four plies). The caller verifies counts
    anyway. Existing closed-domain ranks therefore supply prefix action WDL;
    every path itself is carried by an actual full GameSession.
    """
    from copy import copy
    from dataclasses import replace
    from collections import deque
    from scripts.leaper_clock_rebinding import expand
    from scripts.leaper_single_parity_truth import admit as admit_single
    from scripts.leaper_retrograde import fresh_state,attractor
    from scripts.leaper_design import state_sha
    from generic_chess.core.transition import legal_successors
    from generic_chess.session.session import GameSession
    from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
    if type(last_ply)is not int or not 0<=last_ply<=4:raise ValueError('shallow control allows ply0..4 only')
    tick=time.perf_counter();raw=certificate['target_rule'];_,c,_=admit_single(raw,require_parity=False)
    positions=[expand(p,c.initial_position)for p in certificate['positions']];ix={p:i for i,p in enumerate(positions)}
    edges=[];terms={};counts=Counter()
    def guard():
        if role_stop_requested():raise Cap('USER_STOP')
        if time.perf_counter()-tick>=seconds or counts['Core_edges']>max_edges:raise Cap('SHALLOW_PREFIX_CAP_UNKNOWN')
    for i,p in enumerate(positions):
        guard();s=fresh_state(p,c)
        if s.terminal_status.is_terminal:
            w=s.terminal_status.winner;terms[i]=0 if w is None else 1 if w==p.side_to_move else-1;edges.append(())
        else:
            children=legal_successors(s,c);counts['Core_edges']+=len(children)
            if any(ch.position not in ix for _,ch in children):raise ValueError('prefix source domain not closed')
            edges.append(tuple(ix[ch.position]for _,ch in children))
    values,ranks=attractor(edges,terms);rows=[]
    for world in worlds:
        if world['world']not in certificate['target_worlds']or world['initial_record']['actions']:continue
        _,tc,_=admit_single(world['rule'],require_parity=False)
        if {k:v for k,v in raw.items()if k!='initial_position'}!={k:v for k,v in world['rule'].items()if k!='initial_position'}:
            raise ValueError('prefix world dynamics differ')
        root=GameSession.replay(tc,deserialize_game_record(json.dumps(world['initial_record'])))
        todo=deque([(root,F(1))]);mass=[F(0)]*(last_ply+1);terminal=F(0);survival=F(0);details=[]
        while todo:
            guard();s,prob=todo.popleft();ply=s.state.ply_count;counts['literal_contexts']+=1
            if s.result.status.value!='ongoing':terminal+=prob;continue
            if any(n>=3 for _,n in s.state.repetition_counts):raise ValueError('unexpected shallow count3 barrier')
            branches=[]
            for action,child in legal_successors(s.state,tc):
                counts['Core_edges']+=1
                if child.terminal_status.is_terminal:
                    w=child.terminal_status.winner;value=0 if w is None else 1 if w==0 else-1
                else:
                    p=replace(child.position,ruleset_fingerprint=c.ruleset_fingerprint);j=ix[p]
                    rel=values[j]if values[j]and ranks[j]<=tc.max_ply-child.ply_count else 0
                    value=rel if p.side_to_move==0 else-rel
                branches.append((action,value))
            fork=len({v for _,v in branches})>1
            details.append(dict(world=world['world'],id=state_sha(s.state),ply=ply,actor=s.state.position.side_to_move,
                probability=str(prob),fork=fork,action_WDL=[v for _,v in branches],
                record=json.loads(serialize_game_record(s.to_record()))))
            if fork:mass[ply]+=prob;continue
            if ply==last_ply:survival+=prob;continue
            for action,_ in branches:
                child=copy(s);child.submit(action);counts['public_session_transitions']+=1
                todo.append((child,prob/len(branches)))
        if sum(mass)+terminal+survival!=1:raise ValueError('prefix probability does not conserve mass')
        rows.append(dict(world=world['world'],first_fork_by_ply=list(map(str,mass)),
            terminal_before_fork=str(terminal),ongoing_no_fork_through_last_ply=str(survival),
            eventual_first_fork_bounds=[str(sum(mass)),str(sum(mass)+survival)],details=details))
    return dict(domain_digest=digest(certificate),last_ply=last_ply,rows=rows,counts=dict(counts),seconds=time.perf_counter()-tick,
        scope='Complete literal uniform-policy prefix law throughfixedply4 on existingPRIMARYfreshroots; no naturalPlayer strength, training or fullH64law completion. Positiveforkmass is a rigorous lowerbound on eventualexposure; remainingongoingmass is retained, notdraw. The earlier180sDFS cap staysclosed.')


def run(directory,plan,output=None):
    directory=Path(directory);inputs=load(directory/'inputs.json.gz');truth=load(directory/'truth.json.gz');start=time.perf_counter();rows=[];families=[];status='COMPLETE'
    source_by={r['state_sha256']:r for r in inputs['rows']};rby={r['id']:r for r in truth['roots']}
    for family in inputs['families']:
        if family['status']=='MU_UNAVAILABLE':continue
        began=time.perf_counter()
        def guard(calls):
            if role_stop_requested():raise Cap('USER_STOP')
            if time.perf_counter()-start>=plan['whole_cap_seconds']:raise Cap('WHOLE_CAP_UNKNOWN')
            if time.perf_counter()-began>=plan['family_cap_seconds']:raise Cap('FAMILY_CAP_UNKNOWN')
        source=[r for r in inputs['rows']if r['family']==family['family']];c=admit(family,source[0]);domain=load(directory/f"domain{family['family']}.json.gz")
        positions=[decode_position(p,c.initial_position)for p in domain['positions']];edges=domain['edges'];terms={int(k):v for k,v in domain['terminals'].items()}
        visit,calls=occupation_solver(edges,terms,[p.side_to_move for p in positions],guard,cache_entries=plan['memo_entries_per_family'],max_calls=plan['history_calls_per_family'])
        selected=[]
        try:
            for source_row in source:
                guard(0);r=rby[source_row['state_sha256']];v=visit(r['root_index'],6,())
                if sum(v[0])!=1 or sum(v[4])>1 or sum(v[5])>1 or not 0<v[1]<=6:raise ValueError('invalid exact probability/count law')
                if not r['cooperative_decisive']and v[0][0]+v[0][2]!=0:raise ValueError('uniformpolicy scores in proved no-decisive root')
                row=dict(id=r['id'],family_index=family['family'],split=family['split'],
                    uniform_terminal_LDW=list(map(str,v[0])),expected_decisions=str(v[1]),expected_fork_visits=str(v[2]),
                    expected_guarantee_lowering_decisions=str(v[3]),first_fork_ply_mass=list(map(str,v[4])),
                    first_lowering_ply_mass=list(map(str,v[5])))
                rows.append(row);selected.append(row)
        except Cap as exc:status=str(exc)
        if len(selected)!=len(source):break
        n=len(selected);avg=lambda key:sum(F(r[key])for r in selected)/n
        decisions=avg('expected_decisions');forks=avg('expected_fork_visits');losses=avg('expected_guarantee_lowering_decisions')
        item=dict(family=family['family'],masks=family['masks'],roots=n,
            initial_fork_rate=str(F(sum(rby[r['id']]['wdl_fork']for r in selected),n)),
            uniform_terminal_LDW=[str(sum(F(r['uniform_terminal_LDW'][k])for r in selected)/n)for k in range(3)],
            expected_decisions=str(decisions),expected_fork_visits=str(forks),expected_guarantee_lowering_decisions=str(losses),
            decision_weighted_fork_rate=str(forks/decisions),decision_weighted_lowering_rate=str(losses/decisions),
            probability_ever_fork=str(sum(sum(map(F,r['first_fork_ply_mass']))for r in selected)/n),
            probability_ever_lowering=str(sum(sum(map(F,r['first_lowering_ply_mass']))for r in selected)/n),
            first_fork_ply_mass=[str(sum(F(r['first_fork_ply_mass'][k])for r in selected)/n)for k in range(6)],
            first_lowering_ply_mass=[str(sum(F(r['first_lowering_ply_mass'][k])for r in selected)/n)for k in range(6)],
            occupation_calls=calls()[0],wdl_calls=calls()[1],seconds=time.perf_counter()-began)
        families.append(item);print(json.dumps(item),flush=True)
        if status!='COMPLETE':break
    result=dict(format='leaper-H6-exact-uniform-occupation-v1',status=status,truth_digest=digest(truth),plan=plan,rows=rows,families=families,
        seconds=time.perf_counter()-start,scope='Exact independently uniform legal-action law at both seats on the same admitted initial mu. Not actual PRNG/Player games, population/IID inference, policy strength or oracle-selected training. Initial density, decision-weighted visits, event probability and first-event time are separate estimands.')
    if output is not None:save(output,result)
    return result


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--directory',required=True);cli.add_argument('--plan',required=True);cli.add_argument('--output',required=True);a=cli.parse_args();run(a.directory,load(a.plan),a.output)
