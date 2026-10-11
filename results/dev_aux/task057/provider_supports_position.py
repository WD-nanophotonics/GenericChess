def supports_position(self, position, ply_count):
    """Native's state-local cutoff cannot implement Core continuation."""
    return ply_count < self.compiled.support.max_ply - int(self._requires_reply_probe)
