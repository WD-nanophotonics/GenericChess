#if defined(DEV_AUX_FUTILITY_TRACE) && defined(EVAL_MATERIAL) && MATERIAL_LEVEL == 1
                static thread_local unsigned aux_q_trace_count = 0;
                if (pos.piece_on(move.to_sq()) != NO_PIECE && aux_q_trace_count < 64) {
                    ++aux_q_trace_count;
                    const Piece aux_victim = pos.piece_on(move.to_sq());
                    sync_cout << "info string auxfutility q alpha " << alpha << " base " << futilityBase
                        << " value " << futilityValue << " board " << PieceValue[aux_victim]
                        << " full " << (CapturePieceValue[aux_victim] + (move.is_promote() ? ProDiffPieceValue[pos.piece_on(move.from_sq())] : 0))
                        << " pruned " << (futilityValue <= alpha) << " ply " << ss->ply
                        << " depth " << 0 << " move " << move.to_usi_string()
                        << " sfen " << pos.sfen() << sync_endl;
                }
#endif
