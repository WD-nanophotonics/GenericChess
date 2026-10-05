"""Compiled alive-result gate, scoped to ordinary inherited-mask profile grammar."""
from generic_chess.core.coordinates import index_to_square
from scripts.promotable_contact_cubes import PromotableContactCubes,ContactUnsupported

class PhysicalPromotionContactCubes(PromotableContactCubes):
    def __init__(self,compiled,profiles,**kwargs):
        super().__init__(compiled,profiles,**kwargs)
        self.stats['filtered_quiet_promotion_variants']=0;self.stats['filtered_forced_capture_targets']=0
        for profile in self.closure:
            if profile.promoted:continue
            metadata=compiled.support.type_metadata[profile.base]
            if not metadata.is_promotable:continue
            allowed=compiled.support.promotion_allowed.get(profile.base,())
            forced=compiled.support.promotion_forced.get(profile.base,())
            if len(allowed)!=2 or len(forced)!=2:raise ContactUnsupported('complete owner promotion masks required')
            def alive(current,destination):
                mask=compiled.support.empty_mobility.get(current,())
                if len(mask)!=2 or any(len(x)!=self.area for x in mask):raise ContactUnsupported('compiled alive-result support missing')
                return bool(mask[self.owner][destination])
            for source in range(self.area):
                self.check();quiet=self.quiet[profile,source]
                for destination,result in list(quiet):
                    if result!=profile and not alive(result.current,destination):
                        del quiet[destination,result];self.stats['filtered_quiet_promotion_variants']+=1
                capture=self.capture[profile,source]
                for destination in list(capture):
                    pair=(index_to_square(source,self.shape),index_to_square(destination,self.shape))
                    if pair in allowed[self.owner] and pair[1] in forced[self.owner] and not any(alive(t,destination) for t in metadata.promotion_target_ids):
                        del capture[destination];self.stats['filtered_forced_capture_targets']+=1
