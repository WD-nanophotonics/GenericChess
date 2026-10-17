"""Bounded signed/zero board-P deployment control on existing exposed records."""
from pathlib import Path
from dataclasses import replace
import hashlib,json,sys,time
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.semantic import evaluate
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.core.transition import apply_action,legal_actions
from generic_chess.ai.limits import SearchLimits
from scripts.research_record import record_value


def consume(output):
    directory=ROOT/'docs/research/data/aux89_native_candidates_20261017'
    index=json.loads((directory/'index.json').read_bytes())
    compiled={};native={};models={};rows=[];visits=0;start=time.monotonic()
    variants=(-1.,0.,1.)
    def poll():
        if time.monotonic()-start>=180 or visits>=200000:
            raise TimeoutError('Frozen signed-price diagnostic cap')
        for name in ('rollout','advisor','slack'):
            path=ROOT/'.local_agent'/(name+'.json')
            if path.exists():
                flags=json.loads(path.read_bytes())
                if flags.get('stopped') or flags.get('user_paused'):
                    raise InterruptedError('User stop')
    for entry in index['rules']:
        raw=(directory/entry['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==entry['public_sha256']
        c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(json.loads(raw)))
        compiled[entry['generator_seed']]=c
        native[entry['generator_seed']]=compile_native_semantic_rules(c)
    for entry in index['models']:
        if entry['label']!='trained':continue
        cp=LearnableMaterialCheckpoint.from_dict(json.loads((directory/entry['path']).read_bytes()))
        assert cp.checkpoint_id==entry['checkpoint_id']
        models[entry['generator_seed'],entry['seed']]=cp
    for root in index['roots']:
        poll();gs,seed=root['generator_seed'],root['seed'];c=compiled[gs];n=native[gs]
        session=GameSession.replay(c,deserialize_game_record((directory/root['path']).read_text(encoding='utf8')))
        parent=(session.state,session.to_record(),session.history,session._search_witnesses)
        base=models[gs,seed];profiles=[]
        for value in variants:
            cp=replace(base,board_weights={**base.board_weights,'P':value})
            cp=LearnableMaterialCheckpoint.from_dict(cp.to_dict());cp.validate_ruleset(c)
            assert cp.board_weights['P']==value
            assert cp.hand_weights==base.hand_weights
            assert all(cp.board_weights[t]==w for t,w in base.board_weights.items()if t!='P')
            assert cp.reference_median==base.reference_median and cp.value_scale==base.value_scale
            profiles.append(cp)
        def material(state,cp):
            p=state.position
            board=sum((1 if x.owner==0 else -1)*round(cp.board_weights.get(x.current_type_id,0.)*256)
                      for x in p.board if x is not None)
            hand=sum((p.hands[0].count(t)-p.hands[1].count(t))*round(w*256)
                     for t,w in cp.hand_weights.items())
            return (board+hand)/256
        def walk(state,depth):
            nonlocal visits
            visits+=1
            if visits%64==0:poll()
            terminal=state.terminal_status
            if terminal.is_terminal:
                return [0. if terminal.winner is None else 1e6 if terminal.winner==0 else -1e6]*3
            if not depth:return [material(state,cp)for cp in profiles]
            children=[walk(apply_action(state,a,c),depth-1)for a in legal_actions(state,c)]
            assert children
            fn=max if state.position.side_to_move==0 else min
            return [fn(child[i]for child in children)for i in range(3)]
        actions=session.legal_actions();scores=[walk(apply_action(session.state,a,c),1)for a in actions]
        fn=max if session.state.position.side_to_move==0 else min
        best=[fn(x[i]for x in scores)for i in range(3)]
        optimal=[[a for a,values in zip(actions,scores)if abs(values[i]-best[i])<1e-9]for i in range(3)]
        for i,cp in enumerate(profiles):
            poll();packed=pack_semantic_search_position(c,n,session)
            raw=evaluate(n,packed,board_values=cp.semantic_quantized_board(n.type_ids),
                         hand_values=cp.semantic_quantized_hand(n.type_ids),evaluator_scale=256)
            owner0=raw*(1 if session.state.position.side_to_move==0 else -1)/256
            expected=material(session.state,cp);assert owner0==expected
            result=SemanticSearchEngine(c,n,checkpoint=cp,tt_megabytes=0).search(session,
                SearchLimits(max_depth=2,max_nodes=8192,max_time_seconds=2.,quiescence_max_depth=0),
                root_window_pruning=False)
            assert parent==(session.state,session.to_record(),session.history,session._search_witnesses)
            assert result.completed_depth==2 and not result.used_fallback
            assert result.action in optimal[i]
            rows.append(dict(rule=gs,seed=seed,root=root['which'],boardP=variants[i],
                checkpoint_id=cp.checkpoint_id,root_integer_material=owner0,core_best=best[i],
                score=result.score,action=record_value(result.action),
                completed_depth=result.completed_depth,nodes=result.nodes,
                used_fallback=result.used_fallback,quantized_optimal_membership=True,
                parent_record_hash=hashlib.sha256(json.dumps(record_value(session.to_record()),sort_keys=True).encode()).hexdigest()))
    assert len(rows)==48 and len(models)==8
    receipt=dict(status='PASS_SIGNED_ZERO_EXISTING_CONSUMER',models=len(models),roots=len(index['roots']),
        variants=list(variants),calls=len(rows),core_visits=visits,seconds=time.monotonic()-start,rows=rows,
        scope='Unfitted deployment-stress weights on four TRAIN-exposed rules; no new training/game/strength/unseen-rule/full-domain claim. Existing checkpoint loader and Native only; hand/base and complete history retained. Terminal coarse utility identifies legal finite-D2 optimal sets but does not assert raw mate-distance score equality. No normalization/clipping/new API/default.',
        no_aux_import=not any(k.startswith('results.dev_aux')for k in sys.modules))
    assert receipt['no_aux_import']
    with Path(output).open('x',encoding='utf8')as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in receipt.items()if k!='rows'}))
    return receipt

if __name__=='__main__':consume(sys.argv[1])
