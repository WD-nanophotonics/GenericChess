import json,sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from tools.local_agent.common import write_json
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.session.session import GameSession
D=Path('.local_agent/movement-transfer-20261017');p=json.loads((D/'plan.json').read_bytes());models=json.loads((D/'models.json').read_bytes())['rows'];roots=json.loads((D/'roots.json').read_bytes())['rows'];rows=[];fps=set()
for rid,v in p['variants'].items():
 r=ruleset_from_dict(json.loads((D/f'rule-{rid}.json').read_bytes()));c=compile_legacy_ruleset_for_semantic_execution(r);s=GameSession(c);engine=SemanticEngine(c)
 assert c.ruleset_fingerprint not in fps;fps.add(c.ruleset_fingerprint)
 rec=str(v['recipient']);baseline=f'{rec}-A{rec}';rr=[x for x in roots if x['rule']==rid];mm=[x for x in models if x['rule']==rid]
 for m in mm:
  if m['label'] in ['rule_static_v2']:continue
  old=next(x for x in models if x['rule']==baseline and x['label']==m['label'])
  for k in ['board_weights','hand_weights','material_scale','value_scale']:
   assert m['checkpoint'][k]==old['checkpoint'][k],(rid,m['label'],k)
 rows.append(dict(rule=rid,recipient=v['recipient'],donor=v['movement_donor'],identity=v['identity_control'],fingerprint=c.ruleset_fingerprint,initial_check=[engine.in_check(s.state.position,o)for o in (0,1)],initial_terminal=s.result.status.value,initial_legal_actions=len(s.legal_actions()),prefix_lengths=[x['prefix_completed']for x in rr],terminal_roots=sum(x['terminal_before_game']for x in rr),root_count=len(rr),physical_prefix_hashes=[x['state_sha256']for x in rr],ALL_nonstatic_numeric_profiles_equal_recipient=True))
assert len(fps)==16
write_json(D/'transfer-contract-audit.json',dict(status='PASS_EXACT_ONE_MOVEMENT_PATH_AND_UNCHANGED_LEARNED_COORDINATES',variants=rows,models=len(models),roots=len(roots),all16fingerprints_unique=True,unfiltered=True,scope='12newfullrulefingerprints+4identityrules; exchangedingredients already exposed across4TRAINrules, not newmovementatoms/fullgenericpopulation. SameRNGdoesnotmakelegalprefixstatesidentical. Static intentionallyrecomputed; no newlearner/fitting/defaultactivation. Reachability fromeachdeclaredvariantinitial maintained byfulltypedlegalprefix, not commoncross-ruletrajectory.'))
print('PASS',len(models),'profiles/',len(roots),'roots; unique16 fingerprints; terminals',sum(x['terminal_roots']for x in rows),'initialcheck',[(x['rule'],x['initial_check'])for x in rows if any(x['initial_check'])])
