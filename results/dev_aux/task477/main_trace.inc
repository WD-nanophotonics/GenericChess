#if defined(DEV_AUX_FUTILITY_TRACE) && defined(EVAL_MATERIAL) && MATERIAL_LEVEL == 1
                    static thread_local unsigned aux_main_trace_count = 0;
                    if (capturedPiece != NO_PIECE && aux_main_trace_count < 64) {
                        ++aux_main_trace_count;
                        sync_cout << "info string auxfutility main alpha " << alpha
                            << " base " << (ss->staticEval + 218 + 223 * lmrDepth + 131 * captHist / 1024)
                            << " value " << futilityValue << " board " << PieceValue[capturedPiece]
                            << " full " << (CapturePieceValue[capturedPiece] + (move.is_promote() ? ProDiffPieceValue[movedPiece] : 0))
                            << " pruned " << (futilityValue <= alpha) << " ply " << ss->ply
                            << " depth " << lmrDepth << " move " << move.to_usi_string()
                            << " sfen " << pos.sfen() << sync_endl;
                    }
#endif
