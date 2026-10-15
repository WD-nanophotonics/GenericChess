"""Explicit research-candidate identity; never changes board turn or history."""

def roles(plan):
    result=plan.get("candidate_roles",["TO_MOVE"])
    if not result or len(set(result))!=len(result) or any(x not in ("TO_MOVE","OTHER") for x in result):
        raise ValueError("invalid or duplicate candidate roles")
    return tuple(result)


def candidate_side(initial_turn,role):
    if type(initial_turn) is not int or initial_turn not in (0,1):
        raise ValueError("invalid initial player")
    if role not in ("TO_MOVE","OTHER"):
        raise ValueError("invalid candidate role")
    return initial_turn if role=="TO_MOVE" else 1-initial_turn


def row_role(row):return row.get("candidate_role","TO_MOVE")


def row_target(row,initial_turn):
    target=candidate_side(initial_turn,row_role(row))
    if "candidate_side" in row and row["candidate_side"]!=target:
        raise ValueError("candidate identity differs from frozen role")
    return target


def role_order(plan,family,color):
    result=roles(plan)
    return tuple(reversed(result)) if (family+color)%2 else result
