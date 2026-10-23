"""Compact graph certificates: physical codes plus complete-frontier digest.

Public verification rebuilds every frontier with the separate integer model,
and samples actual Core. The producer's full Core graphs remain private raw
evidence. Reconstructing a Core graph uses the ordinary bounded producer;
source capsules are data, never executed by the reader.
"""
import argparse,gzip,hashlib,json,time
from pathlib import Path
from scripts.verify_leaper_frozen_pair_truth import compact_spec,physical,qualify_graph
from scripts.leaper_rule_coordinates import integer_actions,integer_terminal
from scripts.leaper_frozen_pair_truth import read_frozen,pair_summary


def code(side,spec,n):
    k,a,v=spec;N=n*n
    return ((side*N+k)*(N+1)+(0 if a is None else a+1))*N+v


def decode(value,n):
    N=n*n
    if type(value)is not int or not 0<=value<2*N*(N+1)*N:raise ValueError('invalid physical code')
    p,v=divmod(value,N);p,a=divmod(p,N+1);side,k=divmod(p,N)
    if k==v or(a and a-1 in(k,v)):raise ValueError('overlapping physical code')
    return side,(k,None if a==0 else a-1,v)


def frontier_digest(g):
    n=g.get('n',4);h=hashlib.sha256();terms={int(i):v for i,v in g['terminals'].items()}
    for i in range(len(g['positions'])):
        edges=sorted([*physical(a,n),j]for a,j in zip(g['actions'][i],g['edges'][i],strict=True))
        h.update(json.dumps([i,edges,terms.get(i,'ONGOING')],separators=(',',':')).encode());h.update(b'\n')
    return h.hexdigest()


def pack(g):
    n=g.get('n',4)
    roots=[dict(r,action_keys=[list(physical(a,n))for a in g['actions'][r['index']]])for r in g['roots']]
    return dict(n=n,mask=g['mask'],rule=g['rule'],position_codes=[code(*compact_spec(p,n),n)for p in g['positions']],
        frontier_sha256=frontier_digest(g),roots=roots,counts=g['counts'],seconds=g['seconds'],
        full_Core_graph_raw_sha256=hashlib.sha256(json.dumps(g,separators=(',',':')).encode()).hexdigest())


def reconstruct(packet):
    n=packet['n'];m=packet['mask'];phys=[decode(v,n)for v in packet['position_codes']];indices={p:i for i,p in enumerate(phys)}
    if len(indices)!=len(phys):raise ValueError('duplicate physical code')
    edges=[];actions=[];terms={};positions=[];overrides={r['index']:r['action_keys']for r in packet['roots']}
    for i,(side,spec)in enumerate(phys):
        k,a,v=spec;b=['0']*(n*n);b[k]='1';b[v]='3'
        if a is not None:b[a]='2'
        positions.append([side,''.join(b)])
        mapping={ac:indices.get((1-side,ch))for ac,ch in integer_actions(spec,m,side,n)}
        if None in mapping.values():raise ValueError('incomplete integer closure')
        keys=[tuple(a)for a in overrides[i]]if i in overrides else sorted(mapping)
        if set(keys)!=set(mapping)or len(keys)!=len(mapping):raise ValueError('source root action keys differ')
        edges.append([mapping[a]for a in keys]);actions.append([dict(actor_type_id=t,**{'from':[f%n,f//n],'to':[to%n,to//n]},promotion_target_id=p)for t,f,to,p in keys])
        term=integer_terminal(spec,m,side,n)
        if term['status']!='ongoing':terms[i]=0 if term['winner']is None else 1 if term['winner']==side else-1
    from scripts.leaper_retrograde import attractor
    vv,rr=attractor(edges,terms)
    g=dict(n=n,mask=m,rule=packet['rule'],positions=positions,edges=edges,actions=actions,terminals=terms,
        graph_values=[vv[i]for i in range(len(phys))],graph_ranks=[rr.get(i)for i in range(len(phys))],
        roots=[{k:v for k,v in r.items()if k!='action_keys'}for r in packet['roots']],counts=packet['counts'],seconds=packet['seconds'])
    if frontier_digest(g)!=packet['frontier_sha256']:raise ValueError('complete source Core frontier digest differs')
    return g


def verify_packet(path,output,*,core_samples=64,bundle=Path('docs/research/data/leaper_forward_width_20261024/screen-evidence.json.gz')):
    tick=time.perf_counter();raw=Path(path).read_bytes();manifest_path=Path(path).parent/'graph-manifest.json'
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_bytes())
        if hashlib.sha256(raw).hexdigest()!=manifest['packet_sha256']or hashlib.sha256(gzip.decompress(raw)).hexdigest()!=manifest['decoded_sha256']:raise ValueError('compact packet bytes differ')
    packet=json.loads(gzip.decompress(raw));rows=[];graphs=[]
    worlds,plan,source=read_frozen(bundle)
    if packet['source_bundle_sha256']!=source:raise ValueError('original PRIMARY source bundle differs')
    seen=set();masks={m for e in plan['edges']for m in e['masks']}
    for p in packet['graphs']:
        key=p['n'],p['mask']
        if key in seen:raise ValueError('duplicate graph packet')
        seen.add(key)
        g=reconstruct(p)
        for root in g['roots']:
            matches=[w for w in worlds if w['n']==p['n']and w['mask']==p['mask']and w['rule']==root['rule']and w['record']==root['record']]
            if len(matches)!=1 or root['rank']!=matches[0]['rank']:raise ValueError('source full mu record or rank differs')
        r=qualify_graph(g,core_samples=core_samples);rows.append(r);graphs.append(g);print({k:v for k,v in r.items()if k!='scope'},flush=True)
    if seen!={(n,m)for n in packet['complete_boards']for m in masks}:raise ValueError('complete board coverage differs')
    for n in packet['complete_boards']:
        actual=pair_summary([g for g in graphs if g['n']==n],plan)
        if actual!=packet['summaries'][str(n)]:raise ValueError('paired summary differs')
    if(Path(path).parent/'cost-truth.json').exists():
        from scripts.leaper_frozen_cost_truth import analyze as join_cost
        actual=join_cost(path,bundle);saved=json.loads((Path(path).parent/'cost-truth.json').read_bytes())
        if{k:v for k,v in actual.items()if k!='seconds'}!={k:v for k,v in saved.items()if k!='seconds'}:raise ValueError('retained PRIMARY cost/truth join differs')
    result=dict(verified=True,rows=rows,seconds=time.perf_counter()-tick,
        scope='Fullfrontierdigest equals independently reconstructedintegerclosure; allsourcefullrecords plus64Corefrontiers/graph replayed. FullproducerCoregraphs retainedignored; defaultreader isnotfullCore secondexecution orindependentengine.')
    Path(output).write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packet',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify_packet(a.packet,a.output)
