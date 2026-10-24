"""Independent literal Core truth AND incoming-law action-aliasing check."""
from collections import defaultdict,Counter
from fractions import Fraction as F
from itertools import combinations
from pathlib import Path
import json,time,hashlib
from scripts.leaper_explorer_truth import load,digest
from scripts.leaper_h6_initial_truth import admit
from scripts.leaper_microgames import ExactTree,role_stop_requested
from scripts.leaper_history_edit_context import SOURCE
from scripts.leaper_cooperative_certificate import decode_position
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_to_dict
from generic_chess.core.movegen import legal_actions

def verify(expected,output,seconds=600):
    tick=time.perf_counter();inputs=load(SOURCE/'inputs.json.gz');adj=load(SOURCE/'adjacent-pairs.json.gz');pair=adj['pairs'][0];rows=[]
    for tag,record in(('left_family','left_record'),('right_family','right_record')):
        family=next(f for f in inputs['families']if f['family']==pair[tag]);src=next(r for r in inputs['rows']if r['family']==family['family']);c=admit(family,src)
        starts=[GameSession.replay(c,deserialize_game_record(json.dumps(r[record]))).state for r in pair['rows']]
        tree=ExactTree(c,max_states=150000,seconds=240)
        for start in starts:tree.solve(start)
        if role_stop_requested()or time.perf_counter()-tick>seconds:raise RuntimeError('LITERAL_ACTION_LAW_CAP_UNKNOWN_NO_REFILL')
        ordered={};bestsets=defaultdict(set)
        for state,edges in tree.edges.items():
            if not edges:continue
            children=dict(edges);actions=list(legal_actions(state,c));ordered[state]=tuple((a,children[a])for a in actions)
            v=tree.values[state];best=frozenset(json.dumps(action_to_dict(a),sort_keys=True)for a,ch in ordered[state]if tree.values[ch]==v)
            bestsets[state.position,state.ply_count].add(best)
        groups=dict(Position_clock_groups=len(bestsets),distinct_optimal_set_groups=sum(len(s)>1 for s in bestsets.values()),no_shared_optimal_action_groups=sum(not set.intersection(*(set(x)for x in s))for s in bestsets.values()))
        old=next(r for r in expected['rows']if r['family']==family['family'])
        domain=load(SOURCE/f"domain{family['family']}.json.gz");positions=[decode_position(p,c.initial_position)for p in domain['positions']]
        if 'nontrivial_action_covers'in old:
            nontrivial={(positions[r['vertex']],6-r['remaining']):r for r in old['nontrivial_action_covers']}
            histogram=Counter()
            for group,sets in bestsets.items():
                pos,ply=group
                if group not in nontrivial:
                    if not set.intersection(*(set(x)for x in sets)):raise ValueError('omitted nontrivial action cover')
                    size=1
                else:
                    r=nontrivial[group];allactions=[json.dumps(a,sort_keys=True)for a in domain['actions'][r['vertex']]]
                    selected={allactions[i]for i in r['cover_offsets']};size=r['minimum_actions']
                    if len(selected)!=size or any(not selected&best for best in sets):raise ValueError('action-cover upper certificate fails')
                    if any(all(set(candidate)&best for best in sets)for candidate in combinations(allactions,size-1)):raise ValueError('action-cover lower certificate fails')
                    if r['oracle_tag_bits']!=(size-1).bit_length():raise ValueError('tag-bit count differs')
                histogram[str((ply,size,(size-1).bit_length()))]+=1
            if dict(histogram)!=old['action_cover_counts']:raise ValueError('literal minimum action-cover histogram differs')
        if groups!=old['groups']:raise ValueError('literal incompatible-action groups differ')
        laws=[]
        for foe in('UNIFORM','FLOOR'):
            incoming=defaultdict(F)
            for state in starts:incoming[state]+=F(1,len(starts))
            costs=defaultdict(lambda:defaultdict(F));mass=Counter();visits=F(0);group_mass=defaultdict(F)
            for ply in range(6):
                nxt=defaultdict(F)
                for state,prob in incoming.items():
                    if not tree.edges[state]:continue
                    actor=state.position.side_to_move;visits+=prob;mass[actor]+=prob;group=state.position,state.ply_count;group_mass[group]+=prob
                    for a,ch in ordered[state]:costs[group][json.dumps(action_to_dict(a),sort_keys=True)]+=prob*(tree.values[ch]!=tree.values[state])
                    choices=ordered[state]
                    if foe=='FLOOR' and actor==1:
                        immediate=[(a,ch)for a,ch in choices if ch.terminal_status.is_terminal and ch.terminal_status.winner==1]
                        if immediate:choices=immediate[:1]
                    for a,ch in choices:nxt[ch]+=prob/len(choices)
                incoming=nxt
            minimum={s:sum((min(cs.values())for(pos,ply),cs in costs.items()if pos.side_to_move==s),F(0))for s in(0,1)}
            saved=next(x for x in old['laws']if x['opponent']==foe)
            actual=dict(opponent=foe,expected_decisions=str(visits),seat_decision_mass={str(s):str(mass[s])for s in(0,1)},unavoidable_one_decision_errors={str(s):str(minimum[s])for s in(0,1)},minimum_error_per_decision={str(s):str(minimum[s]/mass[s])for s in(0,1)})
            if actual!={k:saved[k]for k in actual}:raise ValueError('literal exact incoming action law differs')
            positive={(pos,ply)for(pos,ply),cs in costs.items()if min(cs.values())>0}
            if positive!={(positions[r['vertex']],6-r['remaining'])for r in saved['positive_groups']}:raise ValueError('positive incoming group support differs')
            for r in saved['positive_groups']:
                group=(positions[r['vertex']],6-r['remaining']);cs=costs[group]
                by_offset={str(i):str(cs[json.dumps(a,sort_keys=True)])for i,a in enumerate(domain['actions'][r['vertex']])}
                if str(group_mass[group])!=r['mass']or str(min(cs.values()))!=r['minimum_error_mass']or by_offset!=r['cost_by_action']:raise ValueError('literal per-group/action incoming weights differ')
            laws.append(actual)
        rows.append(dict(family=family['family'],literal_full_GameStates=len(tree.values),literal_Core_edges=sum(len(ee)for ee in tree.edges.values()),groups=groups,laws=laws));print(rows[-1],flush=True)
    result=dict(verified=True,source_digest=digest(expected),rows=rows,seconds=time.perf_counter()-tick,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Every original common-root actual fullGameState continuation, exact literal WDL/action frontiers and Fraction incomingUniform/FLOOR mass. No compact vertex/history label supplies this control. SharedCore, not an independent engine or deployed policy estimate.')
    Path(output).write_text(json.dumps(result,indent=2));print({k:v for k,v in result.items()if k!='rows'});return result

if __name__=='__main__':verify(load(Path('artifacts/leaper-future-history-cone-20261024/action-necessity.json')),Path('artifacts/leaper-future-history-cone-20261024/action-law-literal.json'))
