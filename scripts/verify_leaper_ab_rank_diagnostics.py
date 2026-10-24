"""Qualify source scope, repetition injection, literal PVs and rank labels.

One full source graph qualification is hash-bound, not redundantly rerun here.
No positive label is inferred solely from an inspection carrier or Position TT.
"""
from pathlib import Path
from collections import Counter
from copy import copy
import argparse,json,time
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import source_documents,restore,write
from scripts.leaper_ab_rank_diagnostics import load_graph
from scripts.verify_leaper_frozen_learning import replay_query
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.actions import action_to_dict

CONTACT='da92b6a1c814795b455875a48540227f34c94807932a559d309c67ccc6a520e5'


def qualify_premises(g,c,indices):
    world=json.loads(source_documents()['contact/inputs.json'])
    if g['rule']!=world['rule']or c.ruleset_fingerprint!=CONTACT:raise ValueError('rank scope requires exact frozen source RuleSet')
    rule=L.ruleset_from_dict(g['rule'])
    if rule.board_size!=5 or rule.capture_disposition!='remove_from_game'or c.support.max_ply!=64 or c.support.repetition_limit!=4 or c.support.repetition_policy!='draw':raise ValueError('unsupported clock/removal/history scope')
    if c.declarations or rule.promotion_allowed or rule.promotion_forced or any(p.is_promotable or any(type(a).__name__!='LeapAtom'for a in p.movement_atoms)for p in rule.piece_types):raise ValueError('unsupported semantic effects')
    if any(any(mask)for masks in rule.drop_allowed.values()for mask in masks):raise ValueError('unsupported drop')
    for name in('no_progress_draw','automatic_adjudications','consecutive_action_adjudications','repeated_cycle_target_conditions'):
        if getattr(c.support,name,None):raise ValueError('unsupported extra terminal authority')
    keys={repetition_identity_key(p,c)for p in indices}
    if len(keys)!=len(indices):raise ValueError('Position ranks are not injective in actual repetition identity')
    return dict(fingerprint=CONTACT,vertices=len(indices),distinct_actual_repetition_keys=len(keys),plain_scope=True)


def history_label(s,indices,values,ranks):
    if s.state.terminal_status.is_terminal:return 0 if s.result.winner is None else 1 if s.result.winner==0 else-1
    if s.state.position not in indices:return None
    i=indices[s.state.position];v=values[i]*(1 if s.state.position.side_to_move==0 else-1)
    if v==0:return 0
    if v!=1:raise ValueError('bare opponent has a scoring value')
    if ranks[i]>64-s.state.ply_count or any(n>=3 for _,n in s.state.repetition_counts):return None
    return 1


def verify(graph,directory,graph_receipt,output):
    began=time.perf_counter();g,c,indices,values,ranks=load_graph(graph);receipt=json.loads(graph_receipt.read_bytes())
    if not receipt['verified']or receipt['sha256']!=L.sha(graph):raise ValueError('complete Core graph qualification absent or hash differs')
    premises=qualify_premises(g,c,indices);spec=json.loads((directory/'spec.json').read_bytes());results=json.loads((directory/'result.json').read_bytes());counts=Counter();groups={}
    if spec['graph_sha256']!=L.sha(graph):raise ValueError('diagnostic graph binding differs')
    for row in results['rows']:
        slot=row['slot'];s=restore(c,spec['selected'][slot['root']]['record'])
        if L.state_sha(s.state)!=row['state_sha256']:raise ValueError('diagnostic full history differs')
        value=history_label(s,indices,values,ranks)
        if value!=row['root_value']:raise ValueError('diagnostic root label differs')
        actual={json.dumps(L.record_value(a),sort_keys=True):a for a in s.legal_actions()};saved={json.dumps(a['action'],sort_keys=True):a for a in row['actions']}
        if set(actual)!=set(saved):raise ValueError('diagnostic complete frontier differs')
        for key,a in actual.items():
            ch=copy(s);ch.submit(a)
            if saved[key]['value']!=history_label(ch,indices,values,ranks):raise ValueError('diagnostic child rank/clock/history label differs')
        labels=[b['value']for b in row['actions']]
        if all(v is not None for v in labels)and max(labels)!=value:raise ValueError('full history Bellman relation differs')
        r=row['receipt'];chosen=None
        if r['complete']and r['action']is not None:
            action=L.match_action(s,r['action']['action']);counts['PV_plies']+=replay_query(s,[1,slot['B'],0,0],r,action_to_dict(action));ch=copy(s);ch.submit(action);chosen=history_label(ch,indices,values,ranks)
        if chosen!=row['chosen_value']or row['suboptimal']!=(None if chosen is None or value is None else chosen<value):raise ValueError('diagnostic chosen action quality differs')
        key=str((slot['depth'],slot['B']));group=groups.setdefault(key,Counter());group['queries']+=1;group['suboptimal']+=int(row['suboptimal']is True);group['UNKNOWN']+=int(row['suboptimal']is None);group['nodes']+=r['nodes'];group['completed_'+str(r['completed_depth'])]+=1
        counts['queries']+=1;counts['nodes']+=r['nodes']
    out=dict(verified=True,premises=premises,groups={k:dict(v)for k,v in groups.items()},counts=dict(counts),seconds=time.perf_counter()-began,
        scope='Finite source-bound rank/clock/history lift with injective repetition identities and incomingcounts<=2, plus literal returned PVs. No arbitrary Position quotient, oracle training root, population utility or new Player call.')
    write(output,out);return out


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--graph',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);ap.add_argument('--graph-receipt',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();verify(a.graph,a.directory,a.graph_receipt,a.output)
