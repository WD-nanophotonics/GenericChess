def _resolve_opaque_history_key(self, key: str, identity: RuntimePositionIdentity, runtime_hash: RuntimeHash) -> None:
    """Bind one opaque imported key to a verified exact child identity."""
    if key not in self._opaque_imported_keys:
        return
    old_identity = _ImportedIdentity(key)
    old_hash = self._runtime_hash_for_identity(old_identity)
    old_bucket, old_entry = self._find_occurrence(old_identity, old_hash, instrument=False)
    if old_entry is None:
        raise AssertionError('opaque imported occurrence is missing')
    old_index = old_bucket.index(old_entry)
    new_bucket = self._occurrences.get(runtime_hash)
    new_entry = next((candidate for candidate in new_bucket or () if _identity_equal(candidate.identity, identity)), None)
    if new_entry is None:
        prepared_entry = _Occurrence(identity, old_entry.count)
        if new_bucket is None:
            self._occurrences[runtime_hash] = [prepared_entry]
        else:
            new_bucket.append(prepared_entry)
    else:
        new_entry.count += old_entry.count
    frame = self._frames[-1]
    frame.bridge_key = key
    frame.bridge_identity = identity
    frame.bridge_runtime_hash = runtime_hash
    frame.bridge_old_hash = old_hash
    frame.bridge_old_count = old_entry.count
    del old_bucket[old_index]
    if not old_bucket:
        self._occurrences.pop(old_hash, None)
    self._opaque_imported_keys.remove(key)
    self._history_aliases[key] = identity
    self._snapshot = self._snapshot_from_occurrences()
