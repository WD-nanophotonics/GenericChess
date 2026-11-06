"""Small reproducible Core/exact-teacher/shared-value experiment, CPU only."""
from __future__ import annotations
import argparse,gzip,json,random,time
from datetime import datetime,timezone
from collections import Counter
from dataclasses import replace
from pathlib import Path
import torch
from torch import nn
from generic_chess.core.attacks import is_in_check
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.rules.schema import RuleSet,ruleset_to_dict,ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.validation import RuleValidationError
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_design import offsets
from scripts.research_record import record_value,write_record
from scripts.exact_generic_preference_solver_v3 import solve_root_threshold_v3
from scripts.leaper_neural_teacher import solve_session
from scripts.leaper_neural_model import LeaperValueNet,graph_from_session,batch_graphs,rule_signature

FAMILIES=((1,2),(1,8),(2,8),(3,8),(1,3),(2,3))
LABELS={'LOSS':0,'DRAW':1,'WIN':2}


def make_rules(size,family,locations,count=4,max_ply=4):
    a,b=FAMILIES[family]
    types=tuple(PieceType(t,t,tuple(LeapAtom(v) for v in offsets(mask)),is_anchor=t=='K') for t,mask in (('K',3),('A',a),('B',b)))
    board=[None]*(size*size)
    for cell,owner,tid in locations:board[cell]=Piece(owner,tid,tid)
    return RuleSet(board_size=size,piece_types=types,initial_position=tuple(tuple(board[y*size:(y+1)*size]) for y in range(size)),
        capture_disposition='remove_from_game',drop_allowed={t:((False,)*(size*size),)*2 for t in ('A','B')},
        max_ply=max_ply,repetition_limit=3,stalemate_result='draw')


def canonical_group(rules,s):
    # These six movement families are D4-symmetric. Group every rotated/reflected
    # copy, rename and current-player color swap together, before seeing labels.
    n=rules.board_size;sig={p.type_id:rule_signature(p) for p in rules.piece_types};versions=[]
    for mirror in (False,True):
        for rotations in range(4):
            cells=[]
            for i,p in enumerate(s.state.position.board):
                if p is None:continue
                x,y=i%n,i//n
                if mirror:x=n-1-x
                for _ in range(rotations):x,y=n-1-y,x
                cells.append((x,y,p.owner!=s.state.position.side_to_move,sig[p.current_type_id]))
            versions.append(tuple(sorted(cells)))
    return repr((n,rules.max_ply-s.state.ply_count,rules.repetition_limit,min(versions)))


def solve_teacher(session,max_nodes,rules=None):
    if rules is not None:
        result=solve_session(rules,session,max_nodes)
        return result['label'],result['nodes']
    result=session.result
    if result.status.value not in ('ongoing','no_contest'):
        return ('DRAW' if result.winner is None else 'WIN' if result.winner==session.state.position.side_to_move else 'LOSS'),0
    solved=solve_root_threshold_v3(session.compiled,session.state,max_nodes=max_nodes,max_depth=None)
    return (solved.root_value if solved.strong else None),solved.stats.get('states_expanded',0)


