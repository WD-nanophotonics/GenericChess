"""Bind existing published action certificates to a prospective decision consumer.
Data reader only: no Player, solver, source-capsule execution or AUX writes.
"""
from pathlib import Path
import json,gzip,hashlib,time
from datetime import datetime,timezone
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from tools.local_agent.common import write_json
from tools.local_agent import session

ORIGIN=Path('docs/research/data/leaper_lmr_20261025')
def digest(b):return hashlib.sha256(b).hexdigest()
def load_original(name,manifest):
 row=next(v for v in manifest['files']if v['file']==name);b=(ORIGIN/name).read_bytes();assert digest(b)==row['sha256'];raw=gzip.decompress(b);assert digest(raw)==row['original_sha256'];return json.loads(raw),dict(path=(ORIGIN/name).as_posix(),gzip_sha256=digest(b),raw_sha256=digest(raw))
def match(s,raw):
 if 'from_square'in raw:return L.match_action(s,raw)
 if raw.get('kind')not in(None,'board'):
  from generic_chess.core.actions import action_from_dict
  a=action_from_dict(raw);assert a in s.legal_actions();return a
 assert set(raw)<=set(('kind','from','to','promotion_target_id'))
 out=[a for a in s.legal_actions()if hasattr(a,'from_square')and [a.from_square.file,a.from_square.rank]==raw['from']and [a.to_square.file,a.to_square.rank]==raw['to']and a.promotion_target_id==raw.get('promotion_target_id')]
 assert len(out)==1;return out[0]
def key(raw):return json.dumps(raw,sort_keys=True,separators=(',',':'))
def verify_tail(c,s,paths,winner,counts):
 assert not session.stopped();counts[0]+=1;assert counts[0]<=100,'bounded supplied-tree check, no graph enumeration'
 if s.result.status.value!='ongoing':assert s.result.winner==winner and all(not p for p in paths);return
 assert all(paths);groups={}
 for p in paths:groups.setdefault(key(p[0]),[]).append(p[1:])
 actions={match(s,json.loads(k)):tail for k,tail in groups.items()}
 if s.state.position.side_to_move==winner:assert len(actions)==1
 else:assert set(actions)==set(s.legal_actions()),'missing literal defense'
 for a,tail in actions.items():
  child=replay(c,L.record_value(s.to_record()));child.submit(a);verify_tail(c,child,tail,winner,counts)
