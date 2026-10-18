"""Read-only probe: served-score perspective and terminal consistency (frozen data)."""
import json, collections
from pathlib import Path

D = Path(__file__).resolve().parent

games = {}
for line in (D / 'games.jsonl').open():
    g = json.loads(line)
    games[g['slot']] = g

last = {}
scores = collections.Counter()
for line in (D / 'queries.jsonl').open():
    q = json.loads(line)
    scores[round(q['score'], 6)] += 1
    key = (q['slot'], q['relative_ply'])
    prev = last.get(q['slot'])
    if prev is None or q['relative_ply'] >= prev['relative_ply']:
        last[q['slot']] = q

print('queries_scored', sum(scores.values()), 'distinct_scores', len(scores))
print('top_scores', scores.most_common(8))

# decisive games: last query is the move that ended the game.
agree = disagree = 0
examples = []
for slot, q in last.items():
    g = games[slot]
    if g['ending'] != 'ACTUAL_TERMINAL' or g['reward'] == 0:
        continue
    winner = g['result']['winner']
    # actor-perspective score must be the terminal band for the winner and
    # the negative band for the loser.
    expected = 1 if q['actor'] == winner else -1
    ok = (q['score'] * expected) > 0 and abs(q['score']) >= 1000000
    if ok:
        agree += 1
    else:
        disagree += 1
        if len(examples) < 5:
            examples.append((slot, winner, q['actor'], q['score'], g['reward']))
print('terminal_last_query_actor_perspective_agree', agree, 'disagree', disagree)
print('disagreements', examples)

# how many slots have a query at each ply, and depth actually completed
depths = collections.Counter(q['completed_depth'] for q in last.values())
print('last_query_depths', dict(depths), 'slots', len(last))
