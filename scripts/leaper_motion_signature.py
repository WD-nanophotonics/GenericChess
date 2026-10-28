"""Metadata-only conservative motion-family exposure signature, not game truth.

Quotients actor renaming and simultaneous D4 transforms; ignores board/clock/
quantity so equal signatures are conservatively treated as exposure. Inequality
against a partial registry never establishes globally unseen/holdout status.
"""
import hashlib

def motion_family_signature(rule):
 pieces=[]
 for piece in rule['piece_types']:
  if any(a['kind']!='leap' for a in piece['movement_atoms']):raise ValueError('non-Leap metadata is outside this registry projection')
  pieces.append((bool(piece['is_anchor']),[a['offset'] for a in piece['movement_atoms']]))
 candidates=[]
 for swap in (False,True):
  for sx in (-1,1):
   for sy in (-1,1):
    transformed=[(anchor,tuple(sorted(set((sx*(y if swap else x),sy*(x if swap else y)) for x,y in offsets)))) for anchor,offsets in pieces]
    candidates.append(tuple(sorted(transformed)))
 return hashlib.sha256(repr(min(candidates)).encode()).hexdigest()
