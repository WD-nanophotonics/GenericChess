"""Actual Session suffix-tree equivalence versus scoped history projections."""
from collections import Counter,deque,defaultdict
from copy import copy
from pathlib import Path
import json,time,hashlib,argparse
from scripts.leaper_explorer_truth import load,digest
from scripts.leaper_history_edit_context import SOURCE
from scripts.leaper_h6_initial_truth import admit
from scripts.leaper_future_history_cone import future_cones,first_hit_prior
from scripts.leaper_cooperative_certificate import decode_position
from scripts.leaper_microgames import role_stop_requested
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_to_dict

def run(output,seconds=600):
    tick=time.perf_counter();inputs=load(SOURCE/'inputs.json.gz');truth=load(SOURCE/'truth.json.gz');roots={r['id']:r for r in truth['roots']};adj=load(SOURCE/'adjacent-pairs.json.gz');pair=adj['pairs'][0];rows=[];whole=Counter()
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>seconds:raise RuntimeError('SUFFIX_PARTITION_CAP_UNKNOWN_NO_REFILL')
    for tag,key,record in(('left_family','left_id','left_record'),('right_family','right_id','right_record')):
        f=next(f for f in inputs['families']if f['family']==pair[tag]);src=next(r for r in inputs['rows']if r['family']==f['family']);c=admit(f,src);d=load(SOURCE/f"domain{f['family']}.json.gz")
        pos=[decode_position(p,c.initial_position)for p in d['positions']];indices={p:i for i,p in enumerate(pos)};terms={int(i):v for i,v in d['terminals'].items()};cones=future_cones(d['edges'],terms,6)
        todo=deque();sessions={};nodes={};rootkeys=[];stats=Counter();wire=hashlib.sha256()
        def add(s,i,h,prior):
            kk=(i,h,prior)
            if kk not in sessions:sessions[kk]=s;todo.append(kk)
            return kk
        for r in pair['rows']:
            s=GameSession.replay(c,deserialize_game_record(json.dumps(r[record])));i=roots[r[key]]['root_index'];rootkeys.append(add(s,i,6,0))
        while todo:
            if stats['contexts']%256==0:guard()
            kk=todo.popleft();i,h,prior=kk;s=sessions[kk]
            if s.state.position!=pos[i]or s.state.ply_count!=6-h:raise ValueError('literal context differs')
            term=None;children=[]
            if s.result.status.value!='ongoing':term=(s.result.status.value,s.result.winner)
            else:
                actual=s.legal_actions()
                if [action_to_dict(a)for a in actual]!=d['actions'][i]:raise ValueError('actual frontier differs')
                for offset,a in enumerate(actual):
                    child=copy(s);child.submit(a);j=indices[child.state.position]
                    if j!=d['edges'][i][offset]:raise ValueError('actual target differs')
                    children.append((json.dumps(action_to_dict(a),sort_keys=True,separators=(',',':')),add(child,j,h-1,prior|1<<i)));stats['Core_edges']+=1
            nodes[kk]=(term,children);stats['contexts']+=1
            wire.update(json.dumps([i,h,hex(prior),term,[(a,[x,y,hex(z)])for a,(x,y,z)in children]],separators=(',',':')).encode());wire.update(b'\n')
        # Exact bottom-up ordered-action suffix-tree partition, retaining the
        # physical Position and clock. It is coarsest ONLY under these required
        # coordinates in this finite admitted corpus, not a generic minimum key.
        blocks={};classes={};projections={};firsthit={};normalized={};position_groups=defaultdict(set);cone_groups=defaultdict(set);bad=Counter();layers=defaultdict(Counter)
        for kk in sorted(nodes,key=lambda k:(k[1],k[0],k[2])):
            i,h,prior=kk;term,children=nodes[kk]
            signature=(i,h,term,tuple((a,blocks[ch])for a,ch in children))
            block=classes.setdefault(signature,len(classes));blocks[kk]=block
            projection=(i,h,0,term)if term else(i,h,prior&cones[h][i],None)
            norm=(i,h,0,term)if term else(i,h,prior,None)
            if projection in projections and projections[projection]!=block:raise ValueError('cone merges different literal suffix trees')
            projections[projection]=block;normalized[norm]=block
            fk=(i,h,0,term)if term else(i,h,first_hit_prior(d['edges'],terms,i,h,prior),None)
            if fk in firsthit and firsthit[fk]!=block:raise ValueError('first-hit merges different suffix trees')
            firsthit[fk]=block
            if term is None and first_hit_prior(d['edges'],terms,i,h,fk[2])!=fk[2]:raise ValueError('first-hit projection is not idempotent')
            position_groups[i,h].add(block);cone_groups[block].add(projection)
            layers[6-h]['raw_classes']+=1
            if term is None:layers[6-h]['ongoing_classes']+=1
        perlayer=[]
        for ply,ct in sorted(layers.items()):
            h=6-ply
            ct['terminal_normalized_keys']=sum(k[1]==h for k in normalized)
            ct['cone_keys']=sum(k[1]==h for k in projections)
            ct['exact_suffix_blocks']=sum(k[1]==h for k in classes)
            ct['first_hit_keys']=sum(k[1]==h for k in firsthit)
            ct['ongoing_first_hit_keys']=sum(k[1]==h and k[3]is None for k in firsthit)
            ct['ongoing_cone_keys']=sum(k[1]==h and k[3]is None for k in projections)
            ct['ongoing_suffix_blocks']=sum(k[1]==h and k[2]is None for k in classes)
            perlayer.append(dict(ply=ply,**ct))
        stats['first_hit_keys']=len(firsthit);stats['ongoing_first_hit_keys']=sum(k[3]is None for k in firsthit)
        stats['terminal_normalized_keys']=len(normalized);stats['cone_keys']=len(projections);stats['exact_suffix_blocks']=len(classes)
        stats['Position_clock_groups']=len(position_groups);stats['Position_clock_behavior_sensitive_groups']=sum(len(v)>1 for v in position_groups.values())
        stats['suffix_blocks_with_multiple_cone_keys']=sum(len(v)>1 for v in cone_groups.values())
        stats['ongoing_full_keys']=sum(term is None for term,_ in nodes.values());stats['ongoing_cone_keys']=sum(k[3]is None for k in projections);stats['ongoing_suffix_blocks']=sum(k[2]is None for k in classes)
        row=dict(family=f['family'],masks=f['masks'],stats=dict(stats),by_ply=perlayer,actual_frontier_sha256=wire.hexdigest(),root_suffix_blocks=[blocks[k]for k in rootkeys],domain_digest=digest(d))
        rows.append(row);whole.update(stats);print({k:v for k,v in row.items()if k not in('by_ply','root_suffix_blocks')},flush=True)
    result=dict(verified=True,rows=rows,counts=dict(whole),seconds=time.perf_counter()-tick,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Every existing admitted H6 history class and actual public Core action. Cone keys preserve literal ordered-action/terminal-reason suffix-tree blocks at fixed Position/clock. Coarsest suffix partition is finite-corpus and coordinate-constrained, not minimal general history representation, policy state or runtime speed.')
    Path(output).write_text(json.dumps(result,indent=2));print({k:v for k,v in result.items()if k!='rows'});return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.output)
