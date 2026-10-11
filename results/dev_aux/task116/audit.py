"""Exposed first-choice sensitivity only; cannot certify mature parameter learning."""
import hashlib,json,time
from pathlib import Path
import chess
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent
old=ROOT/'results/dev_aux/task114/result.json';data=json.loads(old.read_bytes())
profiles=[{'P':208,'N':73,'B':901,'R':149,'Q':397,'K':0},{'P':208,'N':701,'B':89,'R':997,'Q':131,'K':0},{'P':1,'N':1,'B':1,'R':1,'Q':1,'K':0}]
start=time.perf_counter();rows=[]
for root in data['roots']:
    for color in [True,False]:
        if time.perf_counter()-start>120:raise TimeoutError('120s audit cap')
        game=next(g for g in data['games'] if g['root_seed']==root['seed'] and g['opening_length']==root['opening_length'] and g['agent_color']==color and g['policy']=='UNIFORM_LEGAL_RANDOM')
        board=chess.Board()
        for uci in root['prefix']:board.push_uci(uci)
        prefix=[]
        for uci in game['actions']:
            if board.turn==color:break
            board.push_uci(uci);prefix.append(uci)
        assert board.turn==color
        legal=sorted(board.legal_moves,key=lambda m:m.uci());choices=[];captures=sum(board.is_capture(m) for m in legal);promotions=sum(m.promotion is not None for m in legal)
        for profile in profiles:
            values=[]
            for m in legal:
                child=board.copy(stack=True);child.push(m);outcome=child.outcome(claim_draw=False)
                value=sum((1 if p.color==color else -1)*profile[p.symbol().upper()] for p in child.piece_map().values())
                if outcome is not None:value=0 if outcome.winner is None else 10**9 if outcome.winner==color else -10**9
                values.append(value)
            best=max(values);choice=next(i for i,v in enumerate(values) if v==best)
            choices.append({'action':legal[choice].uci(),'leaf_value':best,'maximizer_count':sum(v==best for v in values),'unique_leaf_values':len(set(values))})
        rows.append({'seed':root['seed'],'opening_length':root['opening_length'],'agent_color':color,'additional_opponent_prefix':prefix,'fen':board.fen(),'legal_count':len(legal),'capture_moves':captures,'promotion_moves':promotions,'choices':choices,'two_price_profiles_differ':choices[0]['action']!=choices[1]['action'],'both_extreme_profiles_tie_every_legal_leaf':all(c['unique_leaf_values']==1 for c in choices[:2])})
summary=[]
for depth in [6,24,48]:
    group=[r for r in rows if r['opening_length']==depth]
    summary.append({'opening_length':depth,'states':len(group),'price_profiles_choose_different':sum(r['two_price_profiles_differ'] for r in group),'both_extreme_profiles_tie_every_legal_leaf':sum(r['both_extreme_profiles_tie_every_legal_leaf'] for r in group),'any_capture_available':sum(r['capture_moves']>0 for r in group)})
result={'complete':True,'source_task114_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'profiles':profiles,'states':rows,'state_count':len(rows),'summary':summary,'wall_seconds':time.perf_counter()-start,'mature_games_executed':0,'scope':['Exposed source positions, not an independent human or scientific holdout. No additional games or trained parameters.','Static one-ply choice differences or ties are neither gains nor estimates of true mature-engine16ply reward sensitivity.','When all candidate legal material leaves tie, prices cannot affect this static policy; deeper actual search can distinguish quiet actions.','Changing openings to improve this statistic changes the distribution; do not silently optimize/reselect frozen tests.']}
(OUT/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps({k:result[k] for k in ['state_count','summary','wall_seconds','mature_games_executed']}))