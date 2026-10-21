"""Finite Leaper experiments using shared Core transitions and public search.

This is an exhaustive, horizon-unrolled reference calculation, not a second
rules engine. Complete GameState (including history) is the key. A resource
limit aborts the calculation as UNKNOWN; it never manufactures a draw.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, replace
import hashlib
from itertools import permutations
import json
from pathlib import Path
import time

from generic_chess.core.attacks import is_in_check
from generic_chess.core.actions import action_to_dict
from generic_chess.core.movement import LeapAtom
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.terminal import TerminalStatus
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleSet, RuleInitialSetupOption, ruleset_to_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record

KING = tuple((x,y) for x in (-1,0,1) for y in (-1,0,1) if x or y)
ORTHOGONAL = ((-1,0),(1,0),(0,-1),(0,1))
DIAGONAL = ((-1,-1),(-1,1),(1,-1),(1,1))
BASE_DIR = Path(__file__).resolve().parents[1]


def role_stop_requested():
    for name in ('rollout','advisor','slack'):
        path=BASE_DIR/'.local_agent'/f'{name}.json'
        if path.exists():
            flags=json.loads(path.read_bytes())
            if flags.get('stopped')or flags.get('user_paused'):return True
    return False


def make_rules(*, kinds=('M','M'), horizon=6, layouts=None, b_geometry=DIAGONAL,width=3):
    """One Anchor and one ordinary per side; matched four-actor occupancy."""
    geometry={'K':KING,'M':KING,'A':ORTHOGONAL,'B':b_geometry}
    names=('K',)+tuple(sorted(set(kinds)))
    types=tuple(PieceType(n,n,tuple(LeapAtom(d)for d in geometry[n]),is_anchor=n=='K')for n in names)
    def board(indices):
        b=[None]*(width*width)
        for square,owner,name in zip(indices,(0,0,1,1),('K',kinds[0],'K',kinds[1])):
            b[square]=Piece(owner,name,name)
        return tuple(tuple(b[y*width:y*width+width])for y in range(width))
    layouts=layouts or [(0,1,width*width-1,width*width-2)]
    return RuleSet(board_size=width,piece_types=types,initial_position=board(layouts[0]),
        initial_setup_options=tuple(RuleInitialSetupOption(str(i),board(b))for i,b in enumerate(layouts)if i),
        drop_allowed={n:((False,)*(width*width),)*2 for n in names if n!='K'},
        capture_disposition='remove_from_game',max_ply=horizon,repetition_limit=2,
        repetition_policy='draw',stalemate_result='draw')


def coexistence_rules(lineup=('A','B'), *, horizon=6):
    """Matched six/eight-actor setup; geometry controls keep count/occupancy."""
    geometry={'M':KING,'A':ORTHOGONAL,'B':DIAGONAL,'C':((-1,0),(1,0))}
    if len(lineup)not in(2,3):raise ValueError('declare two or three ordinary actors per side')
    base=make_rules(kinds=('M','M'),horizon=horizon)
    types=(base.piece_types[0],)+tuple(PieceType(n,n,tuple(LeapAtom(d)for d in geometry[n]))for n in sorted(set(lineup)))
    board=[None]*9
    squares=(0,1,3,8,7,5)if len(lineup)==2 else(0,1,3,2,8,7,5,6)
    owners=(0,)*(len(lineup)+1)+(1,)*(len(lineup)+1)
    for square,owner,name in zip(squares,owners,('K',*lineup,'K',*lineup)):
        board[square]=Piece(owner,name,name)
    return replace(base,piece_types=types,initial_position=tuple(tuple(board[y*3:y*3+3])for y in range(3)),
        drop_allowed={n:((False,)*9,)*2 for n in set(lineup)})


def quiet_layouts(count=8):
    """Deterministic fresh layouts, filtered by real Core attack authority."""
    if type(count)is not int or count<1:raise ValueError('positive layout count required')
    compiled=compile_ruleset_for_execution(make_rules())
    pos=initial_state(compiled).position
    candidates=[]
    for indices in permutations(range(9),4):
        b=[None]*9
        for square,owner,name in zip(indices,(0,0,1,1),('K','M','K','M')):
            b[square]=Piece(owner,name,name)
        p=replace(pos,board=tuple(b))
        if not is_in_check(p,0,compiled)and not is_in_check(p,1,compiled):
            candidates.append(indices)
    candidates.sort(key=lambda x:hashlib.sha256(json.dumps(x).encode()).digest())
    return [(0,1,8,7)]+[x for x in candidates if x!=(0,1,8,7)][:count-1]


def terminal_census(kinds=('A','B'), *, b_geometry=DIAGONAL,width=3,seconds=60.):
    """All four-actor-or-captured static placements, labelled CONSTRUCTED.

    Reject a checked nonmoving Anchor, which no legal previous move can leave.
    This is a terminal-existence check, not a reachability or strategy claim.
    """
    from generic_chess.core.identity import repetition_identity_key
    from generic_chess.core.position import GameState,HistoryRecord
    from generic_chess.core.terminal import terminal_result,TerminalResult
    began=time.perf_counter()
    compiled=compile_ruleset_for_execution(make_rules(kinds=kinds,b_geometry=b_geometry,width=width))
    base=initial_state(compiled).position;counts=Counter();examples={};enumerated=0
    for present in((False,False),(True,False),(False,True),(True,True)):
        actors=[(0,'K'),(1,'K')]+[(i,kinds[i])for i in(0,1)if present[i]]
        for squares in permutations(range(width*width),len(actors)):
            board=[None]*(width*width)
            for square,(owner,name)in zip(squares,actors):board[square]=Piece(owner,name,name)
            for turn in(0,1):
                enumerated+=1
                if enumerated%1024==0:
                    if role_stop_requested():raise Exhaustion('STOPPED_USER')
                    if time.perf_counter()-began>=seconds:raise Exhaustion('UNKNOWN: static census time allowance exhausted')
                pos=replace(base,board=tuple(board),side_to_move=turn)
                if is_in_check(pos,1-turn,compiled):continue
                identity=repetition_identity_key(pos,compiled)
                state=GameState(pos,0,((identity,1),),TerminalResult(TerminalStatus.ONGOING),
                    (HistoryRecord(identity,-1,'',False),))
                terminal=terminal_result(state,compiled);counts[terminal.status.value]+=1
                if terminal.status is TerminalStatus.CHECKMATE:
                    examples.setdefault(str(terminal.winner),dict(turn=turn,present=present,squares=squares))
    return dict(kinds=kinds,width=width,enumerated_placements=enumerated,static_counts=counts,mate_examples=examples,
        seconds=time.perf_counter()-began,
        scope='Constructed static placements including captured ordinary pieces;not all claimed reachable. No opponent-Anchor-in-check predecessor violation admitted.')


def blockade_example():
    """Three VALID fresh rules, the same legal first action, different value.

    A checked/checkmated initial board is rejected by the compiler. Start safe
    and replay the common first move instead of bypassing that validator.
    """
    from generic_chess.core.actions import BoardMove
    from generic_chess.core.coordinates import Square
    rows=[];action=BoardMove(Square(0,2),Square(0,1))
    for label,kinds in(('AA',('A','A')),('AB',('A','B')),('A_bare',('A','A'))):
        rules=make_rules(kinds=kinds,layouts=[(7,6,0,1)])
        if label=='A_bare':
            board=[list(r)for r in rules.initial_position];board[0][1]=None
            rules=replace(rules,initial_position=tuple(tuple(r)for r in board))
        compiled=compile_ruleset_for_execution(rules);session=GameSession(compiled)
        before=json.loads(serialize_game_record(session.to_record()));session.submit(action)
        tree=ExactTree(compiled);value=tree.solve(session.state)
        rows.append(dict(label=label,rules=ruleset_to_dict(rules),before=before,
            after=json.loads(serialize_game_record(session.to_record())),
            player0_value=value,result=str(session.result),contexts=len(tree.values),
            legal_replies=[action_to_dict(a)for a in session.legal_actions()]))
    return rows


class Exhaustion(RuntimeError):
    pass


@dataclass
class ExactTree:
    compiled: object
    max_states: int = 200000
    seconds: float = 120.

    def __post_init__(self):
        self.values={};self.edges={};self.paths={};self.visits=0
        self.began=time.perf_counter()

    def solve(self,state,path=()):
        if state in self.values:return self.values[state]
        if self.visits%128==0 and role_stop_requested():
            raise Exhaustion('STOPPED_USER: partial calculation, no inferred labels')
        if self.visits>=self.max_states or time.perf_counter()-self.began>=self.seconds:
            raise Exhaustion('UNKNOWN: reference state/time allowance exhausted')
        self.visits+=1;self.paths[state]=path
        terminal=state.terminal_status
        if terminal.status is not TerminalStatus.ONGOING:
            assert terminal.status is not TerminalStatus.NO_CONTEST
            value=0 if terminal.winner is None else 1 if terminal.winner==0 else -1
            self.edges[state]=()
        else:
            actions=sorted(legal_actions(state,self.compiled),key=lambda a:json.dumps(action_to_dict(a),sort_keys=True))
            assert actions
            children=tuple((a,apply_action(state,a,self.compiled))for a in actions)
            self.edges[state]=children
            vals=[self.solve(s,path+(a,))for a,s in children]
            value=(max if state.position.side_to_move==0 else min)(vals)
        self.values[state]=value
        return value

    def summary(self):
        terminals=Counter();wdl=Counter();branches=Counter();ply=Counter();choices=[]
        for state,value in self.values.items():
            wdl[str(value)]+=1;ply[state.ply_count]+=1
            edges=self.edges[state];branches[len(edges)]+=1
            if not edges:terminals[state.terminal_status.status.value]+=1
            elif len({self.values[s]for _,s in edges})>1:choices.append(state)
        return dict(contexts=len(self.values),physical_positions=len({s.position for s in self.values}),
            contexts_by_ply=ply,player0_wdl=wdl,terminal_reasons=terminals,branching=branches,
            genuine_choice_contexts=len(choices),seconds=time.perf_counter()-self.began,
            exact_scope=f'All legal complete-history continuations of the listed fresh starts under declared ply{self.compiled.max_ply}/repeat2 rules;not infinite-horizon WDL or independent rule samples.')


def session_at(compiled,setup,path):
    session=GameSession(compiled,initial_setup_key=setup)
    for action in path:session.submit(action)
    return session


def decision_study(tree, setup=None, *, limit=32, ratios=(1.,), depths=(1,2,3,4,6), states=None):
    """Public search decisions scored AFTER search against the exact tree.

    Deterministic preorder selection of nonterminal states; no oracle labels
    enter the evaluator. This is a finite diagnostic, not held-out training.
    """
    from generic_chess.learning.incremental import FixedScaleSessionEnv, Model
    from generic_chess.learning.mainline_search import search
    rows=[]
    selected=[s for s in(tree.paths if states is None else states)if tree.edges.get(s)][:limit]
    names=tuple(t.type_id for t in tree.compiled.types_by_id.values()if not t.is_anchor)
    unit='M'if 'M'in names else'A'if 'A'in names else'B'
    for index,state in enumerate(selected):
        session=session_at(tree.compiled,setup,tree.paths[state])
        assert session.state==state
        env=FixedScaleSessionEnv(session,unit_type=unit)
        for ratio in ratios:
            weights=[ratio if n==('board','B')and unit!='B'else 1. for n in env.names]
            for depth in depths:
                receipt=search(env,Model(weights),depth=depth,nodes=100000,seconds=3.)
                chosen=None
                if receipt.complete and receipt.action.kind=='ACTION':
                    chosen=next(child for a,child in tree.edges[state]if a==receipt.action.action)
                sign=1 if state.position.side_to_move==0 else -1
                rows.append(dict(index=index,ply=state.ply_count,ratio=ratio,depth=depth,
                    completed_depth=receipt.completed_depth,complete=receipt.complete,
                    nodes=receipt.nodes,seconds=receipt.seconds,reason=receipt.reason,
                    exact_best=tree.values[state]*sign,
                    chosen_value=None if chosen is None else tree.values[chosen]*sign,
                    optimal=None if chosen is None else tree.values[chosen]==tree.values[state],
                    action=None if chosen is None else action_to_dict(receipt.action.action),
                    path=[action_to_dict(a)for a in tree.paths[state]],
                    start_record=json.loads(serialize_game_record(session.to_record()))))
    return rows


def saved_root_decisions(benchmark, output, *, world='M_M', depths=(1,2,3,4,6)):
    """Reuse saved exact root/action labels; only public finite search is new."""
    from generic_chess.rules.schema import ruleset_from_dict
    from generic_chess.learning.incremental import FixedScaleSessionEnv,Model
    from generic_chess.learning.mainline_search import search
    benchmark=Path(benchmark)
    rules=ruleset_from_dict(json.loads((benchmark/(world+'-rules.json')).read_bytes()))
    compiled=compile_ruleset_for_execution(rules)
    exact=next(w for w in json.loads((benchmark/'summary.json').read_bytes())['worlds']if '_'.join(w['kinds'])==world)
    rows=[]
    for root in exact['roots']:
        session=GameSession(compiled,initial_setup_key=root['setup'])
        env=FixedScaleSessionEnv(session,unit_type='M'if world=='M_M'else'A')
        for depth in depths:
            receipt=search(env,Model([1.]*len(env.names)),depth=depth,nodes=100000,seconds=3.)
            action=action_to_dict(receipt.action.action)if receipt.complete else None
            chosen=next((a['value']for a in root['actions']if a['action']==action),None)
            rows.append(dict(setup=root['setup'],layout=root['layout'],depth=depth,
                completed_depth=receipt.completed_depth,complete=receipt.complete,
                chosen_value=chosen,exact_best=root['value'],
                optimal=None if chosen is None else chosen==root['value'],
                nodes=receipt.nodes,seconds=receipt.seconds,action=action))
    Path(output).write_text(json.dumps(rows,indent=2),encoding='utf-8')
    return rows


def learning_diagnostic(output, *, episodes=32):
    """Small experiential-gradient check; exact labels are observer-only.

    Same fresh states, initial weights, learner and fixed D2 foe. Candidate
    requested depth is the only treatment. This studies information/gradient
    flow, not another strength or hyperparameter panel.
    """
    from dataclasses import asdict
    from generic_chess.learning.incremental import Model,TDLeafEpisode,FixedScaleSessionEnv,play_episode,BudgetEnd
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    began=time.perf_counter();paid=0;active={};rows=[];queries=[]
    rules=make_rules(kinds=('A','B'),layouts=quiet_layouts(8),b_geometry=KING)
    compiled=compile_ruleset_for_execution(rules);oracle=ExactTree(compiled,seconds=30)
    for i in range(8):oracle.solve(initial_state(compiled,str(i)if i else None))
    config=dict(question='Can material parameters change without policy improvement,and does fully terminal TDLeaf search leave a material gradient?',
        episodes_per_arm=episodes,depths=[1,6],foe_depth=2,initial_B=.25,lambda_=.95,eta=.05,
        scale=10,root_order='i%8;learnercolor=(i//8)%2',query_nodes=8192,
        game_nodes=49152,game_seconds=3,whole_seconds=120,whole_nodes=2000000,
        oracle='Research observer only;never search evaluator,ordering,TDtarget or training data.',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (output/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    (output/'rules.json').write_text(json.dumps(ruleset_to_dict(rules),indent=2),encoding='utf-8')
    def guard():
        if time.perf_counter()-began>=120 or paid>=2000000:raise BudgetEnd('DIAGNOSTIC_CAP')
        if role_stop_requested():raise BudgetEnd('STOPPED_USER')
    summaries=[]
    with (output/'queries.jsonl').open('x',encoding='utf-8')as qout,(output/'episodes.jsonl').open('x',encoding='utf-8')as eout:
        for depth in(1,6):
            env=FixedScaleSessionEnv(GameSession(compiled),unit_type='A')
            initial=[.25 if name==('board','B')else 1. for name in env.names]
            model=Model(initial);foe=Model([1.]*len(initial));status='COMPLETE'
            try:
                for i in range(episodes):
                    guard()
                    if 2000000-paid<49152:raise BudgetEnd('FULL_GAME_RESERVE_CAP')
                    session=GameSession(compiled,initial_setup_key=str(i%8)if i%8 else None)
                    env=FixedScaleSessionEnv(session,unit_type='A');before=list(model.weights)
                    active.update(depth=depth,episode=i,color=(i//8)%2)
                    def observe(ply,actor,receipt):
                        nonlocal paid
                        paid+=receipt.nodes;assert model.weights==before
                        state=env.session.state;child=None
                        if receipt.complete:
                            child=next(s for a,s in oracle.edges[state]if a==receipt.action.action)
                        sign=1 if actor==0 else -1
                        q=dict(active,ply=ply,actor=actor,candidate_weights=before,
                            search_weights=list((model if actor==active['color']else foe).weights),
                            **asdict(receipt),oracle_best=oracle.values[state]*sign,
                            oracle_chosen=None if child is None else oracle.values[child]*sign)
                        queries.append(q);qout.write(json.dumps(q,default=str)+'\n');qout.flush()
                    result=play_episode(env,model,opponent=foe,learner=TDLeafEpisode(),learner_color=active['color'],
                        horizon=6,depth=depth,opponent_depth=2,query_nodes=8192,max_nodes=49152,seconds=3,
                        cancel=guard,on_query=observe,search_backend='mainline')
                    row=dict(active,before_weights=before,weights=list(model.weights),record=env.record(),**asdict(result))
                    rows.append(row);eout.write(json.dumps(row)+'\n');eout.flush()
                    if result.ending=='STOPPED_USER':raise BudgetEnd('STOPPED_USER')
            except BudgetEnd as exc:status=str(exc)
            own=[q for q in queries if q['depth']==depth and q['actor']==q['color']]
            es=[e for e in rows if e['depth']==depth]
            summaries.append(dict(depth=depth,status=status,episodes=len(es),missing=episodes-len(es),initial=initial,final=model.weights,
                outcomes=Counter('UNKNOWN'if e['outcome']is None else str(e['outcome']*(1 if e['color']==0 else -1))for e in es),
                changed_updates=sum(bool(e['update']['changed'])for e in es),candidate_queries=len(own),
                terminal_PV_observations=sum(q['pv_terminal']and q['complete']for q in own),
                suboptimal_candidate_queries=sum(q['oracle_chosen']is not None and q['oracle_chosen']<q['oracle_best']for q in own)))
            if status=='STOPPED_USER':break
    data=dict(config=config,summaries=summaries,nodes=paid,seconds=time.perf_counter()-began,
        scope='Finite mechanism diagnostic;different played states/realized cost,not equal-compute strength or population inference.')
    (output/'summary.json').write_text(json.dumps(data,indent=2),encoding='utf-8');return data


def run(output, *, horizon=6, layouts_count=8, states=200000, seconds=120.,
        worlds=(('M','M'),('A','A'),('B','B'),('A','B'),('B','A')), b_geometry=DIAGONAL):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    layouts=quiet_layouts(layouts_count);results=[]
    for kinds in worlds:
        rules=make_rules(kinds=kinds,horizon=horizon,layouts=layouts,b_geometry=b_geometry)
        compiled=compile_ruleset_for_execution(rules);label='_'.join(kinds)
        (output/(label+'-rules.json')).write_text(json.dumps(ruleset_to_dict(rules),indent=2),encoding='utf-8')
        tree=ExactTree(compiled,max_states=states,seconds=seconds);roots=[];status='COMPLETE'
        try:
            for i in range(len(layouts)):
                setup=str(i)if i else None
                root=initial_state(compiled,setup);v=tree.solve(root)
                roots.append(dict(setup=setup,layout=layouts[i],value=v,terminal=root.terminal_status.status.value,
                    actions=[dict(action=action_to_dict(a),value=tree.values[s])for a,s in tree.edges[root]]))
        except Exhaustion as exc:status=str(exc)
        result=dict(kinds=kinds,horizon=horizon,status=status,roots=roots,summary=tree.summary())
        results.append(result)
        (output/'summary.json').write_text(json.dumps(dict(layouts=layouts,worlds=results),indent=2),encoding='utf-8')
        print(label,status,result['summary'],flush=True)
    return results


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output');parser.add_argument('--horizon',type=int,default=6)
    parser.add_argument('--layouts',type=int,default=8)
    parser.add_argument('--states',type=int,default=200000)
    parser.add_argument('--seconds',type=float,default=120.)
    args=parser.parse_args();run(args.output,horizon=args.horizon,layouts_count=args.layouts,states=args.states,seconds=args.seconds)
