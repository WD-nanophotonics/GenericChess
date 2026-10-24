"""Scoped future-relevant history projection; no runtime/search integration.

A complete position-local graph and the actual remaining draw clock bound every
future position that could compare against incoming repetition counts. Counts
outside that cone cannot alter legal suffixes or their terminal outcomes.
The experiments below use only the already published H6/repeat2 pair.
"""
from collections import Counter,deque,defaultdict
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import argparse,hashlib,json,time
from scripts.leaper_explorer_truth import load,digest
from scripts.leaper_history_edit_context import SOURCE
from scripts.leaper_h6_initial_truth import admit
from scripts.leaper_cooperative_certificate import decode_position
from scripts.leaper_microgames import role_stop_requested

REASONS=('mate0','mate1','stalemate','repetition','max_ply')

def first_hit_prior(edges,terminals,root,remaining,prior):
    """Repeat-two only: retain prior vertices reachable before another stop.

    Caller must check current static/repetition/clock terminal BEFORE calling.
    The current root is already visited, so any future arrival there also stops.
    Dynamic repeats among newly visited future vertices are conservatively
    ignored: this can retain extra prior entries, never erase a reachable one.
    """
    if root in terminals or remaining<=0 or prior>>root&1:
        raise ValueError('first-hit projection needs an ongoing repeat2 context')
    barriers=prior|1<<root;todo=deque((j,1)for j in edges[root]);seen=set();kept=0
    while todo:
        i,depth=todo.popleft()
        if i in terminals:continue
        if barriers>>i&1:
            if prior>>i&1:kept|=1<<i
            continue
        if depth>=remaining or i in seen:continue
        seen.add(i)
        todo.extend((j,depth+1)for j in edges[i])
    return kept

def future_cones(edges,terminals,horizon):
    if type(horizon)is not int or horizon<0:raise ValueError('nonnegative horizon required')
    n=len(edges)
    if any(i<0 or i>=n for i in terminals):raise ValueError('terminal outside graph')
    if any((bool(ee)if i in terminals else not ee)or any(type(j)is not int or not 0<=j<n for j in ee)for i,ee in enumerate(edges)):raise ValueError('complete terminal-sink graph required')
    out=[tuple(0 for _ in edges)]
    for h in range(1,horizon+1):
        row=[]
        for ee in edges:
            mask=0
            for j in ee:
                if j not in terminals:mask|=(1<<j)|out[h-1][j]
            row.append(mask)
        out.append(tuple(row))
    return tuple(out)


def make_solver(edges,sides,terminals,horizon,*,projected,guard=lambda:None):
    if len(sides)!=len(edges)or any(s not in(0,1)for s in sides)or any(sides[i]==sides[j]for i,ee in enumerate(edges)for j in ee):raise ValueError('alternating game required')
    cones=future_cones(edges,terminals,horizon);calls=Counter()
    def terminal(i,h,prior):
        if i in terminals:return 'stalemate'if terminals[i]is None else'mate'+str(terminals[i])
        if prior>>i&1:return 'repetition'
        if h==0:return 'max_ply'
        return None
    def canonical(i,h,prior):
        if not 0<=h<=horizon or prior<0 or prior>>len(edges):raise ValueError('invalid finite context')
        # Current terminal authority MUST precede projection. A current repeated
        # vertex need not be reachable again, yet the game has already ended.
        term=terminal(i,h,prior)
        if term is not None:return i,h,0,term
        return i,h,prior&cones[h][i]if projected else prior,None
    def solve(i,h,prior,foe='UNIFORM'):
        return visit(*canonical(i,h,prior),foe)
    @lru_cache(None)
    def visit(i,h,prior,term,foe):
        calls['states']+=1
        if calls['states']%2048==0:guard()
        if term is not None:
            value=1 if term=='mate0'else-1 if term=='mate1'else 0
            return value,tuple(F(int(reason==term))for reason in REASONS)
        pp=prior|1<<i;children=[solve(j,h-1,pp,foe)for j in edges[i]]
        value=(max if sides[i]==0 else min)(v for v,p in children)
        offsets=list(range(len(edges[i])))
        if foe=='FLOOR' and sides[i]==1:
            immediate=[k for k,j in enumerate(edges[i])if j in terminals and terminals[j]==1]
            if immediate:offsets=immediate[:1]
        if foe not in('UNIFORM','FLOOR'):raise ValueError('unsupported frozen policy')
        probability=tuple(sum((children[k][1][j]for k in offsets),F(0))/len(offsets)for j in range(len(REASONS)))
        return value,probability
    return solve,canonical,terminal,cones,visit,calls


