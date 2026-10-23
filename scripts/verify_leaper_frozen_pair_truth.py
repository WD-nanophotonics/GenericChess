"""Verify frozen singleton graph packets against separate integer geometry.

Every graph vertex/frontier is checked by PRIMARY's independent finite integer
model; sampled frontiers and all actual supplied roots additionally use Core.
No Player, sampled games, source-capsule execution or history label transfer.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import replace
from pathlib import Path
import argparse,gzip,json,time
from generic_chess.core.actions import action_to_dict
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import legal_successors
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_frozen_pair_truth import admit_frozen,admit_position,read_frozen,pair_summary
from scripts.leaper_rule_coordinates import integer_actions,integer_terminal
from scripts.leaper_retrograde import fresh_state,attractor
from scripts.leaper_cooperative_truth import cooperative_distances
from scripts.leaper_design import state_sha
from scripts.leaper_clock_rebinding import compact


def physical(row,n):
    return row['actor_type_id'],row['from'][0]+n*row['from'][1],row['to'][0]+n*row['to'][1],row['promotion_target_id']


def unpack_position(row,template,n):
    if not isinstance(row,list)or len(row)!=2 or type(row[0])is not int or row[0]not in(0,1):raise ValueError('invalid physical row')
    if not isinstance(row[1],str)or len(row[1])!=n*n or set(row[1])-set('0123'):raise ValueError('invalid board encoding')
    alpha={'1':(0,'K'),'2':(0,'A'),'3':(1,'K')}
    p=replace(template,board=tuple(None if x=='0'else Piece(*alpha[x],alpha[x][1])for x in row[1]),side_to_move=row[0])
    admit_position(p,n);return p


def compact_spec(row,n):
    side,board=row
    if any(board.count(k)!=1 for k in('1','3'))or board.count('2')>1:raise ValueError('invalid roster')
    return side,(board.index('1'),board.index('2')if'2'in board else None,board.index('3'))


def qualify_graph(g,*,core_samples=64):
    tick=time.perf_counter();n=g.get('n',4);m=g['mask'];c=admit_frozen(g['rule'],m,n)
    states=[unpack_position(p,c.initial_position,n)for p in g['positions']]
    physicals=[compact_spec(p,n)for p in g['positions']];indices={p:i for i,p in enumerate(physicals)}
    if len(indices)!=len(states):raise ValueError('duplicate physical position')
    ee=[];terms={};counts=Counter();sampled={i*(len(states)-1)//max(1,core_samples-1)for i in range(core_samples)}
    for i,(side,spec)in enumerate(physicals):
        predicted=integer_actions(spec,m,side,n);terminal=integer_terminal(spec,m,side,n)
        if terminal['status']!='ongoing':
            if predicted:raise ValueError('terminal with legal integer successor')
            winner=terminal['winner'];terms[i]=0 if winner is None else 1 if winner==side else-1
        expected={a:indices.get((1-side,child))for a,child in predicted}
        if None in expected.values():raise ValueError('missing finite integer closure vertex')
        retained={physical(a,n):j for a,j in zip(g['actions'][i],g['edges'][i],strict=True)}
        if len(retained)!=len(g['edges'][i])or expected!=retained:raise ValueError('integer/Core frontier differs')
        ee.append(list(expected.values()));counts['integer_vertices']+=1;counts['integer_edges']+=len(expected)
        if i in sampled:
            ss=fresh_state(states[i],c)
            actual={physical(action_to_dict(a),n):indices[compact_spec(compact(ch.position),n)]for a,ch in legal_successors(ss,c)}
            if actual!=expected:raise ValueError('sampled actual Core frontier differs')
            counts['Core_sampled_vertices']+=1;counts['Core_sampled_edges']+=len(actual)
            observed=ss.terminal_status
            if observed.status.value!=terminal['status']or observed.winner!=terminal['winner']:raise ValueError('actual terminal differs')
    if {int(i):v for i,v in g['terminals'].items()}!=terms:raise ValueError('integer terminals differ')
    vv,rr=attractor(ee,terms)
    if g['graph_values']!=[vv[i]for i in range(len(ee))]or g['graph_ranks']!=[rr.get(i)for i in range(len(ee))]:raise ValueError('stored attractor differs')
    dist,_=cooperative_distances(ee,[i for i,v in terms.items()if v])
    for r in g['roots']:
        tc=admit_frozen(r['rule'],m,n);s=GameSession.replay(tc,deserialize_game_record(json.dumps(r['record'])))
        if state_sha(s.state)!=r['state_sha']or s.state.ply_count!=0:raise ValueError('source full record binding differs')
        p=replace(s.state.position,ruleset_fingerprint=c.ruleset_fingerprint);i=r['index']
        if p!=states[i]:raise ValueError('source position binding differs')
        if r['forced_rank']!=rr.get(i)or r['cooperative_distance']!=dist.get(i)or r['graph_WDL']!=vv[i]:raise ValueError('root distance/value differs')
        if [row['H']for row in r['clocks']]!=[6,64]:raise ValueError('frozen clock support differs')
        for row in r['clocks']:
            H=row['H'];value=vv[i]if vv[i]and rr[i]<=H else 0
            # Source action sequence order is preserved in public row labels.
            values=[-vv[j]if vv[j]and rr[j]<=H-1 else 0 for j in g['edges'][i]]
            if row['WDL']!=value or row['actions']!=values or row['fork']!=(len(set(values))>1):raise ValueError('root finite action labels differ')
            if row['cooperative']!=(i in dist and dist[i]<=H):raise ValueError('cooperative clock differs')
            category=('WIN'if value else'clock_blocks_forced_WIN'if vv[i]else
                'no_reachable_mate'if i not in dist else'strategic_DRAW_clock_blocks_cooperation'if dist[i]>H else'strategic_DRAW_with_cooperation')
            if row['draw_category']!=category:raise ValueError('clock/structural draw attribution differs')
        counts['full_source_records']+=1
    return dict(mask=m,n=n,verified=True,counts=dict(counts),seconds=time.perf_counter()-tick,
        scope='Every physical vertex/frontier/terminal checked by separate finite integer model; selected full Core frontiers and all source full records checked. Same shared Core, no independent engine or exhaustive new Core replay.')


def verify(directory,bundle,output,*,core_samples=64):
    directory=Path(directory);worlds,plan,source=read_frozen(bundle);tick=time.perf_counter();rows=[];graphs=[]
    for path in sorted(directory.glob('mask*.json.gz')):
        g=json.loads(gzip.decompress(path.read_bytes()));n=g.get('n',4)
        for root in g['roots']:
            matched=[w for w in worlds if w['n']==n and w['mask']==g['mask']and w['rule']==root['rule']and w['record']==root['record']]
            if len(matched)!=1 or root['rank']!=matched[0]['rank']:raise ValueError('originalmu rank differs')
        receipt=qualify_graph(g,core_samples=core_samples);rows.append(receipt);graphs.append(g);print(receipt,flush=True)
    if pair_summary(graphs,plan)!=json.loads((directory/'summary.json').read_bytes())|{}:
        # The4board summary carries one explicit field documenting a repaired
        # presentation-only name collision after immutable graph completion.
        actual=pair_summary(graphs,plan);saved=json.loads((directory/'summary.json').read_bytes());saved.pop('qualification',None)
        if actual!=saved:raise ValueError('paired summary differs')
    result=dict(verified=True,source_bundle_sha256=source,rows=rows,seconds=time.perf_counter()-tick)
    Path(output).write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.directory,a.bundle,a.output)
