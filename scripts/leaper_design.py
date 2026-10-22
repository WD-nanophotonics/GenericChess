"""Bounded pure-Leaper forward-design probe; no production defaults or learning.

Use prepare, preflight, run, qualify with a NEW --output directory. The preparation
freezes orbit masks, source, complete rules, paired controller seeds and clocks.
No caller-censored game is a draw. Default preparation uses ten metadata-selected
controls; separately registered batches retain their actual sampling law.
"""
from __future__ import annotations
import argparse, hashlib, json, random, time, traceback
from collections import Counter
from dataclasses import replace
from pathlib import Path
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.transition import legal_successors
from generic_chess.rules.schema import RuleSet, ruleset_to_dict, ruleset_from_dict, compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.config import EvaluationConfig
from scripts.research_record import record_value, write_record

ORBITS=((1,0),(1,1),(2,0),(2,1),(2,2))
PAIRS=((1,2),(1,3),(1,4),(1,8),(1,16),(2,4),(2,8),(4,8),(8,16),(3,8))

def offsets(mask):
    if isinstance(mask,bool) or not isinstance(mask,int) or not 1<=mask<=31:
        raise ValueError('mask must be an integer in 1..31')
    return tuple(sorted({(sx*u,sy*v) for i,(x,y) in enumerate(ORBITS) if mask&(1<<i)
                         for u,v in ((x,y),(y,x)) for sx in (-1,1) for sy in (-1,1)}))

def definition(a,b):
    types=(PieceType('K','K',tuple(LeapAtom(v) for v in offsets(3)),is_anchor=True),
           PieceType('A','A',tuple(LeapAtom(v) for v in offsets(a))),
           PieceType('B','B',tuple(LeapAtom(v) for v in offsets(b))))
    board=[None]*16
    for ix,owner,tid in ((0,0,'K'),(1,0,'A'),(4,0,'B'),(15,1,'K'),(14,1,'A'),(11,1,'B')):
        board[ix]=Piece(owner,tid,tid)
    return RuleSet(board_size=4,piece_types=types,
        initial_position=tuple(tuple(board[4*r:4*r+4]) for r in range(4)),
        capture_disposition='remove_from_game',
        drop_allowed={t:((False,)*16,)*2 for t in ('A','B')},
        max_ply=128,repetition_limit=4)

def outcome_value(result, role, censor=None):
    # SessionResult deliberately has no Core TerminalResult.is_terminal property.
    if censor or result.status.value in ('ongoing','no_contest'):return None
    return 0 if result.winner is None else 1 if result.winner==role else -1

def match_action(session, raw):
    actions=[a for a in session.legal_actions() if record_value(a)==raw]
    if len(actions)!=1:raise ValueError('retained action does not uniquely match legal Core action')
    return actions[0]

class LeafOrderAdapter:
    def __init__(self, leaf, ordering):
        self.evaluate=leaf.evaluate
        self.type_value=ordering.type_value
        self.capture_order_value=ordering.capture_order_value

def material_profiles(c):
    base=AlphaBetaPlayer(c,use_disk_cache=False).evaluation_profile
    zero=replace(base,board_value_by_type={t:0 for t in base.board_value_by_type},
        hand_value_by_base_type={t:0 for t in base.hand_value_by_base_type},
        piece_profiles={t:replace(p,normalized_board_value=0,normalized_hand_value=0)
                        for t,p in base.piece_profiles.items()})
    return base,zero

def make_player(c,policy,world=None):
    if policy=='AB':return AlphaBetaPlayer(c,use_disk_cache=False)
    assert policy in ('STATIC_ADAPTER','M0')
    base,zero=material_profiles(c)
    if world is not None:
        assert world['material_profiles']=={'Static':record_value(base),'M0':record_value(zero)}
    ordering=Evaluator(c,base,EvaluationConfig())
    leaf=Evaluator(c,base if policy=='STATIC_ADAPTER' else zero,EvaluationConfig())
    return AlphaBetaPlayer(c,evaluator_override=LeafOrderAdapter(leaf,ordering),use_disk_cache=False)

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(path.read_text(encoding='utf-8'))
def state_sha(state):return hashlib.sha256(json.dumps(record_value(state),sort_keys=True,separators=(',',':')).encode()).hexdigest()

