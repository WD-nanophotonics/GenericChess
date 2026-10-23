"""Portable cooperative witnesses and negative distance-potential certificates.

The verifier regenerates all Core choices; it never trusts producer adjacency,
SCC labels, shortest-path computation or a serialized Python object. A root
potential greater than remaining plies proves no decisive path can fit. Edges
entering a previously thrice-visited nonterminal Position are actual draw
barriers under this frozen repeat4 rule. Mate precedence is preserved.
"""
from dataclasses import replace
from collections import Counter
import argparse
import gzip
import hashlib
import json
import pickle
from pathlib import Path
import time

from generic_chess.core.pieces import Piece
from generic_chess.core.actions import action_from_dict
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.transition import legal_successors
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from scripts.leaper_retrograde import fresh_state
from scripts.leaper_design import state_sha
from scripts.leaper_explorer_truth import load, save, digest
from scripts.leaper_cooperative_truth import admit, cooperative_distances
from scripts.leaper_microgames import role_stop_requested

ALPHABET=((0,'K'),(0,'A'),(0,'B'),(1,'K'),(1,'A'),(1,'B'))


def encode_position(pos, template):
    raw=[pos.side_to_move, ''.join('0'if pc is None else str(1+ALPHABET.index((pc.owner,pc.current_type_id)))for pc in pos.board)]
    assert decode_position(raw,template)==pos
    return raw


def decode_position(raw, template):
    if (len(raw)!=2 or type(raw[0])is not int or raw[0]not in(0,1)or
        not isinstance(raw[1],str)or len(raw[1])!=len(template.board)or set(raw[1])-set('0123456')):
        raise ValueError('invalid compact Position')
    board=tuple(None if ch=='0'else Piece(*ALPHABET[int(ch)-1],ALPHABET[int(ch)-1][1])for ch in raw[1])
    return replace(template,side_to_move=raw[0],board=board)


def root_session(truth, hid, compiled):
    r=next(r for r in truth['roots']if r['id']==hid)
    record=truth['records'][r['record_id']]
    s=GameSession.replay(compiled,deserialize_game_record(json.dumps(record|dict(actions=record['actions'][:r['ply']]))))
    assert state_sha(s.state)==hid
    return r,s


def pack(truth, cooperative):
    assert cooperative['source_truth_digest']==digest(truth)
    # A proposer graph need not be trusted or pre-audited. The independent
    # potential verifier checks every relevant Core edge and closure itself.
    checks={r['path']:r for r in cooperative['graph_checks']}
    packet=dict(format='leaper-cooperative-certificates-v1',truth_digest=digest(truth),
                cooperative_digest=digest(cooperative),graphs={},proofs=[])
    for row in cooperative['rows']:
        if row['cooperative_decisive']:continue
        path=Path(row['graph']);raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==checks[row['graph']]['sha256']
        g=pickle.loads(gzip.decompress(raw));fp=row['fingerprint'];c=compile_rule(ruleset_from_dict(truth['rules'][fp]))
        r,s=root_session(truth,row['id'],c)
        decisive={i for i,w in g['terminals'].items()if w is not None}
        key_index={repetition_identity_key(p,c):i for i,p in enumerate(g['positions'])}
        blocked=sorted(key_index[key]for key,n in s.state.repetition_counts if n==3 and key in key_index)
        ds,_=cooperative_distances(g['edges'],decisive,blocked)
        cap=r['rule_remaining']+1
        potential=[min(ds.get(i,cap),cap)for i in range(len(g['positions']))]
        template=GameSession(c).state.position
        graph_id=checks[row['graph']]['sha256']
        if graph_id not in packet['graphs']:
            packet['graphs'][graph_id]=dict(fingerprint=fp,positions=[encode_position(p,template)for p in g['positions']])
        packet['proofs'].append(dict(id=r['id'],graph_id=graph_id,blocked=blocked,
                                     root_index=g['indices'][s.state.position],potential=potential))
    return packet


