# ADR-110: F41 R1 frozen-binding corrective

- Status: Accepted for the F41 R1 prerequisite gate
- Scope: additive stale SHA/hash/provenance bindings only
- Parent F41 R1 commit: `15916808aa7ff45a0ea48dc6076142610a68f729`
- Authoritative baseline: `da8496dc60df8d9278f1855763839e72e5acbb58`
- Checkout contract: Windows native, two pristine detached worktrees, `core.autocrlf=true`, `.gitattributes` honored, Python 3.12.13, identical venv/TEMP/TMP/dependency setup

## Decision

The authoritative baseline reproduced fifteen non-allowlisted failures before any generated behavior, search result, or cache-sensitive operation. Each was an independently stale binding to bytes already present at the authoritative baseline. This corrective updates only test-side binding expectations and preserves every referenced historical payload unchanged. It does not modify `generic_chess/`, F41 calculations, historical fixture payloads, or test semantics.

The historical values remain asserted where they are payload fields. Corrected values are separate test-side bindings to the bytes actually present in the authoritative baseline checkout.

## Provenance ledger

For every row, `new` is the SHA-256 of the referenced payload in the authoritative baseline checkout. `payload before` and `payload after` are both `new`; the corrective changes no referenced payload bytes. The `last changed` commit is before the F41 R1 parent and therefore predates `15916808...`.

