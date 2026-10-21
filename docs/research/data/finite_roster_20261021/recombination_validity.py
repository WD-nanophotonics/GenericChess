"""Diagnose frozen recombination setup failures; never play or repair them."""
from dataclasses import replace
from pathlib import Path
import json, sys, time
from generic_chess.core.movement import RayAtom
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.schema import RuleReplaceSelector, RulePathConstraint, ruleset_to_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.validation import RuleValidationError
sys.path.insert(0,str(Path.cwd()/'tests'))
from rule_semantics_ir_fixtures import cannon_ruleset

OUT=Path(__file__).resolve().parent/'attack-utility'
original=json.loads((OUT/'rules.json').read_text())
plan={'question':'Which changed premise causes the four invalid initial setups: orthogonal geometry, one-screen capture, or their interaction?',
 'data':'Same eight frozen substrates/actor type/initial states as the closed utility panel; posthoc compile-only factorial, no replacement seeds, repaired setup or games',
 'axes':{'geometry':['original atoms','orthogonal rays'],'capture':['original clear path','one screen']},
 'controls':'Unmodified substrate must compile; original-ray/clear-path semantic control preserves leaps. If no original ray exists, that factorial cell stays unsupported rather than invented.',
 'decision':'Any original-geometry screen failure demonstrates setup validation must follow semantic recomposition even without changed geometry. Invalid cells remain failures; do not call the valid subset full generated coverage.',
 'cap_seconds':60}
(OUT/'validity-plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
start=time.perf_counter();rows=[]
for r in original:
 seed,n,tid=r['seed'],r['board'],r['cannon_type']
 definition=generate_game(GeneratorConfig(seed=seed,board_size=n,setup_preset='bilateral_random',allow_hybrid=True)).ruleset
 compile_ruleset_for_execution(definition)
 assert definition.initial_position==__import__('generic_chess.rules.schema',fromlist=['ruleset_from_dict']).ruleset_from_dict(r['definition']).initial_position
 actor=next(p for p in definition.piece_types if p.type_id==tid)
 for geom in ('original','orthogonal'):
  for capture in ('clear','screen'):
   assert time.perf_counter()-start<60
   if geom=='original' and not any(isinstance(a,RayAtom) for a in actor.movement_atoms):
    rows.append({'seed':seed,'board':n,'type':tid,'geometry':geom,'capture':capture,'status':'unsupported_no_original_ray'})
    continue
   types=definition.piece_types if geom=='original' else tuple(replace(p,movement_atoms=tuple(RayAtom(d) for d in ((1,0),(-1,0),(0,1),(0,-1)))) if p.type_id==tid else p for p in definition.piece_types)
   patterns=tuple(replace(p,name='validity_probe_'+p.name,type_ids=(tid,),composition='replace_legacy',replace_selector=RuleReplaceSelector(type_ids=(tid,),action_family='board',target_relation=p.target_relation,geometry_kind='ray',replace_all_matching=True),path_constraints=(RulePathConstraint('path_count_eq',count=1),) if p.target_relation=='enemy' and capture=='screen' else (RulePathConstraint('path_clear'),)) for p in cannon_ruleset().semantic_actions)
   changed=replace(definition,piece_types=types,semantic_actions=patterns)
   try:
    compile_ruleset_for_execution(changed);status='compiled';error=None
   except RuleValidationError as exc:status='rejected';error=str(exc)
   if geom=='orthogonal' and capture=='screen':
    assert bool(error)==bool(r.get('compile_error'))
   rows.append({'seed':seed,'board':n,'type':tid,'geometry':geom,'capture':capture,'status':status,'error':error})
summary={f'{g}/{c}':{s:sum(x['geometry']==g and x['capture']==c and x['status']==s for x in rows) for s in ('compiled','rejected','unsupported_no_original_ray')} for g in ('original','orthogonal') for c in ('clear','screen')}
summary['elapsed_seconds']=time.perf_counter()-start
(OUT/'validity-result.json').write_text(json.dumps({'plan':plan,'summary':summary,'cells':rows},indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
