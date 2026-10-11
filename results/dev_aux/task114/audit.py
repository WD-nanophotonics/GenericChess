"""Cheap objective discriminator; all policies explicit, no mature engine or learning."""
import hashlib,json,random,sys,time,importlib.util
from pathlib import Path
import chess
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent
p=ROOT/'results/dev_aux/task104/short_game.py';spec=importlib.util.spec_from_file_location('frozen_short_game',p);sg=importlib.util.module_from_spec(spec);spec.loader.exec_module(sg)
config=json.loads((OUT/'declaration.json').read_bytes())
started=time.perf_counter();deadline=started+config['deadline_seconds']
def guard():
    if time.perf_counter()>deadline:raise TimeoutError('audit cap120s')
    for root in [ROOT,ROOT.parent/'GenericChess 2']:
        for name,key,stop in [('rollout.json','user_paused',True),('advisor.json','enabled',False),('slack.json','stopped',True)]:
            if json.loads((root/'.local_agent'/name).read_bytes()).get(key)==stop:raise RuntimeError('stop flag')
def moves(b):return sorted(b.legal_moves,key=lambda m:m.uci())
def qty(b,color):return sg.quantity(b,color)-sg.quantity(b,not color)
def greedy(b):
    color=b.turn; candidates=[]
    for m in moves(b):
        child=b.copy(stack=True);child.push(m)
        outcome=child.outcome(claim_draw=False)
        value=qty(child,color)
        if outcome is not None:value=0 if outcome.winner is None else 100 if outcome.winner==color else -100
        candidates.append((value,m.uci(),m))
    best=max(x[0] for x in candidates)
    return next(x[2] for x in candidates if x[0]==best),len(candidates)
roots=[];failures=[]
for seed in config['opening_seeds']:
    guard();board=chess.Board();rng=random.Random(seed);prefix=[]
    for depth in range(1,max(config['opening_lengths'])+1):
        if board.is_game_over(claim_draw=False):
            for intended in config['opening_lengths']:
                if intended>=depth:failures.append({'seed':seed,'intended_length':intended,'stopped_at':depth-1,'reason':board.outcome(claim_draw=False).termination.name,'prefix':prefix.copy()})
            break
        m=rng.choice(moves(board));board.push(m);prefix.append(m.uci())
        if depth in config['opening_lengths']:
            if board.is_game_over(claim_draw=False):failures.append({'seed':seed,'intended_length':depth,'stopped_at':depth,'reason':board.outcome(claim_draw=False).termination.name,'prefix':prefix.copy()})
            else:roots.append({'seed':seed,'opening_length':depth,'prefix':prefix.copy(),'fen':board.fen(),'quantity_white':qty(board,chess.WHITE),'legal_count':board.legal_moves.count(),'legal_capture_count':sum(board.is_capture(m) for m in board.legal_moves)})
games=[]
for root in roots:
    for color in [chess.WHITE,chess.BLACK]:
        for policy in config['arms']:
            guard();board=chess.Board()
            for uci in root['prefix']:
                m=chess.Move.from_uci(uci);assert m in board.legal_moves;board.push(m)
            assert board.fen()==root['fen']
            opponent_rng=random.Random(62000+root['seed']);agent_rng=random.Random(63000+root['seed'])
            actions=[];agent_choices=[];child_evaluations=0;before=qty(board,color)
            for ply in range(config['post_opening_cap']):
                guard()
                if board.is_game_over(claim_draw=False):break
                if board.turn==color and policy=='ONE_PLY_UNIT_GREEDY_LEXICAL_TIE':
                    m,count=greedy(board);child_evaluations+=count
                else:m=(agent_rng if board.turn==color else opponent_rng).choice(moves(board))
                assert m in board.legal_moves
                if board.turn==color:agent_choices.append(m.uci())
                board.push(m);actions.append(m.uci())
            scored=sg.score(board,color,len(actions),config['post_opening_cap'])
            games.append({'root_seed':root['seed'],'opening_length':root['opening_length'],'agent_color':color,'policy':policy,'actions':actions,'agent_choices':agent_choices,'end_fen':board.fen(),'initial_quantity_difference':before,'quantity_change':qty(board,color)-before,'score':scored,'one_ply_child_evaluations':child_evaluations})
paired=[]
for root in roots:
    for color in [chess.WHITE,chess.BLACK]:
        group=[g for g in games if g['root_seed']==root['seed'] and g['opening_length']==root['opening_length'] and g['agent_color']==color]
        a,b=group
        paired.append({'seed':root['seed'],'opening_length':root['opening_length'],'color':color,'random_reward':a['score']['reward'],'greedy_reward':b['score']['reward'],'reward_difference':b['score']['reward']-a['score']['reward'],'random_quantity_change':a['quantity_change'],'greedy_quantity_change':b['quantity_change'],'terminal':a['score']['terminal'] or b['score']['terminal']})
summary=[]
for depth in config['opening_lengths']:
    pairs=[p for p in paired if p['opening_length']==depth];rs=[r for r in roots if r['opening_length']==depth];gs=[g for g in games if g['opening_length']==depth]
    summary.append({'opening_length':depth,'roots':len(rs),'paired_colors':len(pairs),'reward_ties':sum(p['reward_difference']==0 for p in pairs),'greedy_reward_better':sum(p['reward_difference']>0 for p in pairs),'greedy_reward_worse':sum(p['reward_difference']<0 for p in pairs),'mean_paired_reward_difference':sum(p['reward_difference'] for p in pairs)/len(pairs) if pairs else None,'roots_with_immediate_capture':sum(r['legal_capture_count']>0 for r in rs),'terminal_games':sum(g['score']['terminal'] for g in gs),'actual_plies':sum(len(g['actions']) for g in gs)})
result={'complete':True,'backend':'PYTHON_CHESS_RULES_AND_DECLARED_UNWEIGHTED_POLICIES; NOT_MATURE_SEARCH','python_chess_version':chess.__version__,'frozen_reward_source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'declaration_sha256':hashlib.sha256((OUT/'declaration.json').read_bytes()).hexdigest(),'roots':roots,'opening_failures':failures,'games':games,'game_count':len(games),'paired':paired,'summary':summary,'wall_seconds':time.perf_counter()-started,'mature_games_executed':0,'learned_parameter_updates':0,'limitations':['A greedy/random policy difference tests reward discrimination, not discrimination between material vectors or learning of human ratios.','No price-dependent search, trained values, teacher engine, human labels or mature runtime.','Random-midgame selection changes the play distribution; do not pool with existing frozen480game experiment or claim a faster equivalent experiment.','Opening failures are preserved; no resampling, seed change or result-dependent extension.','Shared seed draw streams diverge under different trajectories; not identical opponent actions.','The one-ply greedy uses lexical ties and automatic standard-Chess terminal authority; no SEE or weighted material prior.','Shorter games do not automatically identify long-range or promoted-piece relative values; only a future actual pilot can decide signal/cost.']}
(OUT/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
print(json.dumps({k:result[k] for k in ['backend','game_count','summary','wall_seconds','opening_failures','mature_games_executed']}))