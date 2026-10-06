"""Arrival-coordinate derivation, independent of compiled horse patterns."""


def incoming_sources(target, width=9, height=10):
    if type(width) is not int or type(height) is not int or min(width, height) < 3:
        raise ValueError('integer board dimensions at least3 required')
    if type(target) is not int or not 0 <= target < width*height:
        raise ValueError('in-board integer target required')
    x, y = target % width, target//width
    rows = []
    for a in (-1, 1):
        for b in (-1, 1):
            leg = (x+a)+width*(y+b)
            for sx, sy in ((x+2*a, y+b), (x+a, y+2*b)):
                if 0 <= sx < width and 0 <= sy < height:
                    rows.append((sx+width*sy, leg))
    return rows


def blockers_eliminating_all_entries(target, width=9, height=10):
    rows = incoming_sources(target, width, height)
    if not rows:
        raise ValueError('no incoming edge; require separate board-domain proof')
    blockers = {rows[0][0], rows[0][1]}
    for source, leg in rows[1:]:
        blockers &= {source, leg}
    return sorted(blockers-{target})