def graph(mask):
    moves=offsets(mask);adj={i:{(i//4+dy)*4+i%4+dx for dx,dy in moves if 0<=i%4+dx<4 and 0<=i//4+dy<4} for i in range(16)}
    todo=set(adj);sizes=[]
    while todo:
        seen={min(todo)};front=list(seen)
        while front:
            for n in adj[front.pop()]-seen:seen.add(n);front.append(n)
        sizes.append(len(seen));todo-=seen
    return {'components':sorted(sizes),'directed_edges':sum(map(len,adj.values())),
            'mean_empty_board_degree':sum(map(len,adj.values()))/16}

def limits(nodes):return SearchLimits(max_depth=64,max_nodes=nodes,max_time_seconds=None,
    quiescence_max_depth=0,quiescence_hard_max_depth=8)

def search_spec(reg, policy):
    """Explicit controller label to base evaluator and counted-node budget."""
    spec=reg.get('search_variants',{}).get(policy)
    base=policy if spec is None else spec['base']
    nodes=reg['nodes'] if spec is None else spec['nodes']
    if base not in ('AB','STATIC_ADAPTER','M0'):raise ValueError('unknown search base')
    if isinstance(nodes,bool) or not isinstance(nodes,int) or nodes<=0:raise ValueError('positive integer node budget required')
    return base,nodes

def forecast_search_turns(reg):
    """Conservative maximum search turns/game, including BOTH search actors."""
    actors=max(sum(p not in ('RNG','FLOOR') for p in pair) for pair in reg['pairs'].values())
    return reg['caller_plies'] if actors==2 else actors*((reg['caller_plies']+1)//2)

def actor_seeds(reg, world, slot):
    """An explicit code index may share streams across its representations."""
    index=world.get('seed_world',world['world'])
    if isinstance(index,bool) or not isinstance(index,int) or index<0:raise ValueError('nonnegative integer seed_world required')
    return {a:reg['seed']+10000*index+100*slot['repeat']+10*slot['role']+a for a in (0,1)}

def prepare(d, repetitions=1, first_repeat=0, nodes=512, material_ablation=False):
    assert not (d/'inputs.json').exists();d.mkdir(parents=True,exist_ok=True);tick=time.perf_counter()
    rows=[]
    for w,(a,b) in enumerate(PAIRS):
        rule=definition(a,b);raw=ruleset_to_dict(rule,include_metadata=True)
        write_record(d/f'input-{w:02d}.json',raw)
        try:
            restored=ruleset_from_dict(load(d/f'input-{w:02d}.json'));assert ruleset_to_dict(restored,include_metadata=True)==raw
            c=compile_rule(restored);s=GameSession(c);player=AlphaBetaPlayer(c,use_disk_cache=False)
            rows.append({'world':w,'masks':[a,b],'rule':raw,'fingerprint':compute_fingerprint(restored),'initial_record':record_value(s.to_record()),
                'initial_state':record_value(s.state),'initial_legal_count':len(s.legal_actions()),'profile':record_value(player.evaluation_profile),
                'geometry':[graph(a),graph(b)],'status':'ready'})
        except Exception as e:rows.append({'world':w,'masks':[a,b],'rule':raw,'status':'setup_failed','failure':repr(e)})
    if material_ablation:
        for row in rows:
            if row['status']=='ready':
                c=compile_rule(ruleset_from_dict(row['rule']));base,zero=material_profiles(c)
                row['material_profiles']={'Static':record_value(base),'M0':record_value(zero)}
    inputs={'scope':'Fixed4x4/KAB per side/D4-symmetric radius2 Leaps/remove/no drops or promotions. Not full generated-domain generality.','worlds':rows}
    write_record(d/'inputs.json',inputs)
    write_record(d/'registration.json',{'question':'Do metadata-selected pure-Leaper rules support a cheap multi-controller forward portrait beyond immediate-win exploitation?',
        'changed_premise':'Prior mixed-roster/geometry experiments confounded roster/layout; fix both and vary only movement orbits. Incoming advice independently supports this cheap question.',
        'selection':'Ten predeclared mask pairs, no outcome/oracle selection or replacement; fixed symmetric layout; isolated, connected, nested and disjoint motion controls.',
        'pairs':{'AB_RNG':['AB','RNG'],'FLOOR_RNG':['FLOOR','RNG'],'RNG_RNG':['RNG','RNG']},'roles':[0,1],
        'repetitions':repetitions,'first_repeat':first_repeat,'nodes':nodes,'rule_max_ply':128,'caller_plies':128,'repetition_limit':4,
        'q':0,'forced_check_depth':8,'disk_cache':False,'TT':'fresh per actor per game, retained inside game',
        'seed':202610221209,'planned_games':len(PAIRS)*6*repetitions,'expected_seconds':600 if repetitions==1 else 2100,'whole_cap_seconds':1200 if repetitions==1 else 2400,
        'preparation_seconds':time.perf_counter()-tick,'input_sha256':sha(d/'inputs.json'),'source_sha256':sha(Path(__file__)),
        'interpretation':'AB is the existing Static default evaluator including dynamics, not a material-only policy. No win-time-only scalar, learning gate, solver, default change or AUX task.',
        'stop':'Preserve all failed/unattempted/UNKNOWN slots at cooperative cap. No refill. Preflight measures cost before starting.'})
    if material_ablation:
        reg=load(d/'registration.json');reg.update(
            question='Does board/hand leaf material add finite utility against Random on all10pureLeaper rules under commonStaticordering?',
            changed_premise='AB512 improves over FLOOR but may use geometry-derived dynamics/order. A same-interface leaf-only counterfactual is needed; default-path games are not the adapter control.',
            pairs={'StaticAdapter_RNG':['STATIC_ADAPTER','RNG'],'M0_RNG':['M0','RNG']},
            planned_games=len(PAIRS)*4*repetitions,material_ablation=True,expected_seconds=900,whole_cap_seconds=1500,
            controls='SAME3methodAdapter on both search arms; Staticordering retained; zeroCURRENTboard/BASEhand material inM0; all other completeprofile fields/dynamics retained. Fresh actorTT/game; diskOFF.',
            cost_gate='Opening+natural-prefix wrapper-path preflight before fitness; defer if forecast not bounded/affordable; no budget extension.')
        write_record(d/'registration.json',reg)
    print('PREPARED',len(rows),Counter(x['status'] for x in rows),flush=True)

def floor(s,rng):
    legal=[];actor=s.state.position.side_to_move
    for action,child in legal_successors(s.state,s.compiled):
        legal.append(action)
        if child.terminal_status.is_terminal and child.terminal_status.winner==actor:
            return action,{'immediate_win':True,'children_scanned':len(legal)}
    return legal[rng.randrange(len(legal))],{'immediate_win':False,'children_scanned':len(legal)}

def preflight(d):
    assert not(d/'preflight.json').exists()
    reg=load(d/'registration.json');inputs=load(d/'inputs.json')
    assert sha(d/'inputs.json')==reg['input_sha256'];assert sha(Path(__file__))==reg['source_sha256']
    material=reg.get('material_ablation',False)
    if material:
        if not(d/'preflight-inputs.json').exists():
            raise ValueError('material ablation requires frozen complete-history preflight-inputs.json before any query')
        roots=load(d/'preflight-inputs.json')['roots']
        assert all(any(x['world']==w['world'] and x['record']['actions'] for x in roots)
                   for w in inputs['worlds'] if w['status']=='ready'), 'include a natural nonempty history for each ready world'
        policies=['STATIC_ADAPTER','M0']
    else:
        roots=load(d/'preflight-inputs.json')['roots'] if (d/'preflight-inputs.json').exists() else [
            {'world':w['world'],'phase':'initial','rule':w['rule'],'record':w['initial_record']}
            for w in inputs['worlds'] if w['status']=='ready']
        policies=reg.get('preflight_policies',['AB'])
    if not roots or not policies:raise ValueError('preflight requires actual roots and search policies')
    from generic_chess.session.serialization import deserialize_game_record
    out={'status':'RUNNING','rows':[],'cap_seconds':120};tick=time.perf_counter();write_record(d/'preflight.json',out);decomp=0
    for ix,root in enumerate(roots):
        if time.perf_counter()-tick>=120:break
        w=inputs['worlds'][root['world']];assert w['rule']==root['rule']
        c=compile_rule(ruleset_from_dict(w['rule']));s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])))
        if material:
            base,zero=material_profiles(c);es=Evaluator(c,base,EvaluationConfig());ez=Evaluator(c,zero,EvaluationConfig())
            for st in [s.state]+[ch for _,ch in legal_successors(s.state,c)]:
                raw=sum((1 if p.owner==0 else -1)*base.board_value_by_type[p.current_type_id] for p in st.position.board if p)
                raw+=sum((1 if a==0 else -1)*n*base.hand_value_by_base_type[t] for a in (0,1) for t,n in st.position.hands[a].counts)
                if st.position.side_to_move==1:raw=-raw
                assert es.evaluate(st)-ez.evaluate(st)==raw;decomp+=1
        for policy in (policies if ix%2==0 else list(reversed(policies))):
            if time.perf_counter()-tick>=120:break
            base,nodes=search_spec(reg,policy)
            player=make_player(c,base,w);t=time.perf_counter();dec=player.choose_action(s,limits(nodes))
            row={'input':ix,'world':root['world'],'phase':root.get('phase','recorded'),'policy':policy,'base_policy':base,'node_budget':nodes,'record':root['record'],'decision':record_value(dec),'seconds':time.perf_counter()-t}
            out['rows'].append(row);write_record(d/'preflight.json',out)
            assert dec.action in s.legal_actions();pv=GameSession.replay(c,s.to_record())
            for raw in row['decision']['principal_variation']:pv.submit(match_action(pv,raw))
            row['PV_legal']=True;write_record(d/'preflight.json',out)
    maxcall=max((r['seconds'] for r in out['rows']),default=None)
    missing=len(roots)*len(policies)-len(out['rows']);turns=forecast_search_turns(reg)
    forecast=None if maxcall is None else maxcall*turns*reg['planned_games']*1.25+reg['preparation_seconds']
    out.update(status='CLOSED',seconds=time.perf_counter()-tick,missing=missing if material else ([] if not missing else ['planned cost calls incomplete']),decomposition_checks=decomp,forecast_seconds=forecast,forecast_search_turns_per_game=turns,forecast_scope='Maximum sampled search-call cost times maximum search turns, plus25percent/preparation. Sampled maximum is not a future per-call bound; other-controller/recording costs are not fully measured. No coverage guarantee.',cost_gate_passed=not missing and forecast is not None and forecast<reg['whole_cap_seconds'])
    write_record(d/'preflight.json',out);print('PREFLIGHT',len(out['rows']),out['seconds'],flush=True)

