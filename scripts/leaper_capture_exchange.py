"""Research-only geometric exchange ranking with royal-last terminal branch;never a legal/WDL bound."""
from generic_chess.core.actions import action_is_board,action_source_square,action_target_square,action_promotion_target_id
from generic_chess.core.coordinates import square_to_index
from generic_chess.core.movement import LeapAtom


def certify_plain_geometry(compiled):
    # Reuse existing compiled leap tables;no new attack table/cache/identity.
    assert all(isinstance(a,LeapAtom) for t in compiled.types_by_id.values() for a in t.movement_atoms)


def material_exchange(victim,mover,own,enemy,royals=(False,False)):
    """Greedy optional-stop swap model over static nonroyal attacker lists."""
    groups=[sorted(own),sorted(enemy)];indices=[0,0];side=1;occupant=mover;gains=[victim]
    while True:
        if indices[side]>=len(groups[side]):
            # A royal is not a zero-price exchange victim. It may end this
            # static sequence only when the target has no opposing defenders.
            if (royals[side] and indices[1-side]>=len(groups[1-side])
                    and not royals[1-side]):
                gains.append(occupant-gains[-1])
            break
        attacker=groups[side][indices[side]];indices[side]+=1
        gains.append(occupant-gains[-1]);occupant=attacker;side=1-side
    for i in range(len(gains)-1,0,-1):gains[i-1]=-max(-gains[i-1],gains[i])
    return gains[0]


def eligible_capture(state,action,compiled):
    if not action_is_board(action) or action_promotion_target_id(action) is not None:return False
    n=compiled.board_size;board=state.position.board
    mover=board[square_to_index(action_source_square(action),n)];victim=board[square_to_index(action_target_square(action),n)]
    return mover is not None and victim is not None and mover.owner!=victim.owner and not compiled.types_by_id[mover.current_type_id].is_anchor and not compiled.types_by_id[victim.current_type_id].is_anchor


def exchange_inputs(state,action,compiled,evaluator):
    n=compiled.board_size;board=state.position.board;origin=square_to_index(action_source_square(action),n);target_square=action_target_square(action);target=square_to_index(target_square,n)
    mover,victim=board[origin],board[target];groups=[[],[]];royals=[0,0]
    for index,piece in enumerate(board):
        if piece is None or index in (origin,target):continue
        if not any(target_square in atom for atom in compiled.leap_targets[piece.current_type_id][piece.owner][index]):continue
        side=int(piece.owner!=mover.owner)
        if compiled.types_by_id[piece.current_type_id].is_anchor:royals[side]+=1
        else:groups[side].append(evaluator.type_value(piece.current_type_id))
    return evaluator.type_value(victim.current_type_id),evaluator.type_value(mover.current_type_id),groups[0],groups[1],royals


def geometric_score(state,action,compiled,evaluator):
    victim,mover,own,enemy,royals=exchange_inputs(state,action,compiled,evaluator)
    return material_exchange(victim,mover,own,enemy,tuple(bool(x) for x in royals))


def reorder_capture_slots(state,actions,compiled,evaluator,orderer,tuning):
    base=orderer.order(state,actions,evaluator,3,None,None,tuning)
    slots=[i for i,a in enumerate(base) if eligible_capture(state,a,compiled)]
    # Preserve all quiet/royal/noncapture slots,alltypedactions and stableties.
    replacement=sorted((base[i] for i in slots),key=lambda a:geometric_score(state,a,compiled,evaluator),reverse=True)
    result=list(base)
    for i,a in zip(slots,replacement):result[i]=a
    return result
