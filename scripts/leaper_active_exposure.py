"""Conservative active-type exposure projection, NOT a reachability solver.

Only complete legacy remove-only/no-drop/no-promotion schemas are filtered.
Unknown effects/custom IR and malformed records retain the ALL-declared signature
or a coverage gap. This is an endpoint exposure consumer, not evaluator/profile
normalization and not a canonical RuleSet/TT identity.
"""
import copy,gzip,hashlib,json,time
from collections import Counter
from pathlib import Path
from scripts.leaper_empty_geometry_signature import empty_geometry_signature
from scripts.leaper_motion_signature import motion_family_signature
from scripts.research_record import write_record

def any_truth(v):
    if isinstance(v,dict):return any(any_truth(x) for x in v.values())
    if isinstance(v,(tuple,list)):return any(any_truth(x) for x in v)
    return bool(v)

def active_projection(rule):
    pieces=rule.get('piece_types');board=rule.get('initial_position')
    if not isinstance(pieces,list) or not pieces or not isinstance(board,list):return None,'missing complete legacy board/types'
    known={'schema_version','board_size','board_width','board_height','piece_types','initial_position','initial_setup_options','promotion_allowed','promotion_forced','drop_allowed','capture_disposition','max_ply','repetition_limit','stalemate_result','metadata'}
    if set(rule)-known:return rule,'all-declared:unknown schema/effects'
    piece_keys={'type_id','name','movement_atoms','is_anchor','is_promotable','promotion_target_ids'}
    if any(set(p)-piece_keys for p in pieces):return rule,'all-declared:unknown actor schema'
    if rule.get('capture_disposition')!='remove_from_game' or rule.get('initial_setup_options'):return rule,'all-declared:capture/create/alternate setup unknown'
    if any_truth(rule.get('drop_allowed',{})) or any_truth(rule.get('promotion_allowed',{})) or any_truth(rule.get('promotion_forced',{})):return rule,'all-declared:creation enabled'
    if any(p.get('is_promotable') or p.get('promotion_target_ids') for p in pieces):return rule,'all-declared:promotion type closure unknown'
    initialized=set()
    for row in board:
        if not isinstance(row,list):return None,'nonliteral board row'
        for p in row:
            if p is None:continue
            if not isinstance(p,dict) or not isinstance(p.get('current_type_id'),str):return None,'unknown board piece'
            initialized.add(p['current_type_id'])
    types={p.get('type_id') for p in pieces}
    if not initialized or not initialized<=types:return None,'initial types missing or undeclared'
    out=copy.copy(rule);out['piece_types']=[p for p in pieces if p['type_id'] in initialized]
    return out,'remove-only initialized-type induction;no create/promotion/drop/alternate setup'

def inspect(paths,*,seconds=240,max_bytes=64*1024*1024):
    tick=time.perf_counter();out={'files':[],'rules':[],'gaps':[]};signatures=set();counts=Counter()
    def visit(v,where,depth=0):
        if depth>80:out['gaps'].append({'where':where,'reason':'depth cap'});return
        if isinstance(v,dict):
            if isinstance(v.get('piece_types'),list) and v.get('piece_types') and all(isinstance(p,dict) and 'movement_atoms' in p for p in v['piece_types']):
                projected,reason=active_projection(v);counts[reason]+=1
                if projected is not None:
                    try:
                        sig=empty_geometry_signature(projected);signatures.add(sig);out['rules'].append({'where':where,'signature':sig,'reason':reason,'active_types':[p.get('type_id') for p in projected['piece_types']]})
                    except (KeyError,ValueError,TypeError) as e:out['gaps'].append({'where':where,'reason':type(e).__name__+':'+str(e)[:120]})
            for k,x in v.items():
                if k=='text' and isinstance(x,str) and x.lstrip().startswith(('{','[')):
                    try:visit(json.loads(x),where+'/literal:'+str(v.get('path','text')),depth+1)
                    except (ValueError,RecursionError):out['gaps'].append({'where':where,'reason':'unparsed literal JSON'})
                else:visit(x,where+'/'+str(k),depth+1)
        elif isinstance(v,list):
            for i,x in enumerate(v):visit(x,where+'/'+str(i),depth+1)
    for index,p in enumerate(paths):
        if time.perf_counter()-tick>seconds:out['gaps'].append({'where':str(p),'reason':f'time cap;remaining{len(paths)-index}NOT_READ'});break
        p=Path(p)
        try:
            raw=p.read_bytes();out['files'].append({'path':p.as_posix(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
            if p.suffix=='.gz':
                with gzip.open(p,'rb') as stream:raw=stream.read(max_bytes+1)
            if len(raw)>max_bytes:raise ValueError('decoded size cap;lexical stream not active-board proof')
            visit(json.loads(raw),p.as_posix())
        except (ValueError,OSError,EOFError,RecursionError) as e:out['gaps'].append({'where':p.as_posix(),'reason':type(e).__name__+':'+str(e)[:120]})
    out.update(signatures=sorted(signatures),reasons=dict(counts),seconds=time.perf_counter()-tick,claim='partial finite-empty/active-type exposure only;not semantic equivalence/holdout;source/tests/private/escaped/IR/oversize gaps retained')
    return out
