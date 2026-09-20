F135 closeout: corrected Standard Shogi known-evaluator schema rebaseline

- Work order: GENERICCHESS_F135_CORRECTED_SHOGI_ORACLE_SCHEMA_REBASELINE
- Existing Courier request: GENERICCHESS-20260919-224046-8034193a
- Baseline SHA: e13c55d5008e9ee57010e9fd3118a31bac2659d1
- Heavy run: F135 Heavy, completed in 2655.0480518341064 seconds
- Frozen corpus: train 3000, dev 750, holdout 750; seed 1220201; identity SHA a1cb1bcf2d461c3bddc4f87928ed4d6260673de268356eec5741b9b534d4aa8b
- Corrected schema: CorrectedShogiFrozenBasisV2; width 1086; feature-name SHA 6accfab1039a546071a23c885d582a2c10792e5db49f69bfa9556c131d516942; corrected oracle SHA fdd6405ffa3f92de05f401dbd12d00a16191ac10c2ba2383fe5332694c9e7aa6
- Legacy oracle SHA: dda316e263a8f6e5a12678199e87cbedea7e4d40358d3087e8c78ddb3894a316; schema witnesses passed for mobility, king escape, king-zone pressure, current check, promotion potential, every hand type, and legal-drop count; Western parity regression passed
- Legacy-vs-corrected scalar audit: RMSE 2864.9107010709968; normalized RMSE 2.1156714620729784; R² 0.4810215529197631; Pearson 0.7869385221038856; Spearman 0.7773195821335707; sign agreement 0.8491111111111111; maximum absolute difference 12336.5
- Legacy-vs-corrected action audit: 256 roots; top-action agreement 0.86328125; pairwise agreement 0.9726439943543965; 35 roots differed; mean corrected-oracle regret 94.07144047457143 raw / 0.06946962149073126 normalized
- Corrected PCG numerical gate: pass; relative residual 7.846774358235549e-13; objective excess -1.5881867761018131e-22; holdout prediction delta 4.0869142325251964e-10 normalized
- Corrected scalar gate: fail; holdout RMSE 211.189237270397; nRMSE 0.15595845351232307; R² 0.9756769607780446; Pearson 0.9878499297805251; Spearman 0.9459971591060606
- Corrected one-ply action gate: pass; top-1 0.97265625; pairwise 0.9851308467506316; mean normalized regret 0.0024239891704051506
- Search diagnostic: 64 roots, 2000 nodes, depth 12; top-action/PV agreement 0.8125; node parity 1.0; completed-depth parity 0.96875; diagnostic only
- Fixed F127 surface: retained train/dev/holdout 1995/252/254; matched-ridge holdout nRMSE 0.16280988963876133; no full-population 0.05 gate imposed
- Classification: CORRECTED_KNOWN_EVALUATOR_SYSTEM_IDENTIFICATION_FAILS

The corrected semantic schema is now independently materialized through a keyed
feature map with exact name-set, width, finite-value, and witness checks. Western
Chess semantics were unchanged. The corrected oracle is numerically identifiable
by the stable PCG learner and passes one-ply action recovery, but it fails the
predeclared scalar A1 gate; the corrected direct-control chain therefore does not
pass. F129-F134 remain reproducible historical measurements but their semantic
interpretations are quarantined as instructed. No A2/F136 experiment, feature
engineering, self-play, MCTS, Arena, or promotion was performed.
Transient result, stage, and shard files remain under the local flow runtime and
are intentionally excluded from Git.

Validation: tests/test_f135_corrected_shogi_oracle_schema_rebaseline.py passed.
