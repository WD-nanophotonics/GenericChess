"""Fresh scoped contact-family development use; no complete material prior."""
from dataclasses import asdict,replace
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import shutil
import sys
from time import monotonic

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generic_chess.core.actions import action_source_square,action_target_square
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.chess_certificate_request import chess_certificate_request
from scripts.conditional_dtm_bridge import dtm_horizon_interval,PREMISES
from scripts.material_leaf_choice import inventory_features,material_score,one_ply_choice
from scripts.contact_rb_choice import rb_contact_choice
from scripts.partial_decision_loss import paired_margin
from scripts.public_goal_intervals import PublicGame

PROTOCOL='docs/research/CHESS_CONTACT_SCOPED_USE_PROTOCOL.md'
MANIFEST_SHA='1a2e45d5eb54ff451a0b7cfb8dad5e31f208d63c0654b6f8eac9581d39886a72'
OUT=ROOT/'docs/research/data/chess_contact_scoped_use_20261005.json'
FREEZE=OUT.with_suffix('.selections.json')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def audit(report):
    start=monotonic()
    def check():
        if monotonic()-start>=15:
            raise TimeoutError('15-second total audit cap')
    source=ROOT/'.local_agent/certificate_source'
    manifest_path=source/'manifest-source-correction.json'
    if sha(manifest_path)!=MANIFEST_SHA:
        raise ValueError('source manifest drift')
    manifest=json.loads(manifest_path.read_text())
    files=[(source/'tables'/m['name'],m) for m in manifest['tables']]
    files += [(source/'python-chess'/m['name'],m) for m in manifest['source_files']]
    for p,m in files:
        if p.stat().st_size!=m['bytes'] or sha(p)!=m['sha256']:
            raise ValueError('source integrity failure')
    working=source/'contact-use-working-tables'
    if working.exists():
        raise FileExistsError('fresh working tables required; no rerun')
    working.mkdir()
    for p,m in files[:2]:
        shutil.copyfile(p,working/p.name)
    sys.path.insert(0,str(source/'python-chess'))
    import chess
    import chess.gaviota
    if chess.__version__!='1.11.2' or Path(chess.__file__).resolve()!=(source/'python-chess/chess/__init__.py').resolve():
        raise ValueError('isolated pinned parser required')
    def fen_key(fen):
        return ' '.join(fen.split()[:4])
    excluded=set()
    def collect(value):
        if isinstance(value,dict):
            for k,v in value.items():
                if k=='fen' and isinstance(v,str):
                    board=chess.Board(v)
                    for b in (board,board.mirror(),board.transform(chess.flip_horizontal),
                              board.mirror().transform(chess.flip_horizontal)):
                        excluded.add(fen_key(b.fen()))
                else:
                    collect(v)
        elif isinstance(value,list):
            for v in value:
                collect(v)
    for name in ('small_certificate_first_probe_20261004','small_selector_diagnostic_20261004'):
        collect(json.loads((ROOT/f'docs/research/data/{name}.json').read_text()))
    report['excluded_current_fens']=sorted(excluded)
    compiled=compile_ruleset_for_execution(build_western_chess_ruleset())
    game=PublicGame(compiled)
    def root(k,e,r,b,owner):
        board=[None]*64
        for sq,side,tid in ((k,owner,'K'),(e,1-owner,'K'),(r,1-owner,'R'),(b,1-owner,'B')):
            board[sq]=Piece(side,tid,tid)
        position=replace(initial_state(compiled).position,board=tuple(board),side_to_move=owner,
            aux_state=(((0,-1),0),((1,-1),0),((2,-1),None),((3,-1),0),((4,-1),0)))
        return synthetic_state(compiled,position)
    def actions(state):
        choices={}
        for a in game.actions(state,check):
            check()
            if report['enumerated']>=5000 or len(choices)>=128:
                raise ValueError('5000 enumeration/128 complete choices cap')
            report['enumerated']+=1;key=str(a)
            if key in choices:
                raise ValueError('lossless key collision')
            choices[key]=a
        return choices
    def destination(a):
        q=action_target_square(a)
        return None if q is None else q.rank*8+q.file
    accepted=[]
    offsets=sorted((x,y) for x in (-1,0,1) for y in (-1,0,1) if x or y)
    for k in [8*y+x for y in range(2,6) for x in range(2,6)]:
        if len(accepted)==2:
            break
        for e in (0,7,56,63):
            if len(accepted)==2:
                break
            for ro in offsets:
                if len(accepted)==2:
                    break
                for bo in offsets:
                    if ro==bo:
                        continue
                    check()
                    if report['proposals']>=128:
                        raise ValueError('128 proposals total; incomplete generation')
                    report['proposals']+=1
                    r=8*(k//8+ro[1])+k%8+ro[0]
                    b=8*(k//8+bo[1])+k%8+bo[0]
                    if len({k,e,r,b})!=4 or max(abs(k%8-e%8),abs(k//8-e//8))<=1:
                        continue
                    state=root(k,e,r,b,0)
                    try:
                        packet=chess_certificate_request(state,compiled)
                    except ValueError as error:
                        if any(t in str(error) for t in ('previous mover','terminal-first')):
                            continue
                        raise
                    if fen_key(packet['fen']) in excluded:
                        continue
                    table=actions(state)
                    if not {r,b}<={destination(a) for a in table.values()}:
                        continue
                    reflected=root(56-8*(k//8)+k%8,56-8*(e//8)+e%8,
                                   56-8*(r//8)+r%8,56-8*(b//8)+b%8,1)
                    mirror_packet=chess_certificate_request(reflected,compiled)
                    if fen_key(mirror_packet['fen']) in excluded:
                        continue
                    accepted.append((state,packet,table,reflected,mirror_packet))
                    if len(accepted)==2:
                        break
    if len(accepted)!=2:
        raise ValueError('incomplete fixed four-root population')
    plans=[]
    for state,packet,table,mirror,mirror_packet in accepted:
        for root_state,request,choices in ((state,packet,table),(mirror,mirror_packet,actions(mirror))):
            children={}
            for key,a in choices.items():
                check()
                if report['public_transitions']>=128:
                    raise ValueError('128 total public transitions cap')
                report['public_transitions']+=1
                children[key]=game.successor(root_state,a)
            owner=root_state.position.side_to_move
            selections={'contact_family':rb_contact_choice(children,game,owner=owner,complete=True)}
            for name,weights in (('unit',{('board','R'):F(1),('board','B'):F(1)}),
                                 ('zero',{('board','R'):F(0),('board','B'):F(0)})):
                selections[name]=one_ply_choice(children,game,
                    lambda c:material_score(c.position,weights,{'K'},30),owner=owner,complete=True)
            if any(not v['complete'] for v in selections.values()):
                raise ValueError('unqualified family/terminal selection')
            row=dict(owner=owner,weight='1/4',root_request=request,complete_choice_count=len(children),
                     selections_before_labels=selections,all_children={},selected_goal_evidence={},paired_margins={})
            for key,c in children.items():
                row['all_children'][key]=dict(state=asdict(c),
                    features={str(t):n for t,n in inventory_features(c.position,{'K'}).items()})
            report['rows'].append(row);plans.append((children,row))
    frozen=json.dumps(report['rows'],sort_keys=True,default=str,indent=2)+'\n'
    FREEZE.write_text(frozen,encoding='utf-8',newline='\n')
    report['prelabel_freeze_sha256']=sha(FREEZE)
    report['all_selections_frozen_before_probes']=True
    cached={}
    with chess.gaviota.PythonTablebase() as tablebase:
        tablebase.add_directory(str(working))
        for children,row in plans:
            intervals={k:(-1,1) for k in children}
            for key in sorted({s['selected'] for s in row['selections_before_labels'].values()}):
                check();child=children[key];terminal=game.terminal(child)
                if terminal.is_terminal:
                    value=0 if terminal.winner is None else 1 if terminal.winner==0 else -1
                    intervals[key]=(value,value)
                    row['selected_goal_evidence'][key]=dict(interval=intervals[key],local_terminal=terminal.status.value)
                    continue
                packet=chess_certificate_request(child,compiled)
                evidence=dict(request=packet,interval=(-1,1))
                row['selected_goal_evidence'][key]=evidence
                if sum(p is not None for p in child.position.board)>3:
                    evidence['reason']='four-piece source unavailable; retained unknown'
                    continue
                fen=packet['fen']
                if fen not in cached:
                    external=chess.Board(fen)
                    if not external.is_valid():
                        raise ValueError('invalid selected converted child')
                    local=set()
                    for a in actions(child).values():
                        s=action_source_square(a);d=action_target_square(a)
                        if s is None or d is None:
                            raise ValueError('unsupported projected action')
                        local.add(f'{chr(97+s.file)}{s.rank+1}{chr(97+d.file)}{d.rank+1}')
                    if local!={m.uci() for m in external.legal_moves}:
                        raise ValueError('selected child complete legal-set mismatch')
                    if report['outer_probe_calls']+2>20:
                        evidence['reason']='20 outer source calls cap; unknown'
                        continue
                    report['outer_probe_calls']+=1;dtm=tablebase.probe_dtm(external);check()
                    report['outer_probe_calls']+=1;wdl=tablebase.probe_wdl(external);check()
                    cached[fen]=(dtm,wdl,len(local))
                dtm,wdl,legal_count=cached[fen]
                bridge=dtm_horizon_interval(side=child.position.side_to_move,ply=child.ply_count,
                    max_ply=1000,repetition_limit=100000,
                    max_repetition_count=max(n for _,n in child.repetition_counts),
                    signed_dtm=dtm,wdl_stm=wdl,premises={p:True for p in PREMISES})
                intervals[key]=bridge['interval']
                evidence.update(interval=intervals[key],signed_dtm=dtm,wdl_stm=wdl,
                                complete_projected_legal_count=legal_count,conditional_bridge=bridge)
            selections=row['selections_before_labels']
            for name in ('unit','zero'):
                row['paired_margins'][name]=paired_margin(intervals,selections['contact_family']['selected'],
                                                         selections[name]['selected'],row['owner'])
    report['mean_paired_margins']={name:[str(sum(F(row['paired_margins'][name][i]) for row in report['rows'])/4)
                                for i in (0,1)] for name in ('unit','zero')}
    report['source_manifest_sha256']=MANIFEST_SHA
    report['external_sources_unchanged']=all(sha(p)==m['sha256'] for p,m in files)
    report['working_tables_unchanged']=all(sha(working/p.name)==m['sha256'] for p,m in files[:2])
    if not report['external_sources_unchanged'] or not report['working_tables_unchanged']:
        raise ValueError('source integrity changed')
    report['complete']=True;report['seconds']=monotonic()-start


if __name__=='__main__':
    if OUT.exists() or FREEZE.exists() or not OUT.parent.is_dir():
        raise ValueError('fresh output/prelabel checkpoint required; no completed rerun')
    pins=[PROTOCOL,'docs/research/SMALL_SOURCE_USE_GENERATOR.md',
          'docs/research/CHESS_CONTACT_COMMON_LAW_DESIGN.md','docs/research/CHESS_CONTACT_COMMON_LAW_RESULTS.md',
          'scripts/audit_chess_contact_scoped_use.py','scripts/contact_rb_choice.py',
          'scripts/chess_certificate_request.py','scripts/conditional_dtm_bridge.py',
          'scripts/material_leaf_choice.py','scripts/partial_decision_loss.py','scripts/public_goal_intervals.py',
          'scripts/audit_exchange_custody.py','generic_chess/core/semantic_executor.py',
          'generic_chess/rules/western_chess.py','docs/research/data/small_certificate_first_probe_20261004.json',
          'docs/research/data/small_selector_diagnostic_20261004.json']
    report=dict(complete=False,proposals=0,public_transitions=0,enumerated=0,outer_probe_calls=0,rows=[],
                source_sha256={p:sha(ROOT/p) for p in pins},scope='fresh positions; exposed R/B outcome class; development only')
    try:
        audit(report)
    except Exception as error:
        report['error']=f'{type(error).__name__}: {error}'
    report['source_hashes_unchanged']=all(sha(ROOT/p)==h for p,h in report['source_sha256'].items())
    OUT.write_text(json.dumps(report,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','rows','excluded_current_fens')}))
