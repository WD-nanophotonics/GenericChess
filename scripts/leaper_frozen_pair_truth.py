"""AUX truth on PRIMARY's previously frozen singleton roots and rule edges.

No rule/layout selection, Player, training or forward policy campaign. The
admitted physical closure is rebuilt through public Core; supplied full fresh
records, draw clocks and repeat4 remain explicit. Only exact PRIMARY plain
singleton templates are admitted; this is not a general Position quotient.
"""
from __future__ import annotations
from collections import Counter,deque
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
import argparse,gzip,hashlib,json,time

from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.transition import legal_successors
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_single_parity_truth import admit,domain,bare_opponent_bound
from scripts.leaper_clock_rebinding import compact,expand
from scripts.leaper_retrograde import fresh_state,attractor
from scripts.leaper_cooperative_truth import cooperative_distances
from scripts.leaper_design import state_sha,ruleset_to_dict
from scripts.leaper_explorer_truth import digest
from scripts.leaper_microgames import role_stop_requested
from scripts.leaper_rule_coordinates import template as primary_template
from scripts.leaper_design import ruleset_from_dict,compile_rule


def admit_frozen(raw,mask,n):
    """Full rule equality to the committed producer template, no mask shortcut."""
    if n not in(4,5,6):raise ValueError('unsupported frozen board')
    rule=ruleset_from_dict(raw);board=[p for row in rule.initial_position for p in row]
    def at(owner,tid):
        found=[i for i,p in enumerate(board)if p and p.owner==owner and p.current_type_id==tid]
        if len(found)!=1:raise ValueError('exact frozen roster required')
        return found[0]
    spec=(at(0,'K'),at(0,'A'),at(1,'K'))
    if raw!=ruleset_to_dict(primary_template(mask,n,spec),include_metadata=True):
        raise ValueError('complete rule differs from committed PRIMARY template')
    c=compile_rule(rule)
    if c.max_ply!=64 or c.repetition_limit!=4:raise ValueError('clock/history admission differs')
    support=c.support
    if (support.stalemate_result!='draw' or support.repetition_policy!='draw'
        or any(getattr(support,k)for k in('automatic_adjudications','consecutive_action_adjudications','no_progress_draw','pass_enabled'))
        or getattr(c,'repeated_cycle_target_conditions',())):
        raise ValueError('unsupported history or scoring terminal authority')
    return c