def run(d):
    assert not(d/'results.json').exists();reg=load(d/'registration.json');pf=load(d/'preflight.json');assert pf['status']=='CLOSED' and not pf['missing']
    assert sha(d/'inputs.json')==reg['input_sha256'];assert sha(Path(__file__))==reg['source_sha256']
    if 'cost_gate_passed' in pf:assert pf['cost_gate_passed']
    if reg.get('material_ablation'):assert pf.get('decomposition_checks',0)>0
    # Cost screen is a bound/forecast only, never a guarantee of full coverage.
    assert max(r['seconds'] for r in pf['rows'])<5
    worlds=load(d/'inputs.json')['worlds']
    slots=[{'slot':i,'world':w,'pair':pair,'role':role,'repeat':rep,'status':'not_started','utility':[-1,1]}
           for i,(w,pair,role,rep) in enumerate((w,pair,role,rep) for w in range(len(worlds)) for pair in reg['pairs'] for role in reg['roles'] for rep in range(reg.get('first_repeat',0),reg.get('first_repeat',0)+reg['repetitions']))]
    assert len(slots)==reg['planned_games'], 'frozen planned game count does not match inputs/controllers/roles/repeats'
    order=list(range(len(slots)));random.Random(reg['seed']).shuffle(order);out={'status':'RUNNING','slots':slots,'execution_order':order,'queries':0,'failures':[]};write_record(d/'results.json',out)
    tick=time.perf_counter();cap=reg['whole_cap_seconds']-reg['preparation_seconds']-pf['seconds'];contexts={}
    for ix in order:
        if time.perf_counter()-tick>=cap:break
        slot=slots[ix];w=worlds[slot['world']];t=time.perf_counter();path=d/f'game-{ix:03d}.json';row={**slot,'queries':[],'censor':None}
        if w['status']!='ready':slot['status']='setup_failed';continue
        try:
            if w['world'] not in contexts:contexts[w['world']]=compile_rule(ruleset_from_dict(w['rule']))
            c=contexts[w['world']];s=GameSession(c);role=slot['role'];pols={role:reg['pairs'][slot['pair']][0],1-role:reg['pairs'][slot['pair']][1]}
            # Same role/rep streams across controller pairs; prefix divergence changes their use.
            seeds=actor_seeds(reg,w,slot);rng={a:random.Random(seeds[a]) for a in (0,1)}
            players={a:make_player(c,search_spec(reg,pols[a])[0],w) for a in (0,1) if pols[a] not in ('RNG','FLOOR')}
            row.update(initial_record=record_value(s.to_record()),policy_by_actor=pols,rng_seeds=seeds);write_record(path,row)
            while not s.state.terminal_status.is_terminal and s.state.ply_count<reg['caller_plies']:
                if time.perf_counter()-tick>=cap:row['censor']='whole_cap';break
                a=s.state.position.side_to_move;policy=pols[a];qt=time.perf_counter();legal=s.legal_actions();q={'actor':a,'policy':policy,'root_ply':s.state.ply_count,'legal_count':len(legal),'state_sha256':state_sha(s.state)}
                if policy=='RNG':action=legal[rng[a].randrange(len(legal))]
                elif policy=='FLOOR':action,detail=floor(s,rng[a]);q['floor']=detail
                else:
                    base,nodes=search_spec(reg,policy)
                    dec=players[a].choose_action(s,limits(nodes));action=dec.action;q.update(decision=record_value(dec),base_policy=base,node_budget=nodes)
                q.update(action=record_value(action),seconds=time.perf_counter()-qt);row['queries'].append(q);out['queries']+=1;row['current_record']=record_value(s.to_record());write_record(path,row)
                if action is None:row['censor']='no_action';break
                s.submit(action)
            res=s.result;value=outcome_value(res,role,row['censor'])
            row.update(status='finished',final_record=record_value(s.to_record()),final_state=record_value(s.state),terminal=record_value(res),utility=[value,value] if value is not None else [-1,1],seconds=time.perf_counter()-t);row.pop('current_record',None);write_record(path,row)
            slot.update(status='finished',utility=row['utility'],terminal=row['terminal'],plies=s.state.ply_count,receipt=path.name)
        except Exception as e:
            row.update(status='failed',failure={'error':repr(e),'traceback':traceback.format_exc()});write_record(path,row);slot.update(status='failed');out['failures'].append({'slot':ix,'failure':row['failure']})
        write_record(d/'results.json',out)
        print('GAME',ix,w['masks'],slot['pair'],slot['role'],slot['status'],slot['utility'],round(time.perf_counter()-tick,2),flush=True)
    out.update(status='CLOSED',seconds=time.perf_counter()-tick,unattempted=[s['slot'] for s in slots if s['status']=='not_started']);write_record(d/'results.json',out)
    print('CLOSED',Counter(s['status'] for s in slots),out['queries'],out['seconds'],flush=True)