def verify(truth,cooperative,packet,*,seconds=1200):
    start=time.perf_counter();stats=Counter();last_stop_check=0.
    assert packet['truth_digest']==digest(truth)and packet['cooperative_digest']==digest(cooperative)
    compiled={fp:compile_rule(ruleset_from_dict(raw))for fp,raw in truth['rules'].items()}
    for fp,c in compiled.items():admit(ruleset_from_dict(truth['rules'][fp]),c)
    for row in cooperative['rows']:
        r,s=root_session(truth,row['id'],compiled[row['fingerprint']])
        if row['cooperative_decisive']:
            assert len(row['witness'])<=r['rule_remaining']
            for ac in row['witness']:s.submit(action_from_dict(ac));stats['positive_edges']+=1
            assert s.result.winner is not None and s.result.winner==row['terminal']['winner']
            stats['positive_roots']+=1
    for graph_id,raw in packet['graphs'].items():
        c=compiled[raw['fingerprint']];template=GameSession(c).state.position
        positions=[decode_position(p,template)for p in raw['positions']];indices={p:i for i,p in enumerate(positions)}
        assert len(indices)==len(positions)
        proofs=[p for p in packet['proofs']if p['graph_id']==graph_id]
        checked=[]
        for proof in proofs:
            r,s=root_session(truth,proof['id'],c);potential=proof['potential'];blocked=set(proof['blocked'])
            assert len(potential)==len(positions)and all(type(v)is int and 0<=v<=r['rule_remaining']+1 for v in potential)
            key_index={repetition_identity_key(pos,c):i for i,pos in enumerate(positions)}
            assert blocked=={key_index[key]for key,n in s.state.repetition_counts if n==3 and key in key_index}
            assert positions[proof['root_index']]==s.state.position and potential[proof['root_index']]>r['rule_remaining']
            checked.append((potential,blocked))
        for i,pos in enumerate(positions):
            now=time.perf_counter()
            if now-start>=seconds:raise RuntimeError('VERIFICATION_CAP_UNKNOWN')
            if now-last_stop_check>=.2:
                last_stop_check=now
                if role_stop_requested():raise RuntimeError('USER_STOP')
            state=fresh_state(pos,c)
            if state.terminal_status.is_terminal:
                if state.terminal_status.winner is not None:
                    assert all(p[i]==0 for p,_ in checked)
                stats['terminal_vertices']+=1
            else:
                for _,ch in legal_successors(state,c):
                    j=indices[ch.position]  # Missing closure vertex rejects.
                    terminal=ch.terminal_status.is_terminal and ch.terminal_status.winner is not None
                    for potential,blocked in checked:
                        if j not in blocked or terminal:assert potential[i]<=1+potential[j]
                    stats['negative_core_edges']+=1
            stats['negative_core_positions']+=1
        stats['negative_roots']+=len(proofs);stats['graphs']+=1
    negative_ids={p['id']for p in packet['proofs']}
    assert negative_ids=={r['id']for r in cooperative['rows']if not r['cooperative_decisive']}
    return dict(verified=True,seconds=time.perf_counter()-start,counts=dict(stats),
                scope='Only selected cooperative path/absence claims. Does not verify all imported minimax labels or policy probabilities.')


def main():
    cli=argparse.ArgumentParser();cli.add_argument('command',choices=('pack','verify'));cli.add_argument('--truth',required=True);cli.add_argument('--cooperative',required=True);cli.add_argument('--packet',required=True);cli.add_argument('--output')
    args=cli.parse_args();truth=load(args.truth);cooperative=load(args.cooperative)
    if args.command=='pack':
        result=pack(truth,cooperative);save(args.packet,result)
        print(json.dumps(dict(graphs=len(result['graphs']),negative_proofs=len(result['proofs']))))
    else:
        result=verify(truth,cooperative,load(args.packet));save(args.output,result);print(json.dumps(result))


if __name__=='__main__':main()
