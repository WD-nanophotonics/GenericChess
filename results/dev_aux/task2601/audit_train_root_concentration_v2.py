from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

TASK = Path("results/dev_aux/task2601")
SOURCE = Path("results/dev_aux/task2595/root-manifest.json")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def skip_ws(text: str, i: int) -> int:
    while i < len(text) and text[i] in " \t\r\n":
        i += 1
    return i


def skip_value(text: str, i: int) -> int:
    """Return the end of a JSON value without decoding its contents."""
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
        raise ValueError("unterminated JSON string")
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
                if not stack or ch != stack[-1]:
                    raise ValueError("mismatched JSON delimiter")
                stack.pop()
            i += 1
        if stack:
            raise ValueError("unterminated JSON container")
        return i
    while i < len(text) and text[i] not in ",}] \t\r\n":
        i += 1
    return i


def extract_object_value(text: str, wanted: str):
    decoder = json.JSONDecoder()
    i = skip_ws(text, 0)
    if i >= len(text) or text[i] != "{":
        raise ValueError("top-level JSON must be an object")
    i += 1
    while True:
        i = skip_ws(text, i)
        if i >= len(text):
            raise ValueError("unterminated top-level object")
        if text[i] == "}":
            raise KeyError(wanted)
        key, i = decoder.raw_decode(text, i)
        if not isinstance(key, str):
            raise ValueError("top-level object key must be text")
        i = skip_ws(text, i)
        if i >= len(text) or text[i] != ":":
            raise ValueError("expected colon after key")
        start = skip_ws(text, i + 1)
        end = skip_value(text, start)
        if key == wanted:
            value, decoded_end = decoder.raw_decode(text, start)
            if skip_ws(text, decoded_end) != end:
                raise ValueError("target array parse did not end at scanned boundary")
            return value
        i = skip_ws(text, end)
        if i < len(text) and text[i] == ",":
            i += 1
            continue
        if i < len(text) and text[i] == "}":
            raise KeyError(wanted)
        raise ValueError("expected comma or object end")


def canonical(record: dict) -> str:
    return json.dumps(record, sort_keys=True, separators=(",", ":"))


def main() -> None:
    out = TASK / "root-concentration-v2.json"
    assert not out.exists()
    text = SOURCE.read_text(encoding="utf-8")
    rows = extract_object_value(text, "train")
    assert isinstance(rows, list) and len(rows) == 8192
    counts = collections.Counter(canonical(row["record"]) for row in rows)
    n = len(rows)
    sum_sq = sum(c * c for c in counts.values())
    terminal = sum(row["terminal"] is not None for row in rows)
    depths = collections.Counter(len(row["record"]["actions"]) for row in rows)
    first_moves = collections.Counter(
        canonical(row["record"]["actions"][0]) if row["record"]["actions"] else "<empty>"
        for row in rows
    )
    result = {
        "task_id": 2601,
        "status": "DESCRIPTIVE_TRAIN_ONLY_SCOPE_CORRECTED",
        "question": "How concentrated are the frozen task2595 TRAIN root draws by complete serialized history?",
        "source": {
            "path": str(SOURCE).replace("\\", "/"),
            "sha256": sha256(SOURCE),
            "rows_decoded": n,
            "scope": "TRAIN array only; other top-level values are structurally skipped without JSON decoding",
        },
        "canonicalization": "compact JSON of complete record with sorted object keys; includes ruleset fingerprint and ordered actions",
        "metrics": {
            "draws": n,
            "unique_full_histories": len(counts),
            "unique_fraction": len(counts) / n,
            "duplicate_excess": n - len(counts),
            "sum_squared_cluster_multiplicity": sum_sq,
            "simpson_concentration_equivalent_draws": n * n / sum_sq,
            "simpson_concentration_fraction": n / sum_sq,
            "max_history_multiplicity": max(counts.values()),
            "terminal_draws": terminal,
            "terminal_fraction": terminal / n,
            "history_depth_counts": dict(sorted(depths.items())),
            "distinct_first_actions": len(first_moves),
            "top_five_first_action_counts": [
                {"action": json.loads(action), "draws": count}
                for action, count in first_moves.most_common(5)
            ],
        },
        "interpretation_limit": (
            "The Simpson value is a descriptive concentration equivalent under "
            "row-frequency weights, not a claim about independent games or a "
            "valid inferential sample size. Repeated histories remain valid "
            "weighted draws if that is the declared target."
        ),
        "prohibited_inferences": [
            "No learner fitness result.",
            "No population claim about Generic rules.",
            "No new admission gate for task2595.",
            "No EVAL root or outcome inspection, root replacement, or rerun.",
        ],
    }
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["metrics"], separators=(",", ":")))


if __name__ == "__main__":
    main()
