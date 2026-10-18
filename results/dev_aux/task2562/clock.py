"""Prospective cost-clock control; no evaluator, ordering or target changes."""
from math import isfinite
REFERENCE_NODES=3200000
REFERENCE_OBSERVATIONS=27795

def rate(base_eta,paid_nodes,last_observation,method):
 if method not in ('Mean','CostClock') or not 0<=last_observation<paid_nodes or not isfinite(base_eta) or base_eta<=0:raise ValueError('clock domain')
 interval=paid_nodes-last_observation
 eta=base_eta if method=='Mean' else base_eta*interval*REFERENCE_OBSERVATIONS/REFERENCE_NODES
 return dict(interval_nodes=interval,last_observation_nodes=last_observation,paid_nodes=paid_nodes,eta=eta)
