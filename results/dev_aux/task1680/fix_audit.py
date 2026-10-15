from pathlib import Path
import json,ast,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1680'
s=(O/'audit.py').read_text(encoding='utf-8-sig').replace('task1683','task1687')
anchor="sp=importlib.util.spec_from_file_location('T',R/plan['model']);T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)"
s=s.replace(anchor,anchor+"\nsp2=importlib.util.spec_from_file_location('ON_T',R/'results/dev_aux/task1675/rules.py');ON_T=importlib.util.module_from_spec(sp2);sp2.loader.exec_module(ON_T)")
s=s.replace('len(T.moves(s))>=2','len(ON_T.moves(s))>=2').replace('assert not any(not T.moves(t) and T.attacked(t,T.king(t,t[16]),1-t[16]) for u,t in T.moves(s))','assert not any(not ON_T.moves(t) and ON_T.attacked(t,ON_T.king(t,t[16]),1-t[16]) for u,t in ON_T.moves(s))')
s=s.replace("  expect={(u,frame(t,True,False)) for u,t in []};assert T.valid(q);assert T.moves(q)==ref(q)","  assert T.valid(q);assert T.moves(q)==ref(q)")
(O/'audit_fixed.py').write_text(s,encoding='utf8');ast.parse(s)
plan=json.loads((O/'plan.json').read_bytes());sp=importlib.util.spec_from_file_location('OFF',O/'rules.py');OFF=importlib.util.module_from_spec(sp);sp.loader.exec_module(OFF)
cases=[{'family':f['family'],'ON_move_count':len(ON),'OFF_move_count':len(OFF.moves(tuple(f['roots'][0])))} for f in plan['families'] if len(OFF.moves(tuple(f['roots'][0])))<2 for ON in [dict(__import__('builtins').zip([],[]))]]
# Root selection belongs originalON; OFFcollapses promotionbranches, not controllerdefect.
fail=R/'results/dev_aux/task1683';(fail/'failure.json').write_text(json.dumps({'status':'AUDIT_ASSUMPTION_FAILURE_PRESERVED','cause':'Copiedrootlaw>=2evasions incorrectly assertedunderchangedOFFrule; originalON3promotionoptions collapse tooneOFFmove. NeedverifyONfrozenrootlaw+OFFvalidity, notreselectroots orrerungames.','cases':cases,'actual_new_go':0,'correction_source':'task1680/audit_fixed.py','correction_result':'task1687/result.json'},indent=2));print('OFF_ROOT_COLLAPSE',cases)
