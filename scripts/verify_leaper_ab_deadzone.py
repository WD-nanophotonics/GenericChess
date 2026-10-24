"""Data-only closed-domain reader via legal_actions + apply_action.

The producer traverses Core legal_successors; this reader independently checks
every saved frontier, terminal, attractor equation and rank. Same Core engine,
not an independently implemented rule engine or a generic history quotient.
"""
from pathlib import Path
from collections import Counter
import argparse,gzip,json,time
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import source_documents,write
from scripts.leaper_cooperative_certificate import decode_position
from scripts.leaper_retrograde import fresh_state
from scripts.leaper_microgames import role_stop_requested
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action


def verify(path,output,*,target_group='contact',swap_owners=False):
    tick=time.perf_counter();g=json.loads(gzip.decompress(path.read_bytes()));docs=source_documents();source=json.loads(docs['contact/inputs.json']);w=json.loads(docs[target_group+'/inputs.json'])
    if g['rule']!=source['rule']:raise ValueError('complete source rule differs')
    differences=[k for k in source['rule']if source['rule'][k]!=w['rule'][k]]
    if target_group not in('contact','two-type')or set(source['rule'])!=set(w['rule'])or set(differences)-{'initial_position','initial_setup_options'}:raise ValueError('unsupported source/target rule difference')
    # A different full fingerprint is not silently treated as the source rule.
    # Compile the actual target and re-execute EVERY vertex/frontier below.
    c=L.compile_rule(L.ruleset_from_dict(w['rule']))
    encoded=g['positions']
    if swap_owners:
        table=str.maketrans('0123456','0456123')
        encoded=[[1-raw[0],raw[1].translate(table)]for raw in encoded]
    ps=[decode_position(p,c.initial_position)for p in encoded];indices={p:i for i,p in enumerate(ps)}
    if len(indices)!=len(ps)or len(ps)!=len(g['edges']):raise ValueError('domain coverage differs')
    vs={int(i):v for i,v in g['relative_values'].items()};rs={int(i):r for i,r in g['ranks'].items()};ts={int(i):w if not swap_owners or w is None else 1-w for i,w in g['terminals'].items()};counts=Counter()
    if set(vs)!=set(range(len(ps))):raise ValueError('value table incomplete')
    for i,p in enumerate(ps):
        if i%256==0 and role_stop_requested():raise RuntimeError('USER_STOP')
        s=fresh_state(p,c);ee=g['edges'][i];v=vs[i]
        if s.terminal_status.is_terminal:
            if ee or i not in ts or ts[i]!=s.terminal_status.winner:raise ValueError('actual static terminal differs')
            expected=0 if ts[i]is None else 1 if ts[i]==p.side_to_move else-1
            if v!=expected or(expected and rs.get(i)!=0):raise ValueError('terminal value/rank differs')
            counts['terminal_'+s.terminal_status.status.value]+=1
        else:
            actual=[]
            for a in legal_actions(s,c):
                child=apply_action(s,a,c)
                if child.position not in indices:raise ValueError('saved domain is not closed')
                actual.append(indices[child.position])
            if Counter(actual)!=Counter(ee)or not ee or i in ts:raise ValueError('complete actual frontier differs')
            children=[vs[j]for j in ee]
            if v==1:
                ranks=[rs[j]for j in ee if vs[j]==-1]
                if not ranks or rs.get(i)!=1+min(ranks):raise ValueError('WIN rank differs')
            elif v==-1:
                if any(x!=1 for x in children)or rs.get(i)!=1+max(rs[j]for j in ee):raise ValueError('LOSS rank differs')
            elif v==0:
                if -1 in children or 0 not in children or i in rs:raise ValueError('DRAW invariant differs')
            else:raise ValueError('not a WDL label')
        counts['vertices']+=1;counts['edges']+=len(ee)
        if i%10000==0:print(path.name,i,len(ps),round(time.perf_counter()-tick,2),flush=True)
    result=dict(verified=True,path=path.name,sha256=L.sha(path),counts=dict(counts),
        target_group=target_group,target_fingerprint=c.ruleset_fingerprint,rule_differences=differences,owner_swap=swap_owners,
        universal_draw=not any(w is not None for w in ts.values()),
        seconds=time.perf_counter()-tick,scope='Every static Core frontier/terminal and graph WDL/rank checked; physical nonzero labels do not become actual-history truth. Complete draw invariants survive this source draw-only clock/repetition.')
    write(output,result);return result


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--graph',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--target-group',choices=('contact','two-type'),default='contact');ap.add_argument('--swap-owners',action='store_true');a=ap.parse_args();verify(a.graph,a.output,target_group=a.target_group,swap_owners=a.swap_owners)
