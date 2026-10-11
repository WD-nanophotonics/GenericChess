"""Private staged-binding candidate; tests Python/C rejection and successful commit."""
import ast,copy,hashlib,json,sys
from pathlib import Path
ROOT=Path.cwd();E=ROOT/'.local_agent/pinned_bebe';sys.path.insert(0,str(E));B=Path(__file__).resolve().parent
from native_initial_fixture import _initial
from generic_chess.native import semantic_engine as eng
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from scripts.research_record import record_value
raw=(E/'generic_chess/native/semantic_engine.py').read_text();tree=ast.parse(raw);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='SemanticSearchEngine');original=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='bind_evaluator');ns=dict(eng.__dict__);exec(compile(ast.Module(body=[copy.deepcopy(original)],type_ignores=[]),'<original private binding>','exec'),ns);ns['_original_bind']=ns['bind_evaluator']
wrapper=ast.parse("""def bind_evaluator(self, board_values, hand_values, dynamic_values=None, spatial_occupancy_values=None, localized_control_values=None, compact_values=None, *, evaluator_scale=1):
    staged = object.__new__(type(self))
    staged.__dict__ = self.__dict__.copy()
    _original_bind(staged, board_values, hand_values, dynamic_values, spatial_occupancy_values, localized_control_values, compact_values, evaluator_scale=evaluator_scale)
    self.__dict__.update(staged.__dict__)
""").body[0]
cls.body=[wrapper if n is original else n for n in cls.body];exec(compile(ast.Module(body=[cls],type_ignores=[]),'<private staged-binding class>','exec'),ns);Candidate=ns['SemanticSearchEngine'];(B/'proposed_bind_evaluator.py').write_text(ast.unparse(wrapper)+'\n',encoding='utf-8');(B/'binding_reference.py').write_text(ast.unparse(original)+'\n',encoding='utf-8')
c,n,packed=_initial();s=GameSession(c);before_state=s.state;w=tuple(s._search_witnesses);zeros={t:0 for t in n.type_ids};mapping={f'{o}:{t}':(0,)*9 for o in (0,1) for t in n.type_ids};mapping['0:P']=(-1,-1,-1,1,1,1,0,0,0);limits=SearchLimits(max_depth=1,max_nodes=1000,max_time_seconds=1,quiescence_max_depth=0)
p=Candidate(c,n,board_values=zeros,hand_values=zeros,tt_megabytes=0);old=p._capsule;values=copy.deepcopy(p.native_evaluator_values);rows=[]
for case,kwargs in [('invalid_python_scale',{'evaluator_scale':0}),('invalid_c_profile',{'compact_values':{}})]:
 try:p.bind_evaluator(zeros,zeros,spatial_occupancy_values=mapping,**kwargs);raise AssertionError('invalid bind accepted')
 except ValueError as e:error={'type':type(e).__name__,'message':str(e)}
 assert p._capsule is old and p.native_evaluator_values==values
 v=p.search(s,limits);assert v.score==0 and v.completed_depth==1
 rows.append(dict(case=case,rejection=error,metadata_preserved=True,capsule_preserved=True,decision=record_value(v)))
p.bind_evaluator(zeros,zeros,spatial_occupancy_values=mapping,evaluator_scale=1);assert p._capsule is not old
v=p.search(s,limits);assert v.score==-6 and v.completed_depth==1;rows.append(dict(case='valid_commit',new_capsule=True,decision=record_value(v),values=copy.deepcopy(p.native_evaluator_values)))
assert s.state==before_state and tuple(s._search_witnesses)==w
out=dict(complete=True,source_sha256=hashlib.sha256(raw.encode()).hexdigest(),rows=rows,product_class_unchanged=eng.SemanticSearchEngine is not Candidate,scope='Private candidate stages existing validator/capsule construction before commit;3actual D1 calls. Python scale and C compact-profile failures covered;not allocator-fault/concurrent-reader/complete immutable compact-profile certification.')
(B/'repair_result.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps([{'case':r['case'],'score':r['decision']['score']} for r in rows]))