def qualify(d):
    tick=time.perf_counter();inputs=load(d/'inputs.json');results=load(d/'recovered-results.json' if (d/'recovered-results.json').exists() else d/'results.json');histories=0;pv_edges=0;checks=0
    for slot in results['slots']:
        if slot['status']!='finished':continue
        row=load(d/slot['receipt']);c=compile_rule(ruleset_from_dict(inputs['worlds'][slot['world']]['rule']));s=GameSession.replay(c,deserialize_game_record(json.dumps(row['initial_record'])))
        final_record=deserialize_game_record(json.dumps(row['final_record']));actions=final_record.actions
        for q,a in zip(row['queries'],actions,strict=True):
            assert q['state_sha256']==state_sha(s.state);assert q['action']==record_value(a);assert a in s.legal_actions();checks+=1
            dec=q.get('decision')
            if dec:
                probe=GameSession.replay(c,s.to_record())
                # PlayerDecision.pv is retained by the strict recorder.
                for pa in dec.get('principal_variation',[]):
                    move=match_action(probe,pa);probe.submit(move);pv_edges+=1
            s.submit(a);histories+=1
        assert record_value(s.state)==row['final_state'];assert record_value(s.result)==row['terminal'];assert s.state.ply_count==slot['plies']
    out={'status':'PASS','games':sum(s['status']=='finished' for s in results['slots']),'history_plies':histories,'action_checks':checks,'pv_edges':pv_edges,'seconds':time.perf_counter()-tick,'scope':'Shared production Core full-history replay, not an independent engine or game-WDL oracle.'};write_record(d/'qualification.json',out);print(json.dumps(out),flush=True)

def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('command',choices=('prepare','preflight','run','qualify'));p.add_argument('--output',type=Path,required=True);p.add_argument('--repetitions',type=int,default=1);p.add_argument('--first-repeat',type=int,default=0);p.add_argument('--nodes',type=int,default=512);p.add_argument('--material-ablation',action='store_true');a=p.parse_args();assert a.repetitions>0 and a.first_repeat>=0 and a.nodes>0;prepare(a.output,a.repetitions,a.first_repeat,a.nodes,a.material_ablation) if a.command=='prepare' else globals()[a.command](a.output)
if __name__=='__main__':main()