def prepare(output,roots4=384,roots5=128,nodes=1500,batch_seconds=600,max_ply=4,seed=20261107):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if (output/'dataset.json.gz').exists():raise FileExistsError('do not overwrite original study')
    config=dict(seed=seed,roots4=roots4,roots5=roots5,teacher_nodes_per_root=nodes,teacher_batch_seconds=batch_seconds,
        max_ply=max_ply,repetition_limit=3,pieces='3/4/5, cycled; two royal anchors plus ordinary leapers',
        samples='nonterminal Core-legal inputs; optional0/1/2 uniform legal prefix; no outcome selection',
        split='D4/color/rename-normalized current board+remainingclock groups assigned before labels,80/20',
        scope='finite'+str(max_ply)+'ply games; not full-length game strength or complete4x4 solve',
        training=dict(hidden=24,rounds=2,seeds=[0,1,2],epochs=160,batch_size=32,lr=.003,threads=2),
        continuation='Only interpret transfer if heldout4x4 balanced accuracy beats both cheap baselines by>=.05 and decisive accuracy improves. No tuning/refills after results.')
    plan_path=output/'plan.json'
    if plan_path.exists():
        if json.loads(plan_path.read_text(encoding='utf-8'))!=config:raise ValueError('resume must preserve original experiment')
    else:write_record(plan_path,config)
    original_start=plan_path.stat().st_mtime
    previous=[json.loads(line) for line in (output/'examples.jsonl').read_text(encoding='utf-8').splitlines()] if (output/'examples.jsonl').exists() else []
    saved={(r['size'],r['slot']):r for r in previous}
    rng=random.Random(config['seed']);rows=[];seen=set();tick=time.perf_counter();attempts=Counter();stopped=None
    for size,number in ((4,roots4),(5,roots5)):
        for slot in range(number):
            if time.time()-original_start>=batch_seconds:stopped='teacher_batch_cap';break
            family=slot%len(FAMILIES);s=None
            for attempt in range(100):
                attempts[str(size)]+=1;count=3+slot%3;cells=rng.sample(range(size*size),count)
                side=(slot//3)%2;pieces=[(cells[0],0,'K'),(cells[1],1,'K'),(cells[2],side,'A')]
                if count>=4:pieces.append((cells[3],1-side,'B'))
                if count>=5:pieces.append((cells[4],side,'B'))
                rules=make_rules(size,family,pieces,count,max_ply=max_ply)
                try:c=compile_ruleset(rules)
                except RuleValidationError:continue  # Random attacked-anchor starts are not legal inputs.
                candidate=GameSession(c)
                if candidate.result.status.value!='ongoing' or is_in_check(candidate.state.position,1,c):continue
                for _ in range((slot//6)%3):
                    if candidate.result.status.value!='ongoing':break
                    candidate.submit(rng.choice(candidate.legal_actions()))
                if candidate.result.status.value!='ongoing':continue
                group=canonical_group(rules,candidate)
                if group in seen:continue
                seen.add(group);s=candidate;break
            if s is None:
                rows.append(dict(size=size,slot=slot,status='NO_LEGAL_UNIQUE_INPUT'));continue
            split='validation' if random.Random(group).randrange(5)==0 else 'train'
            if (size,slot) in saved:
                prior=saved[size,slot]
                if prior['rules']!=ruleset_to_dict(rules) or prior['record']!=record_value(s.to_record()):raise ValueError('saved input changed')
                rows.append(prior);continue
            started=time.perf_counter();label,expanded=solve_teacher(s,nodes,rules)
            row=dict(size=size,slot=slot,family=family,group=group,split=split,rules=ruleset_to_dict(rules),record=record_value(s.to_record()),
                label=label,status='EXACT' if label is not None else 'UNKNOWN',teacher_nodes=expanded,teacher_seconds=time.perf_counter()-started)
            rows.append(row)
            # Preserve actual examples as they arrive; no archive/provenance layer.
            with (output/'examples.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(row,separators=(',',':'))+'\n')
            if slot%32==0:print(json.dumps(dict(size=size,done=slot+1,labels=dict(Counter(r.get('label') for r in rows if r['size']==size)),seconds=time.perf_counter()-tick)),flush=True)
        if stopped:break
    data=dict(config=config,rows=rows,teacher_seconds=time.time()-original_start,attempts=dict(attempts),stop=stopped)
    (output/'dataset.json.gz').write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))
    write_record(output/'teacher-summary.json',dict(seconds=data['teacher_seconds'],stop=stopped,labels={str(size):dict(Counter(r.get('label') or r['status'] for r in rows if r['size']==size)) for size in (4,5)},unknown_not_used_as_draw=True))
    return data


def replay(row):
    rules=ruleset_from_dict(row['rules']);c=compile_ruleset(rules)
    return rules,GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])))


def baseline_features(rules,s,g):
    c=s.compiled;stm=s.state.position.side_to_move;score=0.
    for p in s.state.position.board:
        if p is None or next(t for t in rules.piece_types if t.type_id==p.current_type_id).is_anchor:continue
        mobility=sum(len({sq for atom in at for sq in atom}) for at in c.leap_targets[p.current_type_id][p.owner])/len(s.state.position.board)
        score+=(1 if p.owner==stm else -1)*mobility/16
    material=torch.tensor([score,*g.globals.tolist()],dtype=torch.float32)
    src,dst=g.edges;geo=g.relations[:,4];owners=g.nodes[src,7];anchors=g.nodes[dst,8]
    checks=[float(is_in_check(s.state.position,owner,c)) for owner in (stm,1-stm)]
    feature=torch.tensor([float((geo*owners).sum())/16,float((geo*g.relations[:,7]*owners).sum())/16,
                          float((geo*g.relations[:,8]*owners).sum())/16,float((geo*anchors*owners).sum())/16,
                          float(g.relations[:,9].sum())/16,*checks])
    return material,torch.cat((material,feature))


def metrics(logits,labels):
    prob=logits.softmax(-1);pred=prob.argmax(-1);valid=labels!=1
    recalls=[float((pred[labels==k]==k).float().mean()) if (labels==k).any() else None for k in range(3)]
    return dict(n=len(labels),classes=torch.bincount(labels,minlength=3).tolist(),accuracy=float((pred==labels).float().mean()),
        balanced_accuracy=sum(x for x in recalls if x is not None)/sum(x is not None for x in recalls),recall_LDW=recalls,
        decisive_accuracy=float((pred[valid]==labels[valid]).float().mean()) if valid.any() else None,
        cross_entropy=float(nn.functional.cross_entropy(logits,labels)),brier=float(((prob-nn.functional.one_hot(labels,3))**2).sum(-1).mean()))


