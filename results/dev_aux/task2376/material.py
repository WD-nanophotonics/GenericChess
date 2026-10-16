"""Type-linear material features for full Position board-current and hand-base IDs.

Opt-in research callback only. Rule execution, auxiliary state and terminals stay
with Core; equal material features do not imply equivalent legal states/value.
No learned values, context model, activation or current pilot change.
"""
from collections import Counter
from math import isfinite

def features(position,target,*,excluded_type_ids=frozenset()):
 if target not in(0,1):raise ValueError('two-player target required')
 counts=Counter()
 for piece in position.board:
  if piece is not None and piece.current_type_id not in excluded_type_ids:counts[piece.current_type_id]+=1 if piece.owner==target else-1
 for owner,hand in enumerate(position.hands):
  for base_type,count in hand.counts:
   if base_type not in excluded_type_ids:counts[base_type]+=(1 if owner==target else-1)*count
 return dict(sorted((type_id,count)for type_id,count in counts.items()if count))

def material(position,target,prices,*,excluded_type_ids=frozenset()):
 coefficients=features(position,target,excluded_type_ids=excluded_type_ids);table={key:float(value)for key,value in prices.items()}
 if any(not isfinite(value)for value in table.values()):raise ValueError('material prices must be finite')
 missing=set(coefficients)-set(table)
 if missing:raise ValueError('missing active material price: '+','.join(sorted(missing)))
 value=sum(table[type_id]*count for type_id,count in coefficients.items())
 if not isfinite(value):raise ValueError('material score must be finite')
 return float(value)
