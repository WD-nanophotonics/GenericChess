# Bound raw-model Native inference example

These32 existing-schema checkpoints retain all original AUX105 initial/final
weights, including signed hand values, and temperature10. Scale256 changes only
Native integer precision. Use exact RuleSet fingerprints and complete semantic
GameRecords; this is a finite inference qualification, not a selected champion,
training rerun, production default or universal quantization guarantee.

`inputs.json` supplies four exact published RuleSets and sixteen new fixed random
prefixes. Four are early terminals; do not treat them as failed inputs or search
them as continuing games. The record uses the existing explicit legacy-to-semantic
adapter, preserving complete history. A raw legacy history-key string is not a
semantic history key even though RuleSet fingerprints match.

Example, from repository root with the installed Native backend:

```python
from pathlib import Path
import json
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.ai.limits import SearchLimits

d = Path('docs/research/data/learned_native_inference_20261019')
inputs = json.loads((d / 'inputs.json').read_bytes())
artifact = json.loads((d / 'checkpoints.json').read_bytes())['entries'][0]
gs = int(artifact['model'].split('-')[0])
rule = next(r for r in inputs['rules'] if r['generator_seed'] == gs)
compiled = compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(rule['rule']))
cp = LearnableMaterialCheckpoint.from_dict(artifact['checkpoint'])
assert cp.checkpoint_id == artifact['checkpoint_id']
cp.validate_ruleset(compiled)
root = min((r for r in inputs['roots'] if r['generator_seed'] == gs
            and r['source_terminal']['status'] == 'ongoing'), key=lambda r: r['family'])
session = GameSession.replay(compiled, deserialize_game_record(json.dumps(root['semantic_record'])))
engine = SemanticSearchEngine(compiled, compile_native_semantic_rules(compiled),
                              checkpoint=cp, tt_megabytes=0)
result = engine.search(session, SearchLimits(max_depth=3, max_nodes=200000,
                       max_time_seconds=2, quiescence_max_depth=0), root_window_pruning=True)
```

The same file-loading/constructor/search path was actually exercised for all32
models, each at its prespecified first ongoing new root:18702 main visits, all
saved scalar/action/PV/depth/node fields matched constructed-object receipts.
There were96 wrong-rule fingerprint refusals and no new Core searches. Existing
Python material features/linear value/tanh(raw/10) also match the source contract
on384 model/root contexts across both panels. Raw terminal predictor algebra is
not a replacement for actual terminal targets.

Native scores are scaled integer search values. They have a separate terminal
band/distance convention; do not interpret them as WDL probabilities or demand
tie/PV identity with the original float AUX implementation. This example does
not invoke or modify an optimizer. Full limits, failures and provenance:
[research report](../../GLOBAL_STATE_AND_LEARNED_INFERENCE_20261019.md).
