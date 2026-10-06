"""Native-only capture hints from admitted IR effects; never action legality."""
from scripts.native_chess_contact_intervals import FINGERPRINT


class ChessCaptureEffectHint:
    def __init__(self, fingerprint, patterns):
        if fingerprint != FINGERPRINT: raise ValueError('exact native Chess profile required')
        self.bits = {}
        allowed = {'move','remove','set_token','clear_token','set_flag','promote'}
        for pattern in patterns:
            if pattern.pattern_id in self.bits: raise ValueError('duplicate pattern identity')
            bit = False
            for effect in pattern.effects:
                if effect.kind not in allowed: raise ValueError('unqualified effect vocabulary')
                if effect.kind == 'remove':
                    if effect.piece_owner != 'opponent' or effect.disposition != 'remove_from_game':
                        raise ValueError('unqualified removal ownership/disposition')
                    bit = True
            self.bits[pattern.pattern_id] = bit

    def legal_pattern_captures(self, pattern_id):
        """Caller supplies a native legal pattern; this does not validate it."""
        if pattern_id not in self.bits: raise ValueError('unknown native pattern')
        return self.bits[pattern_id]
