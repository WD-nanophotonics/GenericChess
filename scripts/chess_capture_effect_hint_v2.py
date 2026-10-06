"""Versioned native capture hints with executor-audited effect vocabulary."""
from scripts.native_chess_contact_intervals import FINGERPRINT


class ChessCaptureEffectHintV2:
    def __init__(self, fingerprint, patterns):
        if fingerprint != FINGERPRINT: raise ValueError('exact native profile required')
        self.bits = {}
        allowed = {'move','remove','set_current_type','set_bool','clear_right','set_token','clear_token'}
        for pattern in patterns:
            if pattern.pattern_id in self.bits: raise ValueError('duplicate pattern identity')
            captures = False
            for effect in pattern.effects:
                if effect.kind not in allowed: raise ValueError('unqualified effect vocabulary')
                if effect.kind == 'remove':
                    if effect.piece_owner != 'opponent' or effect.disposition != 'remove_from_game':
                        raise ValueError('unqualified removal ownership/disposition')
                    captures = True
            self.bits[pattern.pattern_id] = captures

    def legal_pattern_captures(self, pattern_id):
        if pattern_id not in self.bits: raise ValueError('unknown native pattern')
        return self.bits[pattern_id]
