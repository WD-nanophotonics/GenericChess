"""Independent paired Session traversal for the fixed retained context census."""
from collections import deque,Counter,defaultdict
from copy import copy
from pathlib import Path
import json,time,hashlib,argparse
from scripts.leaper_explorer_truth import load,digest
from scripts.leaper_history_edit_context import SOURCE
from scripts.leaper_h6_initial_truth import admit
from scripts.leaper_h6_headroom import evaluate
from scripts.leaper_h6_pair_certificates import physical_position,physical_actions
from scripts.leaper_cooperative_certificate import decode_position
from scripts.leaper_microgames import role_stop_requested
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record

def verify(census_path,output,seconds=600):
    tick=time.perf_counter();data=load(census_path);inputs=load(SOURCE/'inputs.json.gz');adj=load(SOURCE/'adjacent-pairs.json.gz');pair=adj['pairs'][0]
    compiled=[];domains=[];indices=[];solvers=[];ends=[];count=Counter();todo=deque();seen=set();buckets=defaultdict(set);cross=defaultdict(set)
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>seconds:raise RuntimeError('SESSION_CENSUS_CAP_UNKNOWN_NO_REFILL')
    for tag in('left_family','right_family'):
        f=next(f for f in inputs['families']if f['family']==pair[tag]);row=next(r for r in inputs['rows']if r['family']==f['family']);c=admit(f,row);compiled.append(c)
        d=load(SOURCE/f"domain{f['family']}.json.gz");domains.append(d);pos=[decode_position(p,c.initial_position)for p in d['positions']];indices.append({p:i for i,p in enumerate(pos)})
        end,solve,*_=evaluate(d['edges'],{int(i):v for i,v in d['terminals'].items()},[p.side_to_move for p in pos],[(0,0)]*len(pos),guard);ends.append(end);solvers.append(solve)
    def add(origin,ls,rs,pl,pr,path):
        l=indices[0][ls.state.position];r=indices[1][rs.state.position];h=6-ls.state.ply_count;key=(origin,l,r,h,pl,pr)
        if key not in seen:seen.add(key);todo.append((key,ls,rs,path))
    for origin,row in enumerate(pair['rows']):
        ls=GameSession.replay(compiled[0],deserialize_game_record(json.dumps(row['left_record'])));rs=GameSession.replay(compiled[1],deserialize_game_record(json.dumps(row['right_record'])));add(origin,ls,rs,0,0,())
    hist=Counter();frontier=hashlib.sha256()
    while todo:
        if count['contexts']%128==0:guard()
        (origin,l,r,h,pl,pr),ls,rs,path=todo.popleft()
        if physical_position(ls.state.position)!=physical_position(rs.state.position)or ls.state.ply_count!=rs.state.ply_count:raise ValueError('physical/clock pair mismatch')
        current=(ls,rs);ix=(l,r);ps=(pl,pr);ended=tuple(s.result.status.value!='ongoing'for s in current)
        vals=tuple(solvers[a](ix[a],h,ps[a])for a in(0,1))
        for a,s in enumerate(current):
            if ended[a]!=ends[a](ix[a],h,ps[a]):raise ValueError('literal terminal refutes class')
            if ended[a]:
                actual=0 if s.result.winner is None else 1 if s.result.winner==0 else-1
                if actual!=vals[a]:raise ValueError('literal terminal value mismatch')
        buckets[origin,l,r,h].add((vals,ended));cross[l,r,h].add((vals,ended));hist[str((6-h,*vals,*ended))]+=1
        if not any(ended):
            ll=ls.legal_actions();rr=rs.legal_actions();la=physical_actions(ls);ra=physical_actions(rs)
            shared=sorted(set(la)&set(ra),key=repr)
            count['shared_edges']+=len(shared);count['left_only_edges']+=len(set(la)-set(ra));count['right_only_edges']+=len(set(ra)-set(la))
            for k in shared:
                lch=copy(ls);rch=copy(rs);lch.submit(la[k]);rch.submit(ra[k]);count['actual_Core_submits']+=2
                add(origin,lch,rch,pl|1<<l,pr|1<<r,(*path,(ll.index(la[k]),rr.index(ra[k]))))
        count['contexts']+=1
        frontier.update(json.dumps([origin,l,r,h,hex(pl),hex(pr),vals,ended,path],separators=(',',':')).encode());frontier.update(b'\n')
        if count['contexts']%8192==0:print(dict(count,seconds=time.perf_counter()-tick),flush=True)
    groups=Counter()
    for sigs in buckets.values():
        vv={v for v,e in sigs};ongoing={v for v,e in sigs if not any(e)}
        groups['same_root_Position_clock_groups']+=1;groups['history_value_sensitive_groups']+=len(vv)>1;groups['both_ongoing_value_sensitive_groups']+=len(ongoing)>1
        groups['multiple_signature_groups']+=len(sigs)>1;groups['history_sensitive_edit_delta_groups']+=len({b-a for a,b in vv})>1
    crossgroups=Counter()
    for sigs in cross.values():
        ongoing={v for v,e in sigs if not any(e)}
        crossgroups['Position_clock_groups']+=1;crossgroups['both_ongoing_WDL_sensitive_groups']+=len(ongoing)>1
        crossgroups['both_ongoing_edit_delta_sensitive_groups']+=len({b-a for a,b in ongoing})>1
    if {k:count[k]for k in data['counts']}!=data['counts']or dict(groups)!=data['groups']or dict(hist)!=data['histogram']or frontier.hexdigest()!=data['contexts_sha256']:raise ValueError('independent Session census differs')
    result=dict(verified=True,census_digest=digest(data),counts=dict(count),groups=dict(groups),across_original_roots=dict(crossgroups),contexts_sha256=frontier.hexdigest(),seconds=time.perf_counter()-tick,
        scope='Actual paired public Sessions reconstruct every retained class and shared edge. Compact continuation WDL still uses qualified frozen graph; separate literal full-GameState witness trees establish selected contrasts. Not a new all-context full-GameState WDL engine or sampling law.')
    Path(output).write_text(json.dumps(result,indent=2));print(result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--census',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.census,a.output)
