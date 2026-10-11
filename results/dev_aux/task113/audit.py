"""Scoped Shogi cheap-reward and future USI probe witnesses; Core legality only."""
import hashlib,json,sys,time
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT));OUT=Path(__file__).resolve().parent
from generic_chess import build_standard_shogi_ruleset, compile_ruleset_for_execution
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from generic_chess.learning.shogi_rules import sfen_to_gc_state, gc_to_sfen, gc_action_to_usi, CSHOGI_INDEX
TYPES=['P','L','N','S','B','R','G','TP','TL','TN','TS','TB','TR']
TOKENS={'TP':'+P','TL':'+L','TN':'+N','TS':'+S','TB':'+B','TR':'+R'}
BASE={'TP':'P','TL':'L','TN':'N','TS':'S','TB':'B','TR':'R'}
PRICES={t:31+17*CSHOGI_INDEX[t] for t in TYPES}|{'K':0}
started=time.perf_counter(); deadline=started+120

def guard():
    if time.perf_counter()>deadline:raise TimeoutError('120s audit cap')
    for root in [ROOT,ROOT.parent/'GenericChess 2']:
        for name,key,stopped in [('rollout.json','user_paused',True),('advisor.json','enabled',False),('slack.json','stopped',True)]:
            v=json.loads((root/'.local_agent'/name).read_bytes())
            if v.get(key)==stopped:raise RuntimeError('stop flag '+str(root/name))

def sfen(pieces,hand='-',white=False):
    pieces={(1,8):'K',(9,0):'k'}|pieces
    if white:
        pieces={(10-f,8-r):p.swapcase() for (f,r),p in pieces.items()}
        hand=hand.swapcase()
    rows=[]
    for r in range(9):
        row='';empty=0
        for f in range(9,0,-1):
            p=pieces.get((f,r))
            if p is None:empty+=1
            else:
                if empty:row+=str(empty);empty=0
                row+=p
        if empty:row+=str(empty)
        rows.append(row)
    return '/'.join(rows)+(' w ' if white else ' b ')+hand+' 1'

def quantity(state,owner,include_hand):
    board=sum(p is not None and p.owner==owner and p.current_type_id!='K' for p in state.position.board)
    hand=sum(n for t,n in state.position.hands[owner].counts if t!='K') if include_hand else 0
    return board+hand

def material(state):
    return sum((1 if p.owner==0 else -1)*PRICES[p.current_type_id] for p in state.position.board if p is not None)+sum((1 if side==0 else -1)*PRICES[t]*n for side,hand in enumerate(state.position.hands) for t,n in hand.counts)

def difference(state,owner,include_hand):return quantity(state,owner,include_hand)-quantity(state,1-owner,include_hand)
compiled=compile_ruleset_for_execution(build_standard_shogi_ruleset())
rows=[];probes=[]
for white in [False,True]:
    owner=int(white)
    for t in TYPES:
        guard(); fen=sfen({(5,3):TOKENS.get(t,t)},white=white)
        state=sfen_to_gc_state(compiled,fen)
        assert material(state)*(1 if owner==0 else -1)==PRICES[t]
        probes.append({'kind':'board','type':t,'owner':owner,'sfen':fen,'expected_raw_e':PRICES[t]})
    for t in ['P','L','N','S','B','R','G']:
        guard();fen=sfen({},hand=t,white=white);state=sfen_to_gc_state(compiled,fen)
        assert material(state)*(1 if owner==0 else -1)==PRICES[t]
        probes.append({'kind':'hand','type':t,'owner':owner,'sfen':fen,'expected_raw_e':PRICES[t]})
    cases=[]
    for t in TYPES:cases.append(('capture_'+t,{(5,4):'G',(5,3):TOKENS.get(t,t).lower()},'-','5e5d',t))
    for t in ['P','L','N','S','B','R']:
        target='4b' if t=='N' else '4c' if t=='B' else '5c'
        cases.append(('promotion_'+t,{(5,3):t},'-','5d'+target+'+',t))
    for t in ['P','L','N','S','B','R','G']:cases.append(('drop_'+t,{},t,t+'*5d',t))
    for name,pieces,hand,usi,t in cases:
        guard();fen=sfen(pieces,hand,white)
        if white:
            def flip_sq(v):return str(10-int(v[0]))+chr(ord('a')+8-(ord(v[1])-ord('a')))
            if '*' in usi:usi=usi[:2]+flip_sq(usi[2:4])
            else:usi=flip_sq(usi[:2])+flip_sq(usi[2:4])+('+' if usi.endswith('+') else '')
        state=sfen_to_gc_state(compiled,fen)
        actions=legal_actions(state,compiled);matching=[a for a in actions if gc_action_to_usi(a)==usi]
        assert len(matching)==1,(name,white,usi,fen)
        child=apply_action(state,matching[0],compiled)
        unit_before=difference(state,owner,True);unit_after=difference(child,owner,True)
        board_before=difference(state,owner,False);board_after=difference(child,owner,False)
        expected=2 if name.startswith('capture') else 0
        assert unit_after-unit_before==expected
        expected_board=1 if name.startswith(('capture','drop')) else 0
        assert board_after-board_before==expected_board
        delta=(material(child)-material(state))*(1 if owner==0 else -1)
        if name.startswith('capture'):value=PRICES[t]+PRICES[BASE.get(t,t)]
        elif name.startswith('promotion'):value=PRICES['T'+t]-PRICES[t]
        else:value=0
        assert delta==value,(name,delta,value)
        rows.append({'case':name,'owner':owner,'sfen':fen,'usi':usi,'legal_action_count':len(actions),'child_sfen':gc_to_sfen(child,compiled),'material_delta':delta,'board_plus_hand_delta':unit_after-unit_before,'board_only_delta':board_after-board_before})
# Future cheap standard-start Shogi cutoff denominator is 38 nonroyal actors,
# independent of prices. This is a declared proposal, not a running evaluator.
initial=sfen_to_gc_state(compiled,'lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1')
assert quantity(initial,0,True)==quantity(initial,1,True)==19
files={str(p):hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['generic_chess/rules/standard_shogi.py','generic_chess/learning/shogi_rules.py','generic_chess/core/movegen.py','generic_chess/core/transition.py']}
result={'complete':True,'backend':'PROJECT_CORE_RULES_ONLY; NOT_MATURE_SEARCH','source_hashes':files,'ruleset_fingerprint':compiled.ruleset_fingerprint,'synthetic_prices':PRICES,'probes':probes,'probe_count':len(probes),'legal_transition_witnesses':rows,'legal_transition_count':len(rows),'initial_nonroyal_actors':38,'proposed_cutoff_quantity':'(owned board+hand actors - opponent board+hand actors)/38','mature_games_executed':0,'mature_search_calls':0,'wall_seconds':time.perf_counter()-started,'scope':['52 one-action PROJECT_CORE legality/material bookkeeping checks, not games, external parity or learning.','40 future raw e probe expectations, not executed USI parameter acceptance. Require binding to the actual supplied source/build and both signs before actual qualification.','Board-only reward improves merely by dropping a held piece; board+hand reward is invariant under drop and promotion and increases by2 under capture.','Equal unit reward does not identify piece ratios or promotion values by itself; future behavioral evidence is necessary.','Standard-game terminal/perpetual-check/declaration authority and history require separate actual adapter validation; these fixtures do not certify them.']}
(OUT/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
print(json.dumps({k:result[k] for k in ['backend','probe_count','legal_transition_count','wall_seconds','mature_games_executed']}))