# GenericChess F83 C2 Selective Successor Arena4 Closeout

Date: 2026-09-15  
Mode: Courier  
Work package: selective-correction successor and minimum strength triage

## Successor construction

The successor treats the published C2 candidate as parent. It trains on the 12 frozen roots where C2's teacher-row top action disagreed with the registered deep-search target, while using each existing C2 top action as an explicit retention target on the other 24 roots. The selected alpha was `0.25`; the retention gate required the preserved roots to keep their top action and at least 75% of their parent top-two margin.

- Successor checkpoint: `7e4298b75a5ee6da22f77d33197ddb38f4c759a1d059386cc1f2be7902d310d1`
- Successor model SHA-256: `529a2ae3da9b9f09d16a7c27881c525f63cdd63c641a4d26f974d27bc0308a1c`
- Parent C2 checkpoint: `86f026ef85d60e600bc1bd6bc7b7285f11e5ce7e6528911b2ea361a489dc5983`
- Parent C2 model SHA-256: `b2308bea76ba55a533b95036f9b0ca37265c15d772ce5fbd14f7b6b098677e95`
- Descriptor SHA-256: `62175408caf78fd91af2f4059d43da89cacb23814b02e470ac8903fb0ba8483e`
- Result artifact SHA-256: `c736a9ef9375ce22a908340230c3142039db0df44f0fb3452e2baa62748ba4f5`
- Corrected roots: 12; preserved roots: 24; retention gate: true

## Approved Arena execution

- Execution plan: `f83-c2-selective-successor-arena4-v2`
- Plan SHA-256: `03fee93c240f73d8920267bc17e3b88c7a814c80a555c01531de5b18a61d656a`
- Resource envelope digest: `5a90cfb12af7581702aa724032b8ac1fec2cd707253eff051df1cf98c02717f7`
- Execution-bound sandbox SHA: `9038c79bf4de601ec28c1ef3148ff1aac833b75a`
- Chat scientific approval: explicit `APPROVE`
- Supervisor binding: exact plan/envelope/sandbox approved
- Registered corpus: Arena4 `593652dd655ddc67f38d9a194b9b2a44f7eef3e28d22a83c5f01abeb35b971a1`
- Opening index: 2; seed `820401`; one role-swapped pair; 512 nodes/move; depth 12; 8 MiB TT; TT reset each move

The first invocation reached the approved stage boundary with owner0 complete and owner1 partial. The exact same argv was resumed; no replacement plan or experiment was created. The resumed run completed the pair:

```text
status=COMPLETE
completed_games=2
completed_pairs=1
game_wins=1
game_losses=1
game_draws=0
mean_pair_score=0.5
opening_final_position_key=614a1fe27d920b4fb2417211588e44730abf6ef4889662b274e723b043df54bf
```

| Game | Child owner | Result | Winner | Plies | Final position key | Artifact SHA-256 |
| --- | ---: | --- | ---: | ---: | --- | --- |
| `game-000000-owner-0.json` | 0 | checkmate | 1 | 81 | `e00df070413ac18024f85332e437be0cd2c0654a9fc7041871fe247439b15d11` | `116c18ff55456995a8b7fb358f0b044113a7639ae036b58bf03ba9a118ffff0f` |
| `game-000000-owner-1.json` | 1 | checkmate | 1 | 235 | `99cc898e2498ba2a9b457206206710d03e8a66d7e2bfea05e7ac91b7f6d6fe1b` | `df8e733ca11286135bd78fefdd1f69a0c57e91442e3d17fb7030779adfaa67c9` |

Result JSON SHA-256: `49283d88e78d819e04842e602ee8e382eb9fa086b6558156fab266c1e1e7d7b5`.

## Decision

The selective successor also produced one win and one loss, with pair score `0.5`. This minimum triage sample provides no strength advantage over its C2 parent. Do not run another pair, Arena8, or promotion under this work package; return to Chat for the next learning decision.

## Recovery fix included in final checkpoint

The execution exposed no new transport issue. A small durable harness fix was also published after the run: a Supervisor-resolved scientific escalation with no request directory now returns the worker recovery state directly to `IDLE` instead of leaving it in `RECOVERED`, with regression coverage. The final published checkpoint is `dc15371f3de9c542f6c1e02b76a0af45f3b67c37`; the execution plan remains bound to the earlier clean checkpoint above.

Focused publication tests passed (89 tests across generic flow, successor identity, F82, arena integrity, and atomic arena suites).
