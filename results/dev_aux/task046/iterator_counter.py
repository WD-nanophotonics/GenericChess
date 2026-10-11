"""Count real stdlib merge input iterator calls; no semantic imports."""
import heapq
class Counted:
 def __init__(self,values,counts,group):self.it=iter(values);self.counts=counts;self.group=group
 def __iter__(self):return self
 def __next__(self):
  self.counts['attempts']+=1
  try:row=next(self.it)
  except StopIteration:
   self.counts['eof_attempts']+=1;raise
  self.counts['reads']+=1;self.counts['pulled_ranks'].append((self.group,row[0]));return row
class CountingHeap:
 def __init__(self):self.reset()
 def reset(self):
  self.last=dict(group_lengths=[],attempts=0,reads=0,eof_attempts=0,pulled_ranks=[])
 def merge(self,*groups):
  self.reset();self.last['group_lengths']=[len(g) for g in groups]
  return heapq.merge(*(Counted(g,self.last,i) for i,g in enumerate(groups)))
