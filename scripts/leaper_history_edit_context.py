"""Exposed history-coordinate census on the existing H6 one-bit pair.

Uses only already closed Core domains. Every retained context has an explicit
path from the original common fresh mu. No invented visited sets, new rule,
Player, training, forecast fitting or old experiment continuation.
"""
from collections import Counter,deque,defaultdict
from pathlib import Path
import argparse,hashlib,json,time
from scripts.leaper_explorer_truth import load,digest
from scripts.leaper_h6_initial_truth import admit
from scripts.leaper_h6_headroom import evaluate
from scripts.leaper_h6_adjacent_pairs import physical_action
from scripts.leaper_cooperative_certificate import decode_position
from scripts.leaper_microgames import role_stop_requested

SOURCE=Path('docs/research/data/leaper_h6_initial_truth_20261023')

def census(output,seconds=300,cap=1000000):
    output=Path(output);output.mkdir(parents=True,exist_ok=False);tick=time.perf_counter()
    inputs=load(SOURCE/'inputs.json.gz');adj=load(SOURCE/'adjacent-pairs.json.gz');truth=load(SOURCE/'truth.json.gz');roots={r['id']:r for r in truth['roots']}
    assert len(adj['pairs'])==1
    pair=adj['pairs'][0];assert pair['left_masks']==[6,27] and pair['right_masks']==[22,27]
    plan=dict(question='Does actual legal prehistory alter WDL or the A6-to-A22 rule effect at identical physical Position and clock?',
        selection='All128originalcommonfreshroots, all common legal prefixes until either arm terminates; stop at H6. Deterministic BFS witnesses, no policy samples or heldout claim.',
        latest_mainline='731709e69007713ac403d60e1218221d1950c8d9',input_digest=digest(inputs),adjacency_digest=digest(adj),truth_digest=digest(truth),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),seconds_cap=seconds,context_cap=cap,
        expectation='UNKNOWN: prior PRIMARY example had terminal-status difference but both histories DRAW. Retain negative census if no WDL witness; do not extend horizon or select new rule to seek positive.')
    (output/'plan.json').write_text(json.dumps(plan,indent=2))
    count=Counter();domains=[];solvers=[];ends=[];indices=[];physical=[];maps=[];families=[]
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=seconds or count['contexts']>=cap:raise RuntimeError('HISTORY_CENSUS_CAP_UNKNOWN_NO_REFILL')
    for tag in ('left_family','right_family'):
        family=next(f for f in inputs['families']if f['family']==pair[tag]);row=next(r for r in inputs['rows']if r['family']==family['family']);c=admit(family,row)
        d=load(SOURCE/f"domain{family['family']}.json.gz");receipt=next(f for f in load(SOURCE/'summary.json')['families']if f['family']==family['family']);assert digest(d)==receipt['domain_digest']
        pos=[decode_position(p,c.initial_position)for p in d['positions']];terms={int(i):w for i,w in d['terminals'].items()}
        end,solve,*_=evaluate(d['edges'],terms,[p.side_to_move for p in pos],[(0,0)]*len(pos),guard)
        domains.append(d);solvers.append(solve);ends.append(end);families.append(family)
        physical.append([digest(p)for p in d['positions']]);indices.append({key:i for i,key in enumerate(physical[-1])})
        maps.append([{physical_action(a):(offset,j)for offset,(a,j)in enumerate(zip(aa,ee,strict=True))}for aa,ee in zip(d['actions'],d['edges'],strict=True)])
    # Root provenance is kept in the key: a witness can share its actual initializer.
    todo=deque();seen=set();rows=[];hist=Counter();buckets=defaultdict(dict);cross=defaultdict(dict);witnesses={};frontier=hashlib.sha256()
    def add(origin,l,r,h,pl,pr,path):
        key=(origin,l,r,h,pl,pr)
        if key not in seen:seen.add(key);todo.append((key,path))
    for origin,row in enumerate(pair['rows']):
        l=roots[row['left_id']]['root_index'];r=roots[row['right_id']]['root_index'];assert physical[0][l]==physical[1][r]
        add(origin,l,r,6,0,0,())
    def wire(row):
        return dict(origin=row['origin'],placement=pair['rows'][row['origin']]['placement'],left_vertex=row['l'],right_vertex=row['r'],remaining=row['h'],
                    prior_left=hex(row['pl']),prior_right=hex(row['pr']),path_offsets=row['path'],values=row['values'],ended=row['ended'])
    def compare(old,row,prefix):
        if old['values']!=row['values']:
            kind=prefix+('_both_ongoing'if not any(old['ended']+row['ended'])else'_terminal_involved')
            if kind not in witnesses:witnesses[kind]=[wire(old),wire(row)]
        if old['values'][1]-old['values'][0]!=row['values'][1]-row['values'][0]:
            kind=prefix+'_edit_delta'+('_both_ongoing'if not any(old['ended']+row['ended'])else'_terminal_involved')
            if kind not in witnesses:witnesses[kind]=[wire(old),wire(row)]
    while todo:
        if count['contexts']%1024==0:guard()
        (origin,l,r,h,pl,pr),path=todo.popleft();assert physical[0][l]==physical[1][r]
        vals=(solvers[0](l,h,pl),solvers[1](r,h,pr));ended=(ends[0](l,h,pl),ends[1](r,h,pr))
        row=dict(origin=origin,l=l,r=r,h=h,pl=pl,pr=pr,path=path,values=vals,ended=ended)
        signature=(vals,ended);hist[str((6-h,*vals,*ended))]+=1
        for old in buckets[origin,l,r,h].values():compare(old,row,'same_root')
        buckets[origin,l,r,h].setdefault(signature,row)
        for old in cross[l,r,h].values():compare(old,row,'different_or_same_root')
        cross[l,r,h].setdefault(signature,row)
        if not any(ended):
            pp=pl|1<<l;qq=pr|1<<r
            left,right=maps[0][l],maps[1][r];shared=sorted(set(left)&set(right),key=repr)
            count['shared_edges']+=len(shared);count['left_only_edges']+=len(set(left)-set(right));count['right_only_edges']+=len(set(right)-set(left))
            for a in shared:
                lo,lj=left[a];ro,rj=right[a];assert physical[0][lj]==physical[1][rj]
                add(origin,lj,rj,h-1,pp,qq,(*path,(lo,ro)))
        count['contexts']+=1
        frontier.update(json.dumps([origin,l,r,h,hex(pl),hex(pr),vals,ended,path],separators=(',',':')).encode());frontier.update(b'\n')
    groups=Counter();examples=[]
    for key,rr in buckets.items():
        v={r['values']for r in rr.values()};ongoing={r['values']for r in rr.values()if not any(r['ended'])}
        groups['same_root_Position_clock_groups']+=1;groups['history_value_sensitive_groups']+=len(v)>1;groups['both_ongoing_value_sensitive_groups']+=len(ongoing)>1
        groups['multiple_signature_groups']+=len(rr)>1
        effects={b-a for a,b in v};groups['history_sensitive_edit_delta_groups']+=len(effects)>1
    result=dict(status='COMPLETE',plan=plan,counts=dict(count),groups=dict(groups),histogram=dict(hist),witnesses=witnesses,
        contexts_sha256=frontier.hexdigest(),domains=[digest(d)for d in domains],fingerprints=[f['fingerprint']for f in families],
        seconds=time.perf_counter()-tick,
        scope='Existing fixed pair128mu, common-prefix reachability only. Context counts are correlated equivalence classes, not independent rules or probability mass. New-only move continuations are excluded from common-prefix census but included in each exact continuation WDL. No claim about arbitrary histories or horizons.')
    (output/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('plan','witnesses','histogram')},indent=2),flush=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();census(a.output)
