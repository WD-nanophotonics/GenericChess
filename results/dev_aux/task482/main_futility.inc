#if defined(DEV_AUX_FULL_CAPTURE_FUTILITY) && defined(EVAL_MATERIAL) && MATERIAL_LEVEL == 1
                    Value futilityValue = ss->staticEval + 218 + 223 * lmrDepth
                                        + (CapturePieceValue[capturedPiece] + ((!move.is_drop() && move.is_promote()) ? ProDiffPieceValue[pos.piece_on(move.from_sq())] : 0)) + 131 * captHist / 1024;
#else
                    Value futilityValue = ss->staticEval + 218 + 223 * lmrDepth
                                        + PieceValue[capturedPiece] + 131 * captHist / 1024;
#endif