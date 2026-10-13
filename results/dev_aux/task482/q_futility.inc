#if defined(DEV_AUX_FULL_CAPTURE_FUTILITY) && defined(EVAL_MATERIAL) && MATERIAL_LEVEL == 1
                Value futilityValue = futilityBase +
                                    (CapturePieceValue[pos.piece_on(move.to_sq())] + ((!move.is_drop() && move.is_promote()) ? ProDiffPieceValue[pos.piece_on(move.from_sq())] : 0));
#else
                Value futilityValue = futilityBase +
                                    PieceValue[pos.piece_on(move.to_sq())];
#endif