"""All-edge model equivalence over the independently defined finite rule trees.

New structural check, not a continuation/relabel of any capped WDL experiment.
Reference execution enumerates public Session choices independently of model.
"""
from copy import copy
from dataclasses import replace
from pathlib import Path
import json,time,hashlib
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleDeclaration
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof_batch_pn import _Forward,_children
from scripts.generic_session_win_proof import SessionChoice
from scripts.generic_win_proof import _Budget,_same_state
OUT=Path('results/dev_aux/task1832')
reference=json.loads(Path('results/dev_aux/task1830/plan.json').read_text());base=deserialize_ruleset(Path(reference['parent_rules']).read_text());roots=json.loads(Path('results/dev_aux/task1822/qualification.json').read_text())['roots']
plan=dict(reference_plan_sha=hashlib.sha256(Path('results/dev_aux/task1830/plan.json').read_bytes()).hexdigest(),cases=16,seconds_cap=180,max_nodes=100000,question='Are every batched child full state/history/record/SessionResult identical to independent actual Session execution over all reachable nodes in these16frozen maxply4games?',scope='Exposed finite model equivalence, no new WDLlabels/training/Native or default adoption')
with (OUT/'plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2)
profiles={'NONE':(), 'DEFENDER_RESTART':(RuleDeclaration('restart',1,require_not_in_check=False,failure_outcome='RESTART'),), 'DEFENDER_LOSS':(RuleDeclaration('loss',1,require_not_in_check=False,failure_outcome='LOSS'),), 'ACTOR_WIN':(RuleDeclaration('win',0,require_not_in_check=False,failure_outcome='WIN'),)}
start=time.perf_counter();rows=[];nodes=edges=frontiers=claims=0
for family in reference['families']:
    for profile in reference['profiles']:
        c=compile_ruleset_for_execution(replace(base,max_ply=4,declarations=profiles[profile]));s=GameSession(c,roots[family]['setup']);local=[0,0,0,0]
        def walk(current):
            global nodes,edges,frontiers,claims
            nodes+=1;local[0]+=1;assert nodes<=plan['max_nodes'] and time.perf_counter()-start<plan['seconds_cap']
            if current.result.status is not SessionStatus.ONGOING:return
            before=current.to_record();model=_Forward(c,current.state,before,current.result);cost=[0,0]
            built=dict(_children(model,_Budget(65536,30.,None),cost));expected=[]
            for d in c.declarations:
                if d.owner==current.state.position.side_to_move:expected.append(SessionChoice('DECLARATION',declaration_id=d.declaration_id))
            expected += [SessionChoice('ACTION',action=a) for a in current.legal_actions()]
            assert len(expected)==len(built) and set(expected)==set(built)
            frontiers+=1;local[2]+=1
            for choice in expected:
                actual=copy(current)
                if choice.kind=='DECLARATION':actual.declare(choice.declaration_id);claims+=1;local[3]+=1
                else:actual.submit(choice.action)
                candidate=built[choice]
                assert _same_state(candidate.state,actual.state) and _same_state(candidate.record,actual.to_record()) and _same_state(candidate.result,actual.result)
                edges+=1;local[1]+=1;walk(actual)
            assert _same_state(current.to_record(),before)
        walk(s);rows.append(dict(family=family,profile=profile,nodes=local[0],edges=local[1],frontiers=local[2],claims=local[3]))
out=dict(status='PASS_ALL_REACHABLE_EDGES',cases=rows,nodes=nodes,edges=edges,frontiers=frontiers,claims=claims,seconds=time.perf_counter()-start,no_rule_or_reward_changes=True)
with (OUT/'result.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2)
print(json.dumps({k:v for k,v in out.items() if k!='cases'}))
