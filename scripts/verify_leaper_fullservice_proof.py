"""Saved return/actual Core PV reader; no new Player/proof search."""
from pathlib import Path
from datetime import datetime
import json,hashlib
from copy import copy
import importlib.util,sys

def load_reference(directory,hashes):
    directory=Path(directory)
    for name in ('generic_win_proof','generic_session_win_proof','generic_session_win_proof_pn'):
        path=directory/(name+'.py');assert hashlib.sha256(path.read_bytes()).hexdigest()==hashes[path.name]
        fullname='scripts.'+name
        if fullname in sys.modules:
            assert Path(sys.modules[fullname].__file__).resolve()==path.resolve()
            continue
        spec=importlib.util.spec_from_file_location(fullname,path);module=importlib.util.module_from_spec(spec);sys.modules[fullname]=module
        spec.loader.exec_module(module)
    return sys.modules['scripts.generic_session_win_proof_pn'],sys.modules['scripts.generic_session_win_proof']
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.verify_leaper_pvs_quality_pilot import action
from scripts.research_record import record_value,write_record

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def independent_certificate(session,raw,proof):
 assert raw['ruleset_fingerprint']==session.compiled.ruleset_fingerprint
 assert raw['root_record']==record_value(session.to_record()) and raw['root_state']==record_value(session.state)
 direct=[0]
 def tree(current,node):
  assert node['terminal']==record_value(current.result) if current.result.status.value!='ongoing' else node['terminal'] is None
  edges=[]
  for choice,child in node['edges']:
   if choice['kind']=='ACTION':c=proof.SessionChoice('ACTION',action=action(choice['action'],current))
   else:c=proof.SessionChoice('DECLARATION',declaration_id=choice['declaration_id'])
   after=type(current).replay(current.compiled,current.to_record());proof.execute(after,c);direct[0]+=1
   edges.append((c,tree(after,child)))
  return proof.SessionProofNode(node['rank'],tuple(edges),current.result if node['terminal'] is not None else None)
 cert=proof.SessionWinCertificate(raw['ruleset_fingerprint'],session.to_record(),session.state,raw['target'],tree(session,raw['tree']))
 receipt=proof.verify_session_certificate(session,cert,max_nodes=200000,seconds=2.)
 assert receipt['verified'],receipt
 return dict(checker=receipt,direct_conversion_Core_edges=direct[0])

