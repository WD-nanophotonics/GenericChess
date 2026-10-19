from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

SOURCE = Path("results/dev_aux/task2568/queries.jsonl")
OUTPUT = Path("results/dev_aux/task2602/task2593-baseline-exposure-v2.json")
WANTED = {"seed", "method", "observed", "complete", "pv_terminal"}


def skip_ws(text: str, i: int) -> int:
    while i < len(text) and text[i] in " \t\r\n":
        i += 1
    return i


def skip_value(text: str, i: int) -> int:
    i = skip_ws(text, i)
    if i >= len(text):
        raise ValueError("missing JSON value")
    if text[i] == '"':
        i += 1
        while i < len(text):
            if text[i] == "\\":
                i += 2
            elif text[i] == '"':
                return i + 1
            else:
                i += 1
        raise ValueError("unterminated string")
    if text[i] in "[{":
        stack = ["]" if text[i] == "[" else "}"]
        i += 1
        in_string = False
        while i < len(text) and stack:
            ch = text[i]
            if in_string:
                if ch == "\\":
                    i += 2
                    continue
                if ch == '"':
                    in_string = False
            elif ch == '"':
                in_string = True
            elif ch == "[":
                stack.append("]")
            elif ch == "{":
                stack.append("}")
            elif ch in "]}":
                if ch != stack[-1]:
                    raise ValueError("mismatched JSON delimiter")
                stack.pop()
            i += 1
        if stack:
            raise ValueError("unterminated container")
        return i
    while i < len(text) and text[i] not in ",}] \t\r\n":
        i += 1
    if i == skip_ws(text, 0):
        raise ValueError("invalid scalar")
    return i


def extract_fields(text: str, wanted: set[str] = WANTED) -> dict:
    """Decode only named top-level values; structurally skip all other values."""
    decoder = json.JSONDecoder()
    i = skip_ws(text, 0)
    if i >= len(text) or text[i] != "{":
        raise ValueError("top-level JSON must be object")
    i += 1
    found = {}
    while True:
        i = skip_ws(text, i)
        if i >= len(text):
            raise ValueError("unterminated object")
        if text[i] == "}":
            return found
        key, after_key = decoder.raw_decode(text, i)
        if not isinstance(key, str):
            raise ValueError("object key must be string")
        colon = skip_ws(text, after_key)
        if colon >= len(text) or text[colon] != ":":
            raise ValueError("expected colon")
        start = skip_ws(text, colon + 1)
        end = skip_value(text, start)
        if key in wanted:
            value, after_value = decoder.raw_decode(text, start)
            if skip_ws(text, after_value) != end:
                raise ValueError("decoded target boundary mismatch")
            found[key] = value
        i = skip_ws(text, end)
        if i < len(text) and text[i] == ",":
            i += 1
        elif i < len(text) and text[i] == "}":
            return found
        else:
            raise ValueError("expected comma or object end")


def audit(path: Path = SOURCE) -> dict:
    digest = hashlib.sha256()
    counts = collections.Counter()
    rows = 0
    selected = 0
    with path.open("rb") as stream:
        for raw in stream:
            digest.update(raw)
            rows += 1
            fields = extract_fields(raw.decode("utf-8"))
            if set(fields) != WANTED:
                raise ValueError(f"row {rows} missing required scope fields")
            if (fields["method"] == "TD" and fields["observed"] is True
                    and fields["complete"] is True
                    and fields["pv_terminal"] is True):
                counts[str(fields["seed"])] += 1
                selected += 1
    return {
        "task_id": 2602,
        "status": "BASELINE_EXPOSURE_SCOPE_CORRECTED",
        "source": {
            "path": path.as_posix(),
            "sha256": digest.hexdigest(),
            "rows_scanned": rows,
            "decoded_top_level_fields_only": sorted(WANTED),
            "all_other_top_level_values": "structurally skipped without JSON decoding",
        },
        "selection": "method=TD AND observed=true AND complete=true AND pv_terminal=true",
        "selected_rows": selected,
        "counts_by_seed": dict(sorted(counts.items())),
        "interpretation": (
            "Counts are exposure diagnostics only. They do not read or score outcomes, "
            "and cannot establish learning success or failure."
        ),
        "decision": (
            "The previously proposed >=128 terminal-PV exposure gate is not met by "
            "any listed frozen baseline seed; do not extend or relabel the old cap."
        ),
    }


def main() -> None:
    result = audit()
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "rows_scanned": result["source"]["rows_scanned"],
        "selected_rows": result["selected_rows"],
        "counts_by_seed": result["counts_by_seed"],
        "source_sha256": result["source"]["sha256"],
    }, separators=(",", ":")))


if __name__ == "__main__":
    main()