def bind(d):
 assert not d.exists();d.mkdir();started=datetime.now(timezone.utc).isoformat();tick=time.perf_counter();manifest=json.loads((ORIGIN/'manifest.json').read_text());origins=[]
 def read(name):
  v,ref=load_original(name,manifest);origins.append(ref);return v
 base=read('lmr-f538-inputs.json.gz');oldref=read('lmr-f538-reference-proof.json.gz');canonical=read('canonical-input-f538.json.gz');oldcanon=read('canonical-qualification-f538.json.gz');extra=read('extra-proof-qualification-f538.json.gz');old19=read('lmr-quality-f538-inputs.json.gz')
 cases=[]
 w=base['reference'];c=L.compile_rule(L.ruleset_from_dict(w['rules']));s=L.GameSession(c);record=L.record_value(s.to_record());assert record==oldref['full_record']and record['ruleset_fingerprint']==oldref['rule_fingerprint'];a=match(s,w['proof_paths'][0][0]);assert all(match(s,p[0])==a for p in w['proof_paths']);assert s.state.position.side_to_move==w['winner']
 cases.append(dict(key='horizontal3-root137',rule=w['rules'],record=record,root_actor=s.state.position.side_to_move,root_own_WDL=1,certified_actions=[dict(action=L.record_value(a),own_WDL=1,basis='Previously Core-qualified22-node all-defense strategy at exact fullhistory root; not rerun here')],other_actions='UNKNOWN in certificate tier; any source graph labels stay separately attributed',exposure='Known exposed root, not holdout',source_revision=w['source_revision']))
 pc=canonical['price_control'];c=L.compile_rule(L.ruleset_from_dict(canonical['rule']));s=replay(c,pc['root_record']);assert s.state.ply_count==oldcanon['root_ply']==17 and s.state.position.side_to_move==oldcanon['root_actor']==1;assert s.state.position.ruleset_fingerprint==oldcanon['rule_fingerprint'];assert pc['bad_action']==oldcanon['bad_action']and pc['safe_action']==oldcanon['safe_action'];bad=match(s,pc['bad_action']);safe=match(s,pc['safe_action']);child=replay(c,pc['root_record']);child.submit(safe);assert L.record_value(child.to_record())==pc['safe_record']
 cases.append(dict(key='canonical4-H128-p17',rule=canonical['rule'],record=pc['root_record'],root_actor=1,root_own_WDL='UNKNOWN_in_independent_certificate_tier',certified_actions=[dict(action=L.record_value(bad),own_WDL=-1,basis='Previously qualified2664-node opponentWIN strategy after this exact action'),dict(action=L.record_value(safe),own_WDL=0,basis='Previously qualified4264position/18720edge no-decisive closure under exact plainLeap/remove/H128/repeat4 scope')],other_actions='UNKNOWN; do not turn two named action certificates into complete root/all-action labels',exposure='Known exposed root/history/action contrast',source_revision=canonical['source_commit']))
 known={x['id']for x in old19['cases']};projection=[]
 for row in extra['rows']:
  c=L.compile_rule(L.ruleset_from_dict(row['rule']));root=replay(c,row['record']);proof=row['proof'];assert row['record']==proof['record'];prefixes={}
  for path in proof['leaf_paths']:
   for n in range(2,len(path)):prefixes[key(path[:n])]=path[:n]
  selected=None
  for _,prefix in sorted(prefixes.items(),key=lambda kv:(len(kv[1]),kv[0])):
   s=replay(c,row['record'])
   for raw in prefix:s.submit(match(s,raw))
   if s.result.status.value=='ongoing'and s.state.position.side_to_move==proof['winner']and L.state_sha(s.state)not in known:selected=(s,prefix);break
  assert selected,'no new exact-history interior available; do not synthesize one'
  s,prefix=selected;tails=[p[len(prefix):]for p in proof['leaf_paths']if p[:len(prefix)]==prefix];counts=[0];verify_tail(c,s,tails,proof['winner'],counts);a=match(s,tails[0][0]);assert all(match(s,t[0])==a for t in tails)
  record=L.record_value(s.to_record());case=dict(key='published-proof-interior-'+row['id'][:8],rule=row['rule'],record=record,state_sha256=L.state_sha(s.state),root_actor=s.state.position.side_to_move,root_own_WDL=1,certified_actions=[dict(action=L.record_value(a),own_WDL=1,basis='New finite supplied-strategy subtree replay at this literal history; all defender branches checked, no graph solver')],other_actions='UNKNOWN unless separately source-attributed',exposure='Prefrozen deterministic shortest/lexical supplied-proof prefix absent from specified old19root cohort; no claim universal unseen/holdout',prefix=prefix,source_root=row['id']);cases.append(case);projection.append(dict(key=case['key'],verified_nodes=counts[0],prefix_length=len(prefix),actual_ply=s.state.ply_count,rule_fingerprint=record['ruleset_fingerprint']))
 fingerprints={x['record']['ruleset_fingerprint']for x in cases}
 # Every consumer must retain original initial/rule fingerprints, history and clocks.
 for case in cases:
  c=L.compile_rule(L.ruleset_from_dict(case['rule']));s=replay(c,case['record']);assert L.record_value(s.to_record())==case['record']
  assert all(match(s,a['action'])in s.legal_actions()for a in case['certified_actions'])
 write_json(d/'inputs.json',dict(cases=cases,scope='Four exact-history cases from published action certificates, mixed label completeness. Not four fully labelled roots, not holdout or all-Leaper strength. No Player/solver calls.',origins=origins))
 write_json(d/'binding-assessment.json',dict(status='INPUTS_BOUND_NO_PLAYER',started_at=started,ended_at=datetime.now(timezone.utc).isoformat(),seconds=time.perf_counter()-tick,cases=len(cases),unique_rules=len(fingerprints),new_projection=projection,source_reuse='Old root qualifications retained as provenance and exact input/action bindings, not re-executed/new independent proof. Only newly selected interior strategy subtrees replayed.',observation_contract='Public progress_callback exports depth/nodes/qnodes, not chosen action. A future time-to-correct observer must preserve original search calls and qualify fixed-depth work parity; completion-depth/time curves alone cannot claim exact first-correct timestamp.',next='Freeze action-completeness tiers and actual DEFAULT/PVS/Native controller before any new Player queries. No new heuristic/solver or unregistered time-to-correct calls.'))
 print('CERTIFICATE INPUTS',len(cases),'rules',len(fingerprints),'new interior checks',projection,flush=True)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args();bind(a.directory)