def admit_position(pos,n):
    if pos.aux_state or any(h.counts for h in pos.hands)or len(pos.board)!=n*n:
        raise ValueError('unsupported auxiliary/hand/shape')
    kings={};ordinary=[]
    for i,p in enumerate(pos.board):
        if p is None:continue
        if p.owner not in(0,1)or p.promoted or p.current_type_id!=p.base_type_id:
            raise ValueError('unsupported owner/promotion')
        if p.current_type_id=='K':
            if p.owner in kings:raise ValueError('duplicate King')
            kings[p.owner]=i
        elif p.current_type_id=='A'and p.owner==0:ordinary.append(i)
        else:raise ValueError('bare opponent bound unavailable')
    if set(kings)!={0,1}or len(ordinary)>1:raise ValueError('roster differs')
    a,b=kings.values()
    if max(abs(a%n-b%n),abs(a//n-b//n))<=1:raise ValueError('adjacent Kings')


def read_frozen(bundle):
    bundle=Path(bundle);payload=bundle.read_bytes()
    manifest=json.loads((bundle.parent/'screen-manifest.json').read_bytes())
    assert hashlib.sha256(payload).hexdigest()==manifest['compressed_sha256']
    body=gzip.decompress(payload);assert hashlib.sha256(body).hexdigest()==manifest['decoded_sha256']
    texts=json.loads(body)['documents_utf8']
    for k,v in texts.items():
        assert hashlib.sha256(v.encode()).hexdigest()==manifest['original_sha256'][k]
    worlds=json.loads(texts['edge-inputs.json'])['worlds']
    plan=json.loads(texts['edge-plan.json'])
    return worlds,plan,hashlib.sha256(payload).hexdigest()


def graph_for(worlds,*,seconds=120):
    """Close union of supplied roots; all physical edges are actual Core edges."""
    tick=time.perf_counter();first=worlds[0]
    n=first['n'];c=admit_frozen(first['rule'],first['mask'],n)
    assert c.max_ply==64 and c.repetition_limit==4
    template=c.initial_position;positions=[];indices={};queue=deque();rootrows=[]
    def add(p):
        if p not in indices:
            indices[p]=len(positions);positions.append(p);queue.append(p)
        return indices[p]
    normalize=lambda raw:{k:v for k,v in raw.items()if k!='initial_position'}
    for w in worlds:
        assert w['n']==n and w['mask']==first['mask'] and normalize(w['rule'])==normalize(first['rule'])
        tc=admit_frozen(w['rule'],w['mask'],n)
        ss=GameSession.replay(tc,deserialize_game_record(json.dumps(w['record'])))
        assert ss.state.ply_count==0 and len(ss.state.history)==1 and len(ss.state.repetition_counts)==1
        assert ss.state.repetition_counts[0][1]==1 and not ss.state.terminal_status.is_terminal
        assert ss.state.position.side_to_move==0
        i=add(replace(ss.state.position,ruleset_fingerprint=template.ruleset_fingerprint))
        rootrows.append(dict(rank=w['rank'],index=i,record=w['record'],rule=w['rule'],state_sha=state_sha(ss.state)))
    edges=[];actions=[];terms={};counts=Counter()
    while queue:
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=seconds:raise RuntimeError('NEW_COHORT_CAP_UNKNOWN')
        if len(positions)>2*(n*n)*(n*n-1)*(n*n-1):raise RuntimeError('NEW_COHORT_SIZE_UNKNOWN')
        pos=queue.popleft();i=indices[pos];assert i==len(edges)
        admit_position(pos,n)
        state=fresh_state(pos,c)
        if state.terminal_status.is_terminal:
            winner=state.terminal_status.winner
            if winner is not None:assert winner==0
            terms[i]=0 if winner is None else 1 if winner==pos.side_to_move else-1
            edges.append([]);actions.append([]);counts['terminal_'+state.terminal_status.status.value]+=1
            continue
        aa=[];ee=[]
        for action,ch in legal_successors(state,c):
            assert ch.position.side_to_move==1-pos.side_to_move
            ee.append(add(ch.position));aa.append(action_to_dict(action));counts['Core_edges']+=1
        assert ee;edges.append(ee);actions.append(aa)
    values,ranks=attractor(edges,terms)
    coop,_=cooperative_distances(edges,[i for i,v in terms.items()if v])
    # Independent finite-clock Bellman sweeps. There is only player0 mate;
    # decisive strategies have strict rank and no repeated vertex. Future
    # cycling can only draw, so fresh repeat4 does not destroy a finite win.
    current={i:terms.get(i,0)for i in range(len(edges))};finite={}
    for h in range(1,65):
        current={i:terms[i]if i in terms else max(-current[j]for j in ee)for i,ee in enumerate(edges)}
        assert all(current[i]==(values[i]if values[i]and ranks[i]<=h else 0)for i in current)
        if h in(5,6,63,64):finite[h]=dict(current)
    roots=[]
    for r in rootrows:
        i=r['index'];v=values[i];rank=ranks.get(i);d=coop.get(i);rows=[]
        for H in(6,64):
            label=finite[H][i]
            branches=[-finite[H-1][j]for j in edges[i]]
            assert label==max(branches) and label in(0,1)
            category=('WIN'if label else'clock_blocks_forced_WIN'if v else
                'no_reachable_mate'if d is None else'strategic_DRAW_clock_blocks_cooperation'if d>H else'strategic_DRAW_with_cooperation')
            rows.append(dict(H=H,WDL=label,fork=len(set(branches))>1,actions=branches,
                cooperative=d is not None and d<=H,draw_category=category))
        roots.append(dict(r,graph_WDL=v,forced_rank=rank,cooperative_distance=d,clocks=rows))
    return dict(mask=first['mask'],n=n,rule=first['rule'],positions=[compact(p)for p in positions],edges=edges,
        actions=actions,terminals=terms,roots=roots,counts=dict(counts),seconds=time.perf_counter()-tick,
        graph_values=[values[i]for i in range(len(edges))],graph_ranks=[ranks.get(i)for i in range(len(edges))])


def pair_summary(graphs,plan):
    by={g['mask']:g for g in graphs};rows=[]
    for e in plan['edges']:
        a,b=e['masks'];lo=by[a]['roots'];hi=by[b]['roots'];assert len(lo)==len(hi)==8
        for x,y in zip(lo,hi,strict=True):
            assert x['rank']==y['rank']
            assert x['rule']['initial_position']==y['rule']['initial_position']
        clocks=[]
        for H in(6,64):
            c=Counter();pairs=[]
            for x,y in zip(lo,hi,strict=True):
                xx=next(z for z in x['clocks']if z['H']==H);yy=next(z for z in y['clocks']if z['H']==H)
                for k in('WDL','fork','cooperative'):c[k+'_changed']+=xx[k]!=yy[k]
                c['WDL_gain']+=yy['WDL']>xx['WDL'];c['WDL_loss']+=yy['WDL']<xx['WDL']
                pairs.append(dict(rank=x['rank'],low={k:xx[k]for k in('WDL','fork','cooperative','draw_category')},high={k:yy[k]for k in('WDL','fork','cooperative','draw_category')}))
            clocks.append(dict(H=H,counts=dict(c),roots=pairs))
        rows.append(dict(e,clocks=clocks))
    tables=[]
    for H in(6,64):
        table={}
        for stratum in('components','parity_only','stable'):
            rr=[next(c for c in r['clocks']if c['H']==H)for r in rows if r['stratum']==stratum]
            table[stratum]={k:dict(changed=sum(r['counts'][k+'_changed']>0 for r in rr),unchanged=sum(r['counts'][k+'_changed']==0 for r in rr))for k in('WDL','fork','cooperative')}
        tables.append(dict(H=H,table=table))
    return dict(edges=rows,tables=tables)


def run(bundle,output):
    output=Path(output)
    if output.exists():raise ValueError('new immutable output required')
    output.mkdir(parents=True);tick=time.perf_counter();worlds,plan,source=read_frozen(bundle)
    masks=sorted({m for e in plan['edges']for m in e['masks']})
    frozen=dict(source_bundle_sha256=source,source_sha='b66566c3647918b4c2f40993869ff0c46fb75e9b',
        source_file_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),board=4,clocks=[6,64],repeat=4,
        masks=masks,edges=plan['edges'],scope='Frozen PRIMARY8common freshroots,24exposed stratifiededges. No newPlayer,rule/layoutselection,training,policycampaign orblindforecast claim.',
        budget='One closure per unique endpoint<=120s and8192vertices; total<=900s. Missing/CAP staysUNKNOWN, noautomaticrefill.')
    (output/'plan.json').write_text(json.dumps(frozen,indent=2))
    graphs=[]
    for m in masks:
        if time.perf_counter()-tick>=900:raise RuntimeError('TOTAL_COHORT_CAP_UNKNOWN')
        g=graph_for([w for w in worlds if w['n']==4 and w['mask']==m])
        data=json.dumps(g,separators=(',',':')).encode();(output/f'mask{m}.json.gz').write_bytes(gzip.compress(data,mtime=0))
        graphs.append(g);print(dict(mask=m,vertices=len(g['positions']),**g['counts'],seconds=g['seconds']),flush=True)
    result=pair_summary(graphs,plan);result['seconds']=time.perf_counter()-tick
    result['scope']=frozen['scope'];(output/'summary.json').write_text(json.dumps(result,indent=2))
    print('COMPLETE',result['tables'],result['seconds'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.bundle,a.output)
