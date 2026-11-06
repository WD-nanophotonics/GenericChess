"""D4 sensitivity of frozen value estimates on full Core replay records.

No solver queries, training or symmetry ensemble. Every transformed legal action
frontier is checked against the transformed original frontier before using WDL.
"""
import argparse
from dataclasses import replace
import gzip
import json
from pathlib import Path
import time

import torch
from generic_chess.core.actions import action_to_dict
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_neural_experiment import LABELS,replay,metrics
from scripts.leaper_neural_model import LeaperValueNet,graph_from_session,batch_graphs
from scripts.research_record import write_record


def point(x,y,n,mirror,rotations):
    if mirror:x=n-1-x
    for _ in range(rotations):x,y=n-1-y,x
    return [x,y]


def action(raw,n,mirror,rotations):
    return dict(raw,**{k:point(*raw[k],n,mirror,rotations) for k in ('from','to')})


def transformed(rules,record,mirror,rotations):
    n=rules.board_size;board=[[None]*n for _ in range(n)]
    for y,row in enumerate(rules.initial_position):
        for x,p in enumerate(row):
            nx,ny=point(x,y,n,mirror,rotations);board[ny][nx]=p
    # All six admitted pilot families are exactly D4 invariant. Verify that
    # condition rather than treating a rotation of an asymmetric rule as equal.
    for piece in rules.piece_types:
        offsets={a.offset for a in piece.movement_atoms}
        moved=set()
        for x,y in offsets:
            if mirror:x=-x
            for _ in range(rotations):x,y=-y,x
            moved.add((x,y))
        if moved!=offsets:raise ValueError('this diagnostic requires D4-symmetric movement')
    r=replace(rules,initial_position=tuple(tuple(row) for row in board));c=compile_ruleset(r)
    rec=dict(record,ruleset_fingerprint=c.ruleset_fingerprint,actions=[action(a,n,mirror,rotations) for a in record['actions']])
    return r,GameSession.replay(c,deserialize_game_record(json.dumps(rec)))


def run(base):
    base=Path(base);destination=base/'symmetry-analysis.json'
    if destination.exists():raise FileExistsError('keep original analysis')
    tick=time.perf_counter();torch.set_num_threads(2)
    raw=json.loads(gzip.decompress((base/'dataset.json.gz').read_bytes()))['rows']
    rows=[r for r in raw if r['status']=='EXACT' and (r['size']==5 or r['split']=='validation')]
    graphs=[];ids=[]
    for i,row in enumerate(rows):
        rules,s=replay(row)
        original=[action_to_dict(a) for a in s.legal_actions()]
        for mirror in (False,True):
            for rotation in range(4):
                rr,ss=transformed(rules,row['record'],mirror,rotation)
                expected={json.dumps(action(a,rules.board_size,mirror,rotation),sort_keys=True) for a in original}
                actual={json.dumps(action_to_dict(a),sort_keys=True) for a in ss.legal_actions()}
                if actual!=expected or ss.result!=s.result:raise ValueError('Core symmetry/replay mismatch')
                graphs.append(graph_from_session(rr,ss));ids.append(i)
    y=torch.tensor([LABELS[r['label']] for r in rows])
    results=[]
    for seed in (0,1,2):
        saved=torch.load(base/f'value4-seed{seed}.pt',map_location='cpu',weights_only=True)
        m=LeaperValueNet(saved['hidden'],saved['rounds']);m.load_state_dict(saved['state_dict']);m.eval()
        with torch.no_grad():
            logits=torch.cat([m(batch_graphs(graphs[start:start+32])) for start in range(0,len(graphs),32)]).reshape(len(rows),8,3)
        probs=logits.softmax(-1);pred=logits.argmax(-1)
        for size in (4,5):
            ix=torch.tensor([i for i,r in enumerate(rows) if r['size']==size]);yy=y[ix];pp=pred[ix]
            decisive=yy!=1
            results.append(dict(seed=seed,size=size,roots=len(ix),decisive_roots=int(decisive.sum()),
                                top_class_changes_under_D4=int((pp!=pp[:,0:1]).any(-1).sum()),
                                decisive_any_view_correct=int((pp[decisive]==yy[decisive,None]).any(-1).sum()),
                                decisive_all_views_wrong=int((pp[decisive]!=yy[decisive,None]).all(-1).sum()),
                                mean_probability_range=float((probs[ix].max(1).values-probs[ix].min(1).values).max(-1).values.mean()),
                                views=[metrics(logits[ix,k],yy) for k in range(8)]))
    result=dict(seconds=time.perf_counter()-tick,roots=len(rows),Core_transformed_replays=len(graphs),solver_queries=0,training=0,models=results,
                limitation='Equivalent rotated/reflected views of the same heldout roots are dependent, not new samples. Sensitivity alone does not identify the cause of cross-size failure; no ensemble or new selection of best view.')
    write_record(destination,result)
    print(json.dumps({k:v for k,v in result.items() if k!='models'}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);a=p.parse_args();run(a.base)
