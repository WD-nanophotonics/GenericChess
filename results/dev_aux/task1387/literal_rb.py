import chess
inside=lambda s:0<=s<64
def reachable(d, s, t):
    p, c = d[s]
    x, y = (s % 8, s // 8)
    u, v = (t % 8, t // 8)
    dx, dy = (u - x, v - y)
    if p == 6:
        return max(abs(dx), abs(dy)) == 1
    if p == 2:
        return sorted([abs(dx), abs(dy)]) == [1, 2]
    if p == 3:
        if abs(dx) != abs(dy) or dx == 0:
            return False
    else:
        assert p == 4
    if p == 4 and (dx and dy or not (dx or dy)):
        return False
    sx = (dx > 0) - (dx < 0)
    sy = (dy > 0) - (dy < 0)
    x += sx
    y += sy
    while (x, y) != (u, v):
        if x + 8 * y in d:
            return False
        x += sx
        y += sy
    return True

def attacked(d, s, side):
    return any((c == side and reachable(d, t, s) for t, (p, c) in d.items()))

def literal(b):
    d = {s: (p.piece_type, p.color) for s, p in b.piece_map().items()}
    assert all((inside(s) and p in [2, 3, 4, 6] for s, (p, c) in d.items()))
    side = b.turn
    result = []
    for s, (p, c) in d.items():
        if c != side:
            continue
        for rank in range(8):
            for file in range(8):
                t = rank * 8 + file
                if t in d and (d[t][1] == side or d[t][0] == 6):
                    continue
                if not reachable(d, s, t):
                    continue
                q = dict(d)
                del q[s]
                q[t] = (p, c)
                king = next((sq for sq, (pt, col) in q.items() if pt == 6 and col == side))
                if not attacked(q, king, not side):
                    result.append(chess.square_name(s) + chess.square_name(t))
    return sorted(result)