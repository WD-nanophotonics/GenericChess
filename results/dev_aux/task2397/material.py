"""Opt-in explicit board/hand valuation channels; Core remains rule authority."""
from math import isfinite
from collections import Counter

def channels(position,target,*,excluded_type_ids=frozenset()):
 if type(target)is not int or target not in(0,1):raise ValueError('two-player integer target required')
 board=Counter();hand=Counter()
 for pc in position.board:
  if pc is not None and pc.current_type_id not in excluded_type_ids:board[pc.current_type_id]+=1 if pc.owner==target else-1
 for owner,h in enumerate(position.hands):
  for base,n in h.counts:
   if base not in excluded_type_ids:hand[base]+=(1 if owner==target else-1)*n
 return {kind:dict(sorted((k,n)for k,n in c.items()if n))for kind,c in(('board',board),('hand',hand))}

def material(position,target,board_prices,hand_prices,*,excluded_type_ids=frozenset()):
 fs=channels(position,target,excluded_type_ids=excluded_type_ids);total=0.
 for kind,prices in(('board',board_prices),('hand',hand_prices)):
  table={k:float(v)for k,v in prices.items()}
  if any(not isfinite(v)for v in table.values()):raise ValueError('nonfinite '+kind+' price')
  missing=set(fs[kind])-set(table)
  if missing:raise ValueError('missing '+kind+' price:'+','.join(sorted(missing)))
  total+=sum(table[k]*n for k,n in fs[kind].items())
 if not isfinite(total):raise ValueError('nonfinite material score')
 return float(total)
