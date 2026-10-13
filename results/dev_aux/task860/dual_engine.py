import os,json
import adapter as A
from warm_adapter import ControlledEngine
class DualEngine(ControlledEngine):
 def __init__(self,ordering,leaf,journal=None,policy='warm_game'):
  old=os.environ.get('DEV_AUX_EVAL_VALUES');os.environ['DEV_AUX_EVAL_VALUES']=' '.join(map(str,leaf[1:15]))
  try:super().__init__(ordering,None,policy)
  finally:
   if old is None:os.environ.pop('DEV_AUX_EVAL_VALUES',None)
   else:os.environ['DEV_AUX_EVAL_VALUES']=old
  self.leaf_weights=list(leaf);self.rawjournal=journal
 def search(self,initial,history,nodes=256):
  self.position(initial,history);self.send('auxleaf');line=self.until(lambda l:l.startswith('info string auxleaf '))[-1];b=A.replay(initial,history);a=line.split(' ',4);v=int(a[3]);expected=A.material(b,self.leaf_weights)*(1 if b.turn==0 else -1);assert v==expected and a[4].split()[:3]==b.sfen().split()[:3],(line,expected);q=super().search(initial,history,nodes);q.update(leaf_weights=self.leaf_weights,leaf_state=line,price_scope='weights=nativecached/SEE/otherpriceconsumers;leaf_weights=actualcompute_eval');A.validate_search(q)
  if self.rawjournal:self.rawjournal.write(json.dumps(q)+'\n');self.rawjournal.flush()
  return q