def analyze(output,seconds=600):
    output=Path(output);output.mkdir(parents=True,exist_ok=False);tick=time.perf_counter();inputs=load(SOURCE/'inputs.json.gz');adj=load(SOURCE/'adjacent-pairs.json.gz');truth=load(SOURCE/'truth.json.gz');roots={r['id']:r for r in truth['roots']};pair=adj['pairs'][0]
    oldlaws=load(Path('docs/research/data/leaper_pair_transfer_20261024/policy-laws.json.gz'))
    plan=dict(question='Can future-unreachable prior positions be forgotten while preserving exact history WDL AND frozen Uniform/FLOOR terminal laws?',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),inputs_digest=digest(inputs),adjacency_digest=digest(adj),policy_digest=digest(oldlaws),
        selection='All complete histories from the original128commonfreshstarts in EACH existing rule; all legal continuations, H6/repeat2 unchanged. No old cappedPlayer/treecase or new rules/horizons.',
        expected='UNKNOWN: history-sensitive states must remain distinct; exact cone can be empty near clock and after irreversible captures.',
        caps=dict(seconds=seconds,contexts=200000,edges=1000000),
        interpretation='Data-only graph calculation, not production TT/learner or speedup claim; full rule admission and frozen complete domains precede projection.')
    (output/'plan.json').write_text(json.dumps(plan,indent=2));rows=[];whole=Counter()
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=seconds or whole['contexts']>200000 or whole['edges']>1000000:raise RuntimeError('CONE_CAP_UNKNOWN_NO_REFILL')
    for tag,key in(('left_family','left_id'),('right_family','right_id')):
        f=next(f for f in inputs['families']if f['family']==pair[tag]);src=next(r for r in inputs['rows']if r['family']==f['family']);c=admit(f,src);d=load(SOURCE/f"domain{f['family']}.json.gz")
        receipt=next(fa for fa in load(SOURCE/'summary.json')['families']if fa['family']==f['family'])
        if digest(d)!=receipt['domain_digest']:raise ValueError('domain changed')
        pos=[decode_position(p,c.initial_position)for p in d['positions']];edges=d['edges'];terms={int(i):v for i,v in d['terminals'].items()};sides=[p.side_to_move for p in pos]
        init=[roots[r[key]]['root_index']for r in pair['rows']]
        prep=time.perf_counter();full=make_solver(edges,sides,terms,6,projected=False,guard=guard);small=make_solver(edges,sides,terms,6,projected=True,guard=guard);prep=time.perf_counter()-prep
        todo=deque((i,6,0)for i in init);seen=set(todo);stats=Counter();sizes=Counter();reduced=set();valued={};frontier=hashlib.sha256();max_group=Counter();lost_identity=0
        while todo:
            if stats['contexts']%1024==0:guard()
            i,h,prior=todo.popleft();a=full[0](i,h,prior);b=small[0](i,h,prior)
            if a!=b:raise ValueError('projected WDL/probability law differs')
            kk=small[1](i,h,prior);reduced.add(kk);max_group[kk]+=1
            if kk in valued and valued[kk]!=a:raise ValueError('merged histories have different continuation law')
            valued[kk]=a;term=full[2](i,h,prior);stats['contexts']+=1;whole['contexts']+=1
            if term is None:
                stats['ongoing']+=1;kept=kk[2];stats['prior_memberships']+=prior.bit_count();stats['kept_memberships']+=kept.bit_count();stats['pruned_contexts']+=prior!=kept
                stats['empty_projected_prior']+=kept==0;sizes[str((6-h,prior.bit_count(),kept.bit_count()))]+=1
                for j in edges[i]:
                    ctx=(j,h-1,prior|1<<i);stats['edges']+=1;whole['edges']+=1
                    if ctx not in seen:seen.add(ctx);todo.append(ctx)
            frontier.update(json.dumps([i,h,hex(prior),kk,a[0],[str(p)for p in a[1]]],separators=(',',':')).encode());frontier.update(b'\n')
        lawrows=[]
        for foe in('UNIFORM','FLOOR'):
            expected={r['id']:r for r in oldlaws['rows']if r['family']==f['family']and r['opponent']==foe}
            for r in pair['rows']:
                i=roots[r[key]]['root_index'];aa=full[0](i,6,0,foe);bb=small[0](i,6,0,foe)
                if aa!=bb:raise ValueError('projected frozen policy law differs')
                pp=aa[1];LDW=(pp[1],sum(pp[2:],F(0)),pp[0])
                if tuple(map(str,LDW))!=tuple(expected[r[key]]['uniform_terminal_LDW']):raise ValueError('published full-history policy law differs')
                lawrows.append(dict(id=r[key],opponent=foe,WDL=aa[0],terminal_reason_probabilities=[str(p)for p in pp]))
        row=dict(family=f['family'],masks=f['masks'],fingerprint=f['fingerprint'],domain_digest=digest(d),stats=dict(stats),
            canonical_contexts=len(reduced),largest_merge=max(max_group.values()),membership_sizes=dict(sizes),
            full_memo=full[4].cache_info()._asdict(),projected_memo=small[4].cache_info()._asdict(),cone_preparation_seconds=prep,
            contexts_sha256=frontier.hexdigest(),policy_rows=lawrows)
        rows.append(row);print({k:v for k,v in row.items()if k not in('policy_rows','membership_sizes')},flush=True)
    result=dict(status='COMPLETE',plan=plan,rows=rows,counts=dict(whole),seconds=time.perf_counter()-tick,
        scope='Exact bounded suffix-game equivalence in admitted position-local draw-only repetition semantics; terminal check before projection. Not a generic GameState identity, full rule domain quotient, history-independent policy claim, cache implementation or measured engine acceleration.')
    (output/'result.json').write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();analyze(a.output)