def train(output,train_seconds=360):
    whole_start=time.perf_counter();output=Path(output);data=json.loads(gzip.decompress((output/'dataset.json.gz').read_bytes()));torch.set_num_threads(2)
    rows=[r for r in data['rows'] if r.get('status')=='EXACT'];graphs=[];materials=[];structures=[]
    for r in rows:
        rules,s=replay(r);g=graph_from_session(rules,s);graphs.append(g);a,b=baseline_features(rules,s,g);materials.append(a);structures.append(b)
    y=torch.tensor([LABELS[r['label']] for r in rows]);train_idx=[i for i,r in enumerate(rows) if r['size']==4 and r['split']=='train'];val_idx=[i for i,r in enumerate(rows) if r['size']==4 and r['split']=='validation'];five=[i for i,r in enumerate(rows) if r['size']==5]
    if not train_idx or not val_idx:raise ValueError('insufficient exact train/validation examples')
    weights=torch.bincount(y[train_idx],minlength=3).float();weights=torch.where(weights>0,len(train_idx)/(3*weights.clamp_min(1)),0.)
    trained=[];baselines={};config=data['config']['training'];tick=time.perf_counter()
    def assess(model,idx,features=None):
        logits=[]
        with torch.no_grad():
            for begin in range(0,len(idx),32):
                ids=idx[begin:begin+32];logits.append(model(batch_graphs([graphs[i] for i in ids])) if features is None else model(features[ids]))
        return metrics(torch.cat(logits),y[idx]) if idx else None
    for name,features in [('material',torch.stack(materials)),('structure',torch.stack(structures))]:
        torch.manual_seed(17);m=nn.Linear(features.shape[1],3);opt=torch.optim.Adam(m.parameters(),lr=.03)
        for _ in range(300):
            opt.zero_grad();loss=nn.functional.cross_entropy(m(features[train_idx]),y[train_idx],weight=weights);loss.backward();opt.step()
        baselines[name]=dict(train=assess(m,train_idx,features),validation4=assess(m,val_idx,features),zero_shot5=assess(m,five,features))
    for seed in config['seeds']:
        torch.manual_seed(seed);model=LeaperValueNet(config['hidden'],config['rounds']);opt=torch.optim.Adam(model.parameters(),lr=config['lr']);rng=random.Random(seed);history=[];epochs=0;start=time.perf_counter()
        for epoch in range(config['epochs']):
            if time.perf_counter()-tick>=train_seconds:break
            ids=list(train_idx);rng.shuffle(ids);loss_sum=0.
            for begin in range(0,len(ids),config['batch_size']):
                ix=ids[begin:begin+config['batch_size']];opt.zero_grad();logits=model(batch_graphs([graphs[i] for i in ix]));loss=nn.functional.cross_entropy(logits,y[ix],weight=weights);loss.backward();opt.step();loss_sum+=float(loss.detach())*len(ix)
            epochs=epoch+1
            if epoch%40==0:
                history.append(dict(epoch=epochs,loss=loss_sum/len(ids),validation=assess(model,val_idx)));print(json.dumps(dict(seed=seed,epoch=epochs,loss=loss_sum/len(ids))),flush=True)
        torch.save(dict(state_dict=model.state_dict(),hidden=config['hidden'],rounds=config['rounds'],seed=seed),output/f'value4-seed{seed}.pt')
        trained.append(dict(seed=seed,epochs=epochs,seconds=time.perf_counter()-start,parameters=sum(p.numel() for p in model.parameters()),train=assess(model,train_idx),validation4=assess(model,val_idx),zero_shot5=assess(model,five),curve=history))
    if not trained:raise ValueError('training budget used before a model fit')
    score=sum(x['validation4']['balanced_accuracy'] for x in trained)/len(trained);best=max(x['validation4']['balanced_accuracy'] for x in baselines.values())
    decisive=sum(x['validation4']['decisive_accuracy'] or 0 for x in trained)/len(trained);base_decisive=max(x['validation4']['decisive_accuracy'] or 0 for x in baselines.values())
    passed=score>=best+.05 and decisive>base_decisive and all(x['epochs']==config['epochs'] for x in trained)
    result=dict(status='B_PASS_FINITE_PILOT' if passed else 'B_NO_GO_OR_INCONCLUSIVE',baselines=baselines,models=trained,seconds=time.perf_counter()-tick,
        mean_validation4_balanced_accuracy=score,best_baseline=best,continued_to_transfer=False,preprocessing_seconds=tick-whole_start,end_to_end_training_seconds=time.perf_counter()-whole_start,
        limitation='Only finite-clock games and6exposed movement pairs; labels exact for those full clocks. No5x5 finetuning, no Arena/strength/general-transfer claim. All exact5x5 data used only for untouched zero-shot description; they are not yet a5x5train/test study.')
    write_record(output/'learning-result.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ('models','baselines')}),flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','train']);p.add_argument('--output',type=Path,required=True);p.add_argument('--roots4',type=int,default=384);p.add_argument('--roots5',type=int,default=128);p.add_argument('--nodes',type=int,default=1500);p.add_argument('--batch-seconds',type=float,default=600);p.add_argument('--train-seconds',type=float,default=360);p.add_argument('--max-ply',type=int,default=4);p.add_argument('--seed',type=int,default=20261107);a=p.parse_args()
    if a.mode=='prepare':prepare(a.output,a.roots4,a.roots5,a.nodes,a.batch_seconds,a.max_ply,a.seed)
    else:train(a.output,a.train_seconds)
