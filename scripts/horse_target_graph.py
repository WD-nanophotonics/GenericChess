"""Target-fixed directed Horse grammar; no compiled geometry or game engine."""
from collections import deque


def hops(source, width, height):
    x, y = source % width, source // width
    for vx, vy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        leg = (x+vx)+(y+vy)*width
        for side in (-1, 1):
            dx, dy = (2*vx, side) if vx else (side, 2*vy)
            xx, yy = x+dx, y+dy
            if 0 <= xx < width and 0 <= yy < height:
                yield xx+yy*width, leg


def reverse_distances(target, blocker, width, height, *, ignore_target_leg=False):
    area = width*height
    if target == blocker or not 0 <= target < area or not 0 <= blocker < area:
        raise ValueError('distinct in-board target/blocker required')
    reverse = [[] for _ in range(area)]
    for source in range(area):
        if source in (target, blocker): continue
        for dest, leg in hops(source, width, height):
            if dest == blocker or leg == blocker: continue
            if dest != target and not ignore_target_leg and leg == target: continue
            reverse[dest].append(source)
    distances = {target: 0}; queue = deque([target])
    while queue:
        here = queue.popleft()
        for source in reverse[here]:
            if source not in distances:
                distances[source] = distances[here]+1; queue.append(source)
    return {source: distances.get(source, 0) for source in range(area)
            if source not in (target, blocker)}


def second_mass(width, height, checkpoint=None):
    """Exact first/second contact counts by path-blocker set intersection."""
    area = width*height; constraints = {}; motifs = 0; direct_edges = 0
    for source in range(area):
        for middle, leg1 in hops(source, width, height):
            direct_edges += 1
            for target, leg2 in hops(middle, width, height):
                motifs += 1
                if checkpoint is not None: checkpoint()
                if source == target or leg1 == target: continue
                assert ((source % width+source//width)-(target % width+target//width)) % 2 == 0
                forbidden = {middle, leg1, leg2}-{source, target}
                pair = (source, target)
                constraints[pair] = forbidden if pair not in constraints else constraints[pair] & forbidden
    second = sum(area-2-len(forbidden) for forbidden in constraints.values())
    return dict(direct=direct_edges*(area-3), second=second,
                direct_edges=direct_edges, two_step_pairs=len(constraints), motifs=motifs,
                intersection_size_counts={size: sum(len(f)==size for f in constraints.values()) for size in range(4)})


def forward_oracle(source, target, blocker, width, height, checkpoint=None):
    """Separate source BFS implementation of the coordinate movement axioms."""
    queue = deque([(source, 0)]); seen = {source}
    offsets = ((-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1))
    while queue:
        here, distance = queue.popleft()
        if checkpoint is not None: checkpoint()
        x, y = here % width, here // width
        for dx, dy in offsets:
            xx, yy = x+dx, y+dy
            if not 0 <= xx < width or not 0 <= yy < height: continue
            lx = x+(1 if dx > 0 else -1) if abs(dx) == 2 else x
            ly = y+(1 if dy > 0 else -1) if abs(dy) == 2 else y
            leg = lx+width*ly; dest = xx+width*yy
            if leg in (target, blocker) or dest == blocker: continue
            if dest == target: return distance+1
            if dest not in seen:
                seen.add(dest); queue.append((dest, distance+1))
    return 0
