def is_square_attacked(self, position: Position, square: int, by_owner: int, checkpoint: Checkpoint | None=None) -> bool:
    """Semantic pseudo-attack (R2-09/R2-10): exact type/geometry
    compatibility, path predicates, state guards and slot guards with
    attacker-relative SELF/OPPONENT.  No full legal recursion and no S3
    own-anchor safety, matching the legacy attacked-square distinction.

    B-3: S4-bearing capture patterns still contribute their S0/S1
    capture eligibility to pseudo-attack; S4 postconditions are never
    consulted here."""
    self._ensure_match(position)
    incoming = self.semantic._incoming_attack_paths
    if incoming is not None:
        _checkpoint(checkpoint)
        key = (str(by_owner), square)
        source_groups = self.semantic._incoming_attack_sources
        rows = incoming.get(key, ())
        if source_groups is not None:
            groups = []
            for source, typed in source_groups.get(key, {}).items():
                _checkpoint(checkpoint)
                piece = position.board[source]
                if piece is not None and piece.owner == by_owner:
                    groups.append(typed.get(piece.current_type_id, ()))
            rows = (row for rank, row in heapq.merge(*groups))
        for pattern, tid, source, gid, path in rows:
            _checkpoint(checkpoint)
            piece = position.board[source]
            if piece is None or piece.owner != by_owner or piece.current_type_id != tid:
                continue
            binding = self._make_binding(pattern, gid, tid, piece, source, square, None, path, position)
            if self._path_holds(pattern.path, position, binding, by_owner, checkpoint=checkpoint) and self._guards_hold(pattern, position, binding, by_owner, checkpoint=checkpoint):
                return True
        return False
    sources_by_owner_type = _sources_by_owner_type(position)
    owner_key = str(by_owner)
    for pattern in self._patterns:
        _checkpoint(checkpoint)
        if pattern.target.kind != 'target_enemy':
            continue
        for tid in pattern.type_ids:
            _checkpoint(checkpoint)
            for source, piece in sources_by_owner_type.get((by_owner, tid), ()):
                _checkpoint(checkpoint)
                for gid in pattern.geometry_ids:
                    _checkpoint(checkpoint)
                    geometry = self.ir.geometry.get(gid)
                    if geometry is None or geometry.kind == 'drop':
                        continue
                    if geometry.atom_source is not None and geometry.atom_source[0] != tid:
                        continue
                    for path in geometry_paths_to(geometry, owner_key, source, square):
                        _checkpoint(checkpoint)
                        binding = self._make_binding(pattern, gid, tid, piece, source, square, None, path, position)
                        if self._path_holds(pattern.path, position, binding, by_owner, checkpoint=checkpoint) and self._guards_hold(pattern, position, binding, by_owner, checkpoint=checkpoint):
                            return True
    return False
