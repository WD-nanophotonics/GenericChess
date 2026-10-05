"""One frozen fresh cutoff-safety development root. Never rerun output."""
from dataclasses import asdict,replace
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.material_leaf_choice import material_score,one_ply_choice
from scripts.native_chess_contact_intervals import contact_interval_choice,EMPTY_AUX,FINGERPRINT
from scripts.public_goal_intervals import PublicGame

OUT=ROOT/'docs/research/data/cutoff_safety_use_20261005.json'
FREEZE=OUT.with_suffix('.selections.json')
SOURCES=('scripts/audit_cutoff_safety_use.py','scripts/native_chess_contact_intervals.py',
         'scripts/material_interval_choice.py','scripts/material_leaf_choice.py',
         'scripts/public_goal_intervals.py','scripts/audit_exchange_custody.py',
         'generic_chess/rules/western_chess.py','generic_chess/rules/compiler.py',
         'generic_chess/core/transition.py','generic_chess/core/semantic_executor.py',
         'generic_chess/core/terminal.py','docs/research/CUTOFF_SAFETY_USE_PROTOCOL.md',
         'docs/research/CUTOFF_SOURCE_APPLICABILITY.md',
         'docs/research/NATIVE_CONTACT_INTERVAL_INTERFACE_DESIGN.md',
         'docs/research/PAWN_PREFIX_SUPPORT_OVERLAP_RESULTS.md')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def friendly(value):
    if isinstance(value,dict):
        return {str(k):friendly(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return [friendly(v) for v in value]
    return str(value) if isinstance(value,F) else value


def audit(report):
    start=monotonic()
    def check():
        if monotonic()-start>=15:
            raise TimeoutError('15sec total source/use cap')
    def actions(state):
        result={}
        for a in game.actions(state,check):
            check()
            if report['enumerated']>=5000 or len(result)>=128:
                raise ValueError('5000 total/128 per node action cap')
            report['enumerated']+=1;key=str(a)
            if key in result:
                raise ValueError('lossless action ID collision')
            result[key]=a
        return result
    def play(state,action):
        check()
        if report['public_transitions']>=128:
            raise ValueError('128 total public transition cap')
        report['public_transitions']+=1
        return game.successor(state,action)
    c=compile_ruleset_for_execution(build_western_chess_ruleset());game=PublicGame(c)
    report['source_premises']={
        'max_ply1000':c.support.max_ply==1000,
        'repetition100000_draw':c.support.repetition_limit==100000 and c.support.repetition_policy=='draw',
        'stalemate_draw':c.support.stalemate_result=='draw',
        'no_other_history_adjudication':not c.support.automatic_adjudications and not c.support.consecutive_action_adjudications and c.support.no_progress_draw is None,
        'no_declarations_cycle_rules':not c.ir.declarations and not c.ir.repeated_cycle_target_conditions,
        'consistent_prefix_count_bound':1001<100000,
        'pinned_rules':initial_state(c).position.ruleset_fingerprint==FINGERPRINT}
    if not all(report['source_premises'].values()):
        raise ValueError('cutoff source qualification failed')
    board=[None]*64
    for sq,owner,tid in ((9,0,'K'),(53,0,'P'),(35,1,'K'),(18,1,'R'),(0,1,'N')):
        board[sq]=Piece(owner,tid,tid)
    p=replace(initial_state(c).position,board=tuple(board),side_to_move=0,aux_state=EMPTY_AUX)
    root=replace(synthetic_state(c,p),ply_count=998)
    report['root_state']=asdict(root)
    if game.terminal(root).is_terminal:
        raise ValueError('predeclared root not ongoing')
    complete_actions=actions(root);children={key:play(root,a) for key,a in complete_actions.items()}
    selections={model:contact_interval_choice(children,game,owner=0,duration=model,complete=True)
                for model in ('geometric_half','linear_mixture','both')}
    weights={('board',tid):F(1) for tid in ('P','N','B','R','Q')}
    selections['unit']=one_ply_choice(children,game,
        lambda s:material_score(s.position,weights,{'K'},30),owner=0,complete=True)
    selections['zero']=one_ply_choice(children,game,lambda s:F(0),owner=0,complete=True)
    report['complete_choice_count']=len(children)
    report['all_children']={key:asdict(s) for key,s in children.items()}
    report['selections_before_labels']=friendly(selections)
    if not all(v['complete'] for v in selections.values()):
        raise ValueError('whole root interface incomplete')
    FREEZE.write_text(json.dumps(friendly({k:report[k] for k in (
        'root_state','all_children','selections_before_labels','source_premises')}),
        sort_keys=True,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
    report['prelabel_freeze_sha256']=sha(FREEZE)
    report['all_selections_frozen_before_goal_expansion']=True
    for key in sorted({v['selected'] for v in selections.values() if v['selected'] is not None}):
        child=children[key];t=game.terminal(child)
        row=dict(child_ply=child.ply_count,replies=[],complete_replies=False,interval=[-1,1])
        report['selected_goal_evidence'][key]=row
        if t.is_terminal:
            value=0 if t.winner is None else 1 if t.winner==0 else -1
            row.update(interval=[value,value],terminal_child=True,complete_replies=True)
            continue
        if child.ply_count!=999 or child.position.side_to_move!=1:
            raise ValueError('selected source not opponent at ply999')
        replies=actions(child)
        if len(replies)>64 or not replies:
            raise ValueError('selected child needs nonempty <=64 complete replies')
        values=[]
        for reply_id,a in replies.items():
            leaf=play(child,a);goal=game.terminal(leaf)
            if leaf.ply_count!=1000 or not goal.is_terminal:
                raise ValueError('unqualified endpoint: do not invent a draw')
            value=0 if goal.winner is None else 1 if goal.winner==0 else -1
            values.append(value)
            row['replies'].append(dict(action_id=reply_id,state=asdict(leaf),value=value))
            row['interval']=[-1,min(values)]
        row.update(complete_replies=True,interval=[min(values),min(values)])
    for model in ('geometric_half','linear_mixture','both'):
        chosen=selections[model]['selected'];report['paired_margins'][model]={}
        for baseline in ('unit','zero'):
            other=selections[baseline]['selected']
            if chosen is None:
                interval=[-2,2]
            elif chosen==other:
                interval=[0,0]
            else:
                a=report['selected_goal_evidence'][chosen]['interval']
                b=report['selected_goal_evidence'][other]['interval']
                interval=[a[0]-b[1],a[1]-b[0]]
            report['paired_margins'][model][baseline]=interval
    report['complete']=True;report['seconds']=monotonic()-start


if __name__=='__main__':
    if OUT.exists() or FREEZE.exists():
        raise FileExistsError('frozen output already exists; never rerun')
    if not OUT.parent.is_dir():
        raise FileNotFoundError('preflight report destination before observation')
    report=dict(complete=False,public_transitions=0,enumerated=0,selected_goal_evidence={},paired_margins={},
                source_sha256={p:sha(ROOT/p) for p in SOURCES},root_weight='1',external_source_calls=0)
    try:
        audit(report)
    except Exception as e:
        report['error']=f'{type(e).__name__}: {e}'
    report['source_hashes_unchanged']=all(sha(ROOT/p)==h for p,h in report['source_sha256'].items())
    OUT.write_text(json.dumps(friendly(report),indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in (
        'root_state','all_children','selections_before_labels','selected_goal_evidence','source_sha256')},default=str))
