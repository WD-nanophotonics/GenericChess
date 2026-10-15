"""Leaf prices vary; Native and capture price tables stay UNIT720 by frozen variant definitions. Scope remains exact4x4KRN. This is an ablation, not product change."""
from scripts.generic_session_native_material import SessionKRNMaterialProvider
class LeafOnlyUnitProvider(SessionKRNMaterialProvider):
 def profile(self,values):
  values=tuple(values);r,n,b,p=values
  name=self.plan['variant_names'][str(values)];self.e.send('setoption name UCI_Variant value '+name);raw=self.e.ready()
  assert any(x.startswith(f'info string variant {name} files 4 ranks 4 ') for x in raw)
  self.e.send('devauxleafrnbp '+' '.join(map(str,values)));ack=self.e.ready()
  expected=f'info string DEV_AUX leafRNBP {r} {n} {b} {p} nativeP {p} nativeR 720 nativeN {n} nativeB {b} captureP {p} captureR 720 captureN {n} captureB {b}'
  assert expected in ack;self.log('PROFILE',values=values,raw=raw,ack=ack);self.current=values
  self.e.send('ucinewgame');self.log('CLEAR',values=values,raw=self.e.ready())
