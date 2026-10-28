"""Recheck inferred bounds using existing literal Core finite-strategy checker."""
import argparse,json
from collections import defaultdict,Counter
from pathlib import Path
from generic_chess.core.actions import action_to_dict
from generic_chess.session.session import GameSession
from scripts.verify_published_new_family_games import load,record_hash,diagnostic_action
from scripts.leaper_truth_compatibility import bind_context,verify_bound_tree,digest
from scripts.research_record import record_value,write_record

def verify(derived,source):
 roots=load(source/'inputs.json.gz')['rows'];contexts={};by_root={};parents={};out=defaultdict(dict)
 for r in roots:
  c=bind_context(r['RuleSet'],r['record']);k=record_hash(c.session);by_root[k]=r;contexts[k]=c
 for e in derived['edges']:
  old=parents.setdefault(e['child'],(e['parent'],e['action']));assert old==(e['parent'],e['action'])
  out[e['parent']][e['action']]=e['child']
 def context(k):
  if k in contexts:return contexts[k]
  seq=[];cur=k
  while cur not in by_root:
   parent,token=parents[cur];seq.append(token);cur=parent
  r=by_root[cur];base=contexts[cur];s=GameSession.replay(base.session.compiled,base.session.to_record())
  for token in reversed(seq):s.submit(diagnostic_action(json.loads(token),r['fingerprint']))
  assert record_hash(s)==k;c=bind_context(r['RuleSet'],record_value(s.to_record()),compiled=s.compiled);contexts[k]=c;return c
 def tree(k,bound,direction):
  todo=[k];wire=[];seen=set()
  while todo:
   cur=todo.pop()
   if cur in seen:continue
   seen.add(cur);c=context(cur);n=derived['nodes'][cur];children=[]
   if n['terminal']['status']=='ongoing':
    existential=(n['actor']==0)==(direction=='lower')
    qualifies=lambda x:derived['bounds'][x][0]>=bound if direction=='lower' else derived['bounds'][x][1]<=bound
    candidates=[(a,ch) for a,ch in out[cur].items() if qualifies(ch)]
    if existential:assert candidates;candidates=candidates[:1]
    else:assert len(candidates)==n['legal']
    for token,ch in candidates:
     a=diagnostic_action(json.loads(token),c.identity['ruleset_fingerprint']);children.append(dict(action=action_to_dict(a),state=record_value(context(ch).session.state)));todo.append(ch)
   wire.append(dict(state=record_value(c.session.state),children=children))
  return wire
 checks=[];example=None
 for k,n in sorted(derived['nodes'].items(),key=lambda kv:(kv[1]['ply'],kv[0])):
  if n['terminal']['status']!='ongoing':continue
  lo,hi=derived['bounds'][k]
  for direction,bound in [('lower',lo),('upper',hi)]:
   if (direction=='lower' and bound==-1) or(direction=='upper' and bound==1):continue
   wire=tree(k,bound,direction);proof=verify_bound_tree(context(k),wire,bound,direction=direction,value_seat=0)
   checks.append(dict(record_sha256=k,ply=n['ply'],bounds=[lo,hi],proof=proof))
   if example is None and len(wire)>2:example=dict(rule=next(r['RuleSet'] for r in roots if r['fingerprint']==context(k).identity['ruleset_fingerprint']),record=record_value(context(k).session.to_record()),nodes=wire,bound=bound,direction=direction)
 return dict(checks=checks,verified_bound_directions=len(checks),nonterminal_roots=len({r['record_sha256'] for r in checks}),example=example,scope='Existing verify_bound_tree independently enumerates universal defenses; no unseen continuation is added to source forest.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--derived',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(load(a.derived),a.source);write_record(a.output,r);print(json.dumps({k:v for k,v in r.items() if k not in ('checks','example')}))
