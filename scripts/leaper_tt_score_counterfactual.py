"""Explicit diagnostic counterfactual: suppress TT score eligibility only.
Stored entries and hash moves remain; this is NOT an observer or optimization.
"""
from generic_chess.ai.alphabeta.transposition import TranspositionTable,TTEntry


class NoTTScoreReuse:
    def __init__(self):self.probes=0;self.masked_hits=0
    def __enter__(self):
        self.original=TranspositionTable.probe
        def probe(table,key):
            value=self.original(table,key);self.probes+=1
            if value is None:return None
            self.masked_hits+=1
            return TTEntry(value.key,-1,value.score,value.bound,value.best_action,value.generation)
        TranspositionTable.probe=probe
        return self
    def __exit__(self,*exc):TranspositionTable.probe=self.original
