"""Native empty-hand board-pattern hints; drops stay explicitly unsupported."""
from scripts.native_chess_contact_intervals import FINGERPRINT


class ChessCaptureEffectHintV3:
    def __init__(self, fingerprint, patterns, geometry):
        if fingerprint != FINGERPRINT: raise ValueError('exact native profile required')
        self.bits = {}; self.excluded = []
        seen=set()
        allowed={'move','remove','set_current_type','set_bool','clear_right','set_token','clear_token'}
        for p in patterns:
            if p.pattern_id in seen: raise ValueError('duplicate pattern identity')
            seen.add(p.pattern_id)
            if not p.geometry_ids: raise ValueError('geometry required')
            kinds={geometry[g].kind for g in p.geometry_ids}
            if kinds == {'drop'}:
                self.excluded.append(p.pattern_id); continue
            if 'drop' in kinds: raise ValueError('mixed board/drop scope')
            capture=False
            for e in p.effects:
                if e.kind not in allowed: raise ValueError('unqualified effect vocabulary')
                if e.kind=='remove':
                    if e.piece_owner!='opponent' or e.disposition!='remove_from_game':
                        raise ValueError('unqualified removal ownership/disposition')
                    capture=True
            self.bits[p.pattern_id]=capture

    def legal_pattern_captures(self, pattern_id):
        if pattern_id not in self.bits: raise ValueError('unknown/excluded native board pattern')
        return self.bits[pattern_id]
