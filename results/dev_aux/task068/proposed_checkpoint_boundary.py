class Fixed(C):
 def _set_checkpoint_values(self,checkpoint):
  super()._set_checkpoint_values(checkpoint);self._compact_values=copy.deepcopy(self._compact_values)
 def _set_ordering_checkpoint_values(self,checkpoint):
  super()._set_ordering_checkpoint_values(checkpoint);self._ordering_compact_values=copy.deepcopy(self._ordering_compact_values)
 def bind_checkpoint(self,checkpoint):
  checkpoint.validate_ruleset(self._compiled)
  if checkpoint.checkpoint_id==self._checkpoint_id:return
  staged=object.__new__(type(self));staged.__dict__=self.__dict__.copy();staged._set_checkpoint_values(checkpoint);staged._capsule=staged._new_capsule();self.__dict__.update(staged.__dict__)
