from scripts.generic_royal_actor import RoyalActor
class NPlusActor(RoyalActor):
 def hit(self,state,a,b):
  if state[a].upper()=='N' and abs(b%self.width-a%self.width)+abs(b//self.width-a//self.width)==1:return True
  return super().hit(state,a,b)
