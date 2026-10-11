"""Independent capped standard-Chess objective; no trained values in reward."""
import random, time
import chess

def quantity(board, color):
    return sum(len(board.pieces(t, color)) for t in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN))

def score(board, agent_color, plies, cap=64):
    if not 0 <= plies <= cap or cap <= 0:
        raise ValueError("invalid cap/ply")
    outcome = board.outcome(claim_draw=False)
    difference = quantity(board, agent_color) - quantity(board, not agent_color)
    reward = difference / 15
    kind = "cutoff"
    if outcome is not None:
        kind = outcome.termination.name
        if outcome.winner is None:
            reward = 0.0
        else:
            reward = (1 if outcome.winner == agent_color else -1) * (100 + (cap - plies) / cap)
    return dict(reward=reward, quantity_difference=difference, terminal=outcome is not None,
                termination=kind, winner=None if outcome is None else outcome.winner,
                proxy_result=None if outcome is not None else (1 if difference > 0 else -1 if difference < 0 else 0),
                played_plies=plies, cap=cap)

def opening(seed, plies=6):
    board = chess.Board()
    rng = random.Random(seed)
    moves = []
    for _ in range(plies):
        if board.is_game_over(claim_draw=False):
            break
        move = rng.choice(sorted(board.legal_moves, key=lambda m:m.uci()))
        board.push(move)
        moves.append(move.uci())
    if board.is_game_over(claim_draw=False):
        raise ValueError("opening terminal; freeze failure, do not resample")
    return moves

def play(search, agent_color, opening_moves, random_seed, cap=64, check_stop=lambda:None):
    """search receives full-history board.copy and returns (Move, metadata)."""
    board = chess.Board()
    for uci in opening_moves:
        move = chess.Move.from_uci(uci)
        if move not in board.legal_moves:
            raise ValueError("illegal opening")
        board.push(move)
    rng = random.Random(random_seed)
    moves, searches = [], []
    started = time.perf_counter()
    for ply in range(cap):
        check_stop()
        if board.is_game_over(claim_draw=False):
            break
        if board.turn == agent_color:
            move, metadata = search(board.copy(stack=True))
            searches.append(metadata)
        else:
            move = rng.choice(sorted(board.legal_moves, key=lambda m:m.uci()))
        if move not in board.legal_moves:
            raise ValueError("illegal player move")
        board.push(move)
        moves.append(move.uci())
    return dict(opening=list(opening_moves), random_seed=random_seed, agent_color=agent_color,
                actions=moves, search_records=searches, final_fen=board.fen(),
                score=score(board, agent_color, len(moves), cap), wall_seconds=time.perf_counter()-started)
