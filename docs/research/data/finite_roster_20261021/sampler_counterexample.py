"""Exact source-consumer witness: category fallback is not a fixed-score policy.

No product change or generated-game claim. The consumer is run with a controlled
capture/check oracle, not a fabricated claim that an illegal move is Core-legal.
"""
from collections import Counter
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace
import json
import generic_chess.ai.benchmark.position_mining as mining
from generic_chess.core.actions import BoardMove,DropMove
from generic_chess.core.coordinates import Square

OUT=Path(__file__).resolve().parent
quiet=BoardMove(Square(0,0),Square(0,1))
drop=DropMove('P',Square(1,1))
illegal_capture=BoardMove(Square(0,0),Square(1,0))
session=SimpleNamespace(state=object());compiled=SimpleNamespace(board_size=4)
old_capture,old_check=mining._is_capture,mining._gives_check
mining._is_capture=lambda state,a,n:a==illegal_capture
mining._gives_check=lambda session,a,compiled:False

class Tape:
 def __init__(self,roll,index):self.roll=roll;self.index=index
 def random(self):return self.roll
 def choice(self,seq):return seq[self.index%len(seq)]

def distribution(actions):
 counts=Counter()
 for roll in range(20):
  for index in range(6):
   selected=mining._choose_action(session,actions,Tape((roll+.5)/20,index),compiled)
   counts['quiet' if selected==quiet else 'drop' if selected==drop else 'illegal_capture']+=1
 return counts

try:
 baseline=distribution([quiet,drop])
 proposed=distribution([quiet,drop,illegal_capture])
finally:mining._is_capture,mining._gives_check=old_capture,old_check
correct=Fraction(baseline['drop'],sum(baseline.values()))
after_rejection=Fraction(proposed['drop'],proposed['drop']+proposed['quiet'])
assert correct==Fraction(4,5) and after_rejection==Fraction(13,17)
assert correct!=after_rejection
result={'question':'Can the existing mining category policy be moved before legality and repaired by a blanket rejection?',
 'consumer':'generic_chess.ai.benchmark.position_mining._choose_action',
 'controlled_oracle':'One quiet legal action,one legal nonchecking drop,and one illegal pseudo capture; no promotions or checks; classification supplied by controlled oracles in a private process. This is an algorithm-level counterexample, not a Core legality defect or actual position claim.',
 'exact_enumeration':'20 equally weighted threshold bins x6 choice-index residues (LCM of sizes1,2,3),120 equiprobable tapes, one categorical choice each; repeat-until-legal probability is conditional accepted mass.',
 'full_legal_counts':dict(baseline),'pseudo_counts':dict(proposed),
 'correct_drop_probability':str(correct),'naive_reject_drop_probability':str(after_rejection),
 'decision':'Do not apply a blanket pre-legality rejection sampler to this consumer. Fixed-score softmax/uniform conditions from Ludii do not establish this category-with-empty-fallback policy equivalence. Preserve frozen opening RNG sequences and actual legal-action semantics; no new API, sampler or games.'}
(OUT/'sampler-counterexample.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
