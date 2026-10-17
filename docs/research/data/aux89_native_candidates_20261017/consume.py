"""Use standard checkpoint/session APIs; no AUX import or learning code required."""
from pathlib import Path
import hashlib,json,sys,time
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.ai.limits import SearchLimits
from generic_chess.learning.serialization import stable_sha256
from scripts.research_record import record_value

def consume(output=None):
    directory=Path(__file__).resolve().parent
    index=json.loads((directory/'index.json').read_text(encoding='utf8'))
    compiled={};native={};models={};rows=[];start=time.perf_counter()
    for entry in index['rules']:
        path=directory/entry['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['public_sha256']
        c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(json.loads(path.read_text(encoding='utf8'))))
        compiled[entry['generator_seed']]=c
        native[entry['generator_seed']]=compile_native_semantic_rules(c)
    for entry in index['models']:
        cp=LearnableMaterialCheckpoint.from_dict(json.loads((directory/entry['path']).read_text(encoding='utf8')))
        assert cp.checkpoint_id==entry['checkpoint_id']
        assert cp.semantic_native_scale==256 and cp.value_scale==10.
        assert cp.dynamic_weights=={} and not cp.promoted_to_champion
        cp.validate_ruleset(compiled[entry['generator_seed']])
        models[entry['generator_seed'],entry['seed'],entry['label']]=cp
    for root in index['roots']:
        gs,seed=root['generator_seed'],root['seed'];c=compiled[gs]
        s=GameSession.replay(c,deserialize_game_record((directory/root['path']).read_text(encoding='utf8')))
        assert stable_sha256(record_value(s.state))==root['state_sha256']
        assert stable_sha256(record_value(s._search_witnesses))==root['witnesses_sha256']
        for expected in root['expected_native']:
            cp=models[gs,seed,expected['label']]
            before=(s.state,s.to_record(),s.history,s._search_witnesses)
            engine=SemanticSearchEngine(c,native[gs],checkpoint=cp,tt_megabytes=0)
            result=engine.search(s,SearchLimits(max_depth=2,max_nodes=8192,max_time_seconds=2.,quiescence_max_depth=0),root_window_pruning=False)
            assert before==(s.state,s.to_record(),s.history,s._search_witnesses)
            assert result.completed_depth==expected['completed_depth']==2
            assert result.action in s.legal_actions()
            assert json.dumps(record_value(result.action),sort_keys=True,separators=(',',':'))==expected['action']
            assert result.score==expected['score']
            rows.append(dict(rule=gs,seed=seed,root=root['which'],label=expected['label'],checkpoint_id=cp.checkpoint_id,score=result.score,action=record_value(result.action),completed_depth=result.completed_depth,nodes=result.nodes,used_fallback=result.used_fallback))
    receipt=dict(status='PASS_EXISTING_BACKEND_CHECKPOINT_PACKET',models=len(models),rules=len(compiled),full_semantic_roots=len(index['roots']),native_queries=len(rows),no_aux_import=not any(k.startswith('results.dev_aux')for k in sys.modules),rows=rows,seconds=time.perf_counter()-start,scope='Research-only floating model -> explicit existing256 quantization; TRAIN-exposed source roots, not a new game/learning/strength/unseenrule/all-domain converter or default/champion promotion. Source coefficients unchanged; no fake dynamic tables. Native extension remains external.')
    assert receipt['no_aux_import']
    if output is not None:
        Path(output).write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
    print(json.dumps({k:v for k,v in receipt.items()if k!='rows'}))
    return receipt

if __name__=='__main__':
    consume(sys.argv[1]if len(sys.argv)>1 else None)