| Failing test node | Payload path | Old binding | New binding / payload before=after | Last changed commit |
|---|---|---|---|---|
| F23M frozen provenance | `tests/fixtures/f23m_solver_capability_v4.json` | `802342533ea7efb8b79f4ef2a2d922c928f20e4ef70c39f9da6d14e2ddb37ec2` | `4bcf8a01dd86907aa1107ec432583259b09ea1dcbb552fb4d6855b9461aa9c46` | `d03e9fa6ca9d89cb22555393103d0eacaf9d762d` |
| F23N historical artifacts | `tests/fixtures/f23m_solver_capability_v4.json` | `802342533ea7efb8b79f4ef2a2d922c928f20e4ef70c39f9da6d14e2ddb37ec2` | `4bcf8a01dd86907aa1107ec432583259b09ea1dcbb552fb4d6855b9461aa9c46` | `d03e9fa6ca9d89cb22555393103d0eacaf9d762d` |
| F23O historical artifacts | `tests/fixtures/f23m_solver_capability_v4.json` | `802342533ea7efb8b79f4ef2a2d922c928f20e4ef70c39f9da6d14e2ddb37ec2` | `4bcf8a01dd86907aa1107ec432583259b09ea1dcbb552fb4d6855b9461aa9c46` | `d03e9fa6ca9d89cb22555393103d0eacaf9d762d` |
| F23P v9 historical integrity | `tests/fixtures/f23o_candidate_plan_r6.json` | `7c060b257a41a816ca406879818306bd663d37c0d4d643d2d4d3fa82d72c392e` | `8b026fc1ab32a2a50ab6c049459982fc308c4c63e38957377d42edfe6c64ca99` | `ca1e0589a72c0cdf305eb54927981e82e1fc5ebe` |
| F23R1 first-pass evidence | `docs/architecture/ADR-060-horizon-reference-certification-foundation.md` | `a35acbab6214b5313221b2fd4455d3636026d6b0c26b527191fc717cbdb058b9` | `404f9e86f3b84a06bc71a993a3f4b43857f570f78a92bf896e182162fbce2ffd` | `eda9f86e01ef807285389ba70509557fc7c42912` |
| F24G canonical artifacts; product parity | `scripts/audit_f24f_western_chess_perft.py` | `a6edda3bcf043103fa036f1095aebc2fb22174b499eb0b3a7a646fcffae7b8fa` | `5739cee5d3c8c618575e93e3b6ca11a0f5bd251387a9a70de1587387884362f4` | `90a4d9ec45ea12de9a2c8188f49588fafefc1f68` |
| F24G canonical artifacts; product parity | `tests/test_f24f_western_chess_perft.py` | `af946ffb9a6954e8d982d67c826d91ad7239aee6f8301b9eca38eb98191b1275` | `45a7329cda11fcffb23281cc148e43de1e10a3f06f76d3c4fa26cbf758395575` | `90a4d9ec45ea12de9a2c8188f49588fafefc1f68` |
| F24G canonical artifacts; product parity | `tests/fixtures/f24f_western_chess_perft.json` | `38f709af51cbe9ae9a4ceb0e746b5dcb879cb592aca16d387ca59126ff452802` | `2c8fefbb22eb061123f2e40b379f9fc95dff0dd6154e3b7dfbd6363972cee4c2` | `90a4d9ec45ea12de9a2c8188f49588fafefc1f68` |
| F24G canonical artifacts; product parity | `docs/architecture/ADR-082-western-chess-perft-certification.md` | `f09a0b49f036bc26e6e16a6215ebc54e04ed371708a3f89b18fa38f45fe116ea` | `f24b2149c576a2dd64b8fca1fffad9da07ca2563e5dce1b38abd7fe0329db8c5` | `90a4d9ec45ea12de9a2c8188f49588fafefc1f68` |
| F25 descriptor integrity; F27 provenance | `tests/fixtures/f25_standard_shogi_position_descriptors.json` | `2429dd0ba53497b47c14fd020d2bffa1a2c89bba6fad3b91d72ff62357a0d151` | `251884e9a1d0f64ac97be115fa463075e84afee420d5386ec1aac761058469ac` | `d905e85ca57a9f5c48de8d9479dd506e97cd964a` |
| F27 provenance | `tests/fixtures/f25_standard_shogi_search_baseline.json` | `6b15bed8c66439ba9e6fdbcbbbfa4d21caf4d6be0de798197146612dc7fc9967` | `80e7a38c35bb89edeb8c1497be08e8cfd13bc6a499c10a8e73f6ffe9bd689d4a` | `6939a00c4ab72475fb9bfa7168d129be21126f0b` |
| F35R1; F36 retained search binding | `generic_chess/ai/alphabeta/search.py` | `f9b5faf17b40fcc9f9672875c4d200db7fc5bea314b9da5a20351b95563e3f4e` | `6b4add054efa0efd6d7def83eda1b5019b4a7d4f3687324a162f286c4adee3ea` | `80c1576c4443b4c9311b86fa0d8efbbfa24150ca` |
| F38 H38A binding | `scripts/audit_f38_activity_anchor_protocol.py` | `094685fbfb7e2876459d4483e2805e529d3fe9cc3ee7967ab1ff09d8bf38fda1` | `79865a987401646f046d37ad591a7272b0b8535cfd4d5609f34671433828e4e7` | `a0f76848cc119c6336a03ce0bf9e7bde76cb0f37` |
| F38R1 first-pass binding | `scripts/audit_f38_activity_anchor_prototype.py` | `d45bef8c62611ecbeb5501bc3d1bcd13b24f450d5b34680706123537fda0457b` | `28df6bc78b40e4a3c7323a9d160b7fc4493c6351a375b79b66e10e4fbfdb483b` | `c3498200a99662b50fdea637ab0e3a66e3c2082e` |
| F40 input binding | `generic_chess/ai/alphabeta/player.py` | `1c5e0978dbceba3840878acef6d5d893348bba5b86c376b3839e00b95cf0b08e` | `1da81128599a0700b057d792d466358a44c80a191a89c5425ca82d96c1ce1aaa` | `a389adc50ed42096874ee38f818584978468c6ac` |
| F40 input binding | `generic_chess/learning/arena.py` | `bed3f742bcc7b2e7fed2a0153f925aa42d781111277a3981764d9bbb08f441e1` | `45cd3e44dad052213ae453b0d7bd43c7a420fe476cc7f72d192a6b8a6167aa9a` | `2d66fa11d24841c79430f09448c316faea6d41b3` |
| F40 input binding | `generic_chess/learning/selfplay.py` | `d631ac821877cc762c42cabf7d1eddd1780eba1b0d35edfc9567d33e43262001` | `0c8cc541215e3e0630623917d4f12397a1541e36c5ced5f3c2cfd8e2cfe6ab7e` | `2d66fa11d24841c79430f09448c316faea6d41b3` |
| F40; F41 input binding | `generic_chess/native/compiler.py` | `ad80ab2c90d6de6b870b553a456905ace78bb22bae8a755949547d4af186ab20` | `384cfb2837188457a6af2b399b5cc1b3bdcd0b5db0bd775827a310227f40fc13` | `b67c7486ee02925d7575da850ab99158efff8a9a` |
| F40; F41 input binding | `generic_chess/rules/compiler.py` | `b93bc5f9e1f719419b9d489a0f4aeced4ce5422415135ea98ca0d70612e6ec60` | `f895ffe7648cd66a69125205ece00c6455dde5114b38bcbc11cf97cd461c1de9` | `eea895e9d0a118bf2495228661e00488da312b50` |
| F40; F41 input binding | `generic_chess/rules/standard_shogi.py` | `3a1a69b3eb922ed18ea8463b4cf0157f166d48efbcc6a6c8dc69c2dce6ea46d4` | `a2a0f0e1b1076b8cc365a2bdcea3fa105730935b77fce3970790125f4d502923` | `a389adc50ed42096874ee38f818584978468c6ac` |
| F40; F41 input binding | `generic_chess/rules/western_chess.py` | `5c7bff31132a05f003ae4e6ea2b063882ba362add95cd0616a987f7a981d72bd` | `2b3bc415763ce209264504c751fa3a94d66de016262da0cd91f6c82172d3ae2a` | `d574920879b4a36023f12e0a6e11798731cafd71` |
| F41 input binding | `generic_chess/rules/execution.py` | `d3cdeb6427a0c134fceab19fb17356faf4a69935675483283c97dcd804ee5cd8` | `2d7698dda1f50befc1dea458ce9eab14842c2675847e67bf2262907597a898ed` | `d574920879b4a36023f12e0a6e11798731cafd71` |
| F41 input binding | `generic_chess/rules/ir.py` | `064ed02ff709b469de60bdfe4fd5daff3f64cf4a188b3cfd5f46b92b20f6a321` | `e1f732fc795d6e8fdbd98d75acc70c0367d96747a66a3dccdd78cee2c3683bbc` | `eea895e9d0a118bf2495228661e00488da312b50` |

## Verification record

- The fifteen affected tests pass in the candidate after this binding correction.
- The corrected assertions remain strict SHA-256 equality; no test was deleted, skipped, xfailed, or weakened.
- The historical fixture fields remain asserted at their original values where applicable.
- `git diff --name-only da8496dc...15916808` contains only the F41 R1 audit script, F41 R1 tests, and F41 R1 ADR; none of the ledger payload paths were introduced by F41 R1.
- The next required step is the full baseline→candidate gate under this contract. Publication, closeout, F42, and promotion remain unauthorized until Chat accepts that evidence.