def verify(base,output,reference_directory=None):
 b=Path(base);o=b/'study';p=json.loads((o/'protocol.json').read_text());rows=json.loads((o/'literal-before-Core.json').read_text())['rows'];assert sha(o/'literal-before-Core.json')==p['inputs_sha256']
 calls=[];pvs=0;proofwins=[];outerwall=innerwall=0;independent=[]
 _,proof=load_reference(reference_directory or b/'reference',p['reference']['files'])
 for i,f in enumerate(sorted(o.glob('return-*.json'))):
  r=json.loads(f.read_text());assert r['slot']==i;ri=r['root'];on=r['on'];assert ri==i//2 and on==((i%2==1) if ri%2==0 else (i%2==0));c,s=make_session(rows[ri]);assert record_value(s.to_record())==r['record_before'];d=r['decision'];elapsed=(datetime.fromisoformat(r['ended_at'])-datetime.fromisoformat(r['started_at'])).total_seconds();assert elapsed>=d['wall_seconds']-.01;outerwall+=elapsed;innerwall+=d['wall_seconds']
  if not on:assert d['proof'] is None and d['verification'] is None
  if d['normal']:
   n=d['normal'];assert n['runtime_depth_balanced'] and n['native_legality_fallbacks']==n['native_legality_operational_failures']==0 and d['phase_seconds']['native_provider_present']
   clone=type(s).replay(c,s.to_record())
   for a in n['principal_variation']:clone.submit(action(a,clone));pvs+=1
   if d['choice']:
    assert d['choice'][0] in ('ACTION','DECLARATION')
    if d['choice'][0]=='ACTION':assert d['choice'][1]==n['action'];assert action(n['action'],s) in s.legal_actions()
    else:assert d['choice'][1]==n['declaration']
  if d['source']=='VERIFIED_PROOF':
   assert on and d['proof']['status']=='PROVEN_WIN' and d['verification']['verified'] and d['certificate']==d['proof']['certificate'];assert d['certificate']['root_record']==r['record_before'];proofwins.append(ri);assert d['certificate']['target']==s.state.position.side_to_move;independent.append(independent_certificate(s,d['certificate'],proof))
  calls.append(r)
 s=json.loads((o/'summary.json').read_text());assert s['returns']==len(calls) and s['NOT_RUN']==list(range(len(calls),32))
 posts=[json.loads(f.read_text()) for f in sorted(o.glob('post-[0-9][0-9].json'))];strict=[]
 for r in posts:
  ri=r['root'];baseline=next(x for x in calls if x['root']==ri and not x['on']);c,ses=make_session(rows[ri]);chosen=baseline['decision']['choice'];assert r['baseline_return_slot']==baseline['slot']
  if 'baseline_child_record' in r:
   ses.submit(action(chosen[1],ses));assert record_value(ses.to_record())==r['baseline_child_record'];assert record_value(ses.result)==r['Core_terminal']
  if r['status']=='BASELINE_ACTION_CERTIFIED_LOSS':
   independent.append(independent_certificate(ses,r['proof']['certificate'],proof))
   assert r['proof']['status']=='PROVEN_WIN' and r['verification']['verified'] and r['root_actor_action_interval']==[-1,-1]
  if ri in proofwins and r['root_actor_action_interval'][1]<1:strict.append(ri)
 relative=[]
 for ri in range(16):
  pair=[next((x for x in calls if x['root']==ri and x['on']==on),None) for on in (False,True)]
  if not all(pair):relative.append(dict(root=ri,status='MISSING',difference_interval=[-2,2]));continue
  off,on=[x['decision'] for x in pair];post=next((x for x in posts if x['root']==ri),None)
  if off['choice'] and off['choice']==on['choice']:relative.append(dict(root=ri,status='IDENTICAL_FULL_TYPED_CHOICE',difference_interval=[0,0]));continue
  c,original=make_session(rows[ri])
  def actual_one_step_value(d):
   choice=d['choice']
   if not choice:return None
   if isinstance(choice,dict):kind=choice['kind'];raw=choice.get('action');did=choice.get('declaration_id')
   else:kind=choice[0];raw=choice[1];did=raw.get('declaration_id') if kind=='DECLARATION' else None
   child=type(original).replay(c,original.to_record())
   if kind=='ACTION':child.submit(action(raw,child))
   else:child.declare(did)
   if child.result.status.value=='ongoing':return None
   if child.result.winner is None:return 0
   return 1 if child.result.winner==original.state.position.side_to_move else -1
  offval=actual_one_step_value(off);onval=1 if ri in proofwins else actual_one_step_value(on)
  offbounds=post['root_actor_action_interval'] if post and 'root_actor_action_interval' in post else [-1,1]
  if offval is not None:offbounds=[offval,offval]
  onbounds=[onval,onval] if onval is not None else [-1,1]
  relative.append(dict(root=ri,status='VERIFIED_BOUNDS_OR_UNKNOWN',OFF=offbounds,ON=onbounds,difference_interval=[onbounds[0]-offbounds[1],onbounds[1]-offbounds[0]]))
 families=sorted({rows[ri]['family'] for ri in strict});allcoverage=len(calls)==32 and len(posts)==16 and len({rows[x['root']]['family'] for x in calls})==8;gate=allcoverage and len(families)>=2
 result=dict(status='PASS_SCOPED_VERIFIED_GAIN' if gate else 'NO_GO_OR_INCONCLUSIVE',returns=len(calls),planned=32,NOT_RUN=s['NOT_RUN'],pairs=sum(any(x['root']==ri and x['on'] for x in calls) and any(x['root']==ri and not x['on'] for x in calls) for ri in range(16)),literal_Core_PV_plies=pvs,verified_candidate_win_roots=proofwins,strict_gain_roots=strict,strict_gain_families=families,relative_action_bounds=relative,identical_choice_roots=[r['root'] for r in relative if r['status']=='IDENTICAL_FULL_TYPED_CHOICE'],potential_positive_families=sorted({rows[r['root']]['family'] for r in relative if r['difference_interval'][1]>0}),complete_coverage=allcoverage,caller_UTC_envelope_seconds=outerwall,reported_inner_seconds=innerwall,unreported_final_assertion_residual_seconds=outerwall-innerwall,postassessment_rows=len(posts),independent_certificate_replay=independent,new_Player=0,new_proof_search=0,limits='Exposed newdevelopment combinations;sharedCore/source not independentimplementation. Positive certificates independently reconstructed through publicCore and replaychecker;sharedCore/checker not independent implementation. InnerCPU excludesfinally assertion;wholeUTCenvelope retained. PNallocation+terminationjointpolicy versus defaultAB,not anywinoptimalbaseline. UNKNOWNnotDRAW;no games/default/classstrength.')
 write_record(output,result);print(json.dumps(result));return result
if __name__=='__main__':
 import sys;verify(sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)>3 else None)
