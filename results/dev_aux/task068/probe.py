import copy,importlib.util,json,sys
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'.local_agent/pinned_bebe'));B=Path(__file__).resolve().parent
from native_initial_fixture import _initial
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
spec=importlib.util.spec_from_file_location('generic_chess.native._aux_binding',R/'results/dev_aux/task066/proposed_native_binding.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);C=m.SemanticSearchEngine
c,n,_=_initial();s=GameSession(c);state=s.state;w=tuple(s._search_witnesses);zeros={t:0 for t in n.type_ids};model=json.loads((R/'results/dev_aux/task065/result.json').read_bytes())['rows'][0]['values']['compact_nonlinear'];model['output_bias']=100.;bad=copy.deepcopy(model);bad['width']=17
cp=LearnableMaterialCheckpoint(ruleset_fingerprint=c.ruleset_fingerprint,board_weights=zeros,hand_weights=zeros,compact_nonlinear=bad);cp.validate_ruleset(c)
p=C(c,n,board_values=zeros,hand_values=zeros,tt_megabytes=1,evaluator_scale=1);old=p._capsule;oldvalues=copy.deepcopy(p.native_evaluator_values);oldid=p.checkpoint_id
try:p.bind_checkpoint(cp);raise AssertionError('C bad width accepted')
except ValueError as e:rejection=str(e)
assert p._capsule is old and p.native_evaluator_values!=oldvalues and p.checkpoint_id==cp.checkpoint_id
p.bind_checkpoint(cp);assert p._capsule is old
limits=SearchLimits(max_depth=1,max_nodes=1000,max_time_seconds=1,quiescence_max_depth=0);v=p.search(s,limits);assert v.score==0 and v.completed_depth==1
class Fixed(C):
 def _set_checkpoint_values(self,checkpoint):
  super()._set_checkpoint_values(checkpoint);self._compact_values=copy.deepcopy(self._compact_values)
 def _set_ordering_checkpoint_values(self,checkpoint):
  super()._set_ordering_checkpoint_values(checkpoint);self._ordering_compact_values=copy.deepcopy(self._ordering_compact_values)
 def bind_checkpoint(self,checkpoint):
  checkpoint.validate_ruleset(self._compiled)
  if checkpoint.checkpoint_id==self._checkpoint_id:return
  staged=object.__new__(type(self));staged.__dict__=self.__dict__.copy();staged._set_checkpoint_values(checkpoint);staged._capsule=staged._new_capsule();self.__dict__.update(staged.__dict__)
f=Fixed(c,n,board_values=zeros,hand_values=zeros,tt_megabytes=1,evaluator_scale=1);fc=f._capsule;fv=copy.deepcopy(f.native_evaluator_values);fid=f.checkpoint_id
try:f.bind_checkpoint(cp);raise AssertionError('bad accepted')
except ValueError:pass
assert f._capsule is fc and f.native_evaluator_values==fv and f.checkpoint_id==fid
valid=LearnableMaterialCheckpoint(ruleset_fingerprint=c.ruleset_fingerprint,board_weights=zeros,hand_weights=zeros,compact_nonlinear=model);f.bind_checkpoint(valid);assert f._capsule is not fc
owned=copy.deepcopy(f._compact_values);valid.compact_nonlinear['hidden_bias'][0]=50.;assert f._compact_values==owned
new=f.search(s,limits);assert new.completed_depth==1 and new.score==100*f.native_evaluator_values['scale']
assert s.state==state and tuple(s._search_witnesses)==w
out={'complete':True,'C_rejection':rejection,'genuine_checkpoint_rules_validation_passed':True,'original_candidate_metadata_drift':True,'same_rejected_ID_retry_silently_skipped':True,'old_capsule_search_score':v.score,'private_staged_candidate_preserves_fields_ID_capsule':True,'valid_commit_score':new.score,'valid_commit_scale':f.native_evaluator_values['scale'],'checkpoint_nested_input_owned':True,'scope':'Two actual D1 searches andtwo C rejection attempts;not same-ID corrected-content proof because actual public ID hashes payload;not ordering execution/concurrency/allocator certification.'};(B/'result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());(B/'proposed_checkpoint_boundary.py').write_bytes(__import__('inspect').getsource(Fixed).encode());print(json.dumps(out))
