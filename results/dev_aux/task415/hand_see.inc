#if defined(DEV_AUX_HAND_SEE) && defined(EVAL_MATERIAL) && MATERIAL_LEVEL == 1
    int swap = CapturePieceValue[piece_on(to)]
        + ((!drop && m.is_promote()) ? ProDiffPieceValue[piece_on(from)] : 0) - threshold;
#else
    int swap = PieceValue[piece_on(to)] - threshold;
#endif
	if (swap < 0)
        return false;

	// この時点で、
	//   PieceValue[piece_on(to)] - 最初に動かす駒の価値 >= threshold
	// なら、取り返されたところですでにしきい値以上になることは確定しているのでtrueが返せる。

#if STOCKFISH
	swap = PieceValue[piece_on(from)] - swap;
#else
	// →　駒打ちの時は、移動元にその駒がないので、これを復元してやる必要がある。
	PieceType from_pt = drop ? m.move_dropped_piece() : type_of(piece_on(from));
#if defined(DEV_AUX_HAND_SEE) && defined(EVAL_MATERIAL) && MATERIAL_LEVEL == 1
    const PieceType aux_after_from_pt = (!drop && m.is_promote())
        ? PieceType(int(from_pt) + 8) : from_pt;
    swap = CapturePieceValue[aux_after_from_pt] - swap;
#else
    swap = PieceValue[from_pt] - swap;
#endif
#endif

	if (swap <= 0)
        return true;

#if STOCKFISH
	assert(color_of(piece_on(from)) == sideToMove);
#else
	ASSERT_LV3(drop || color_of(piece_on(from)) == sideToMove);
#endif

    Bitboard occupied  = pieces() ^ from ^ to;  // xoring to is important for pinned piece logic
    Color    stm       = sideToMove;
    Bitboard attackers = attackers_to(to, occupied);
    Bitboard stmAttackers, bb;
    int      res = 1;

    while (true)
    {
        stm = ~stm;
        attackers &= occupied;

        // If stm has no more attackers then give up: stm loses
        // 手番側がtoに利く駒が尽きたなら、お手上げ。(see_geの判定は)手番側の負け。
        if (!(stmAttackers = attackers & pieces(stm)))
            break;

        // Don't allow pinned pieces to attack as long as there are
        // pinners on their original square.
        // 元のマスにピンしている駒がある限り、ピンされている駒が攻撃することを許可しない。
        if (pinners(~stm) & occupied)
        {
            stmAttackers &= ~blockers_for_king(stm);

            if (!stmAttackers)
                break;
        }

        res ^= 1;

        // Locate and remove the next least valuable attacker, and add to
        // the bitboard 'attackers' any X-ray attackers behind it.
        // 次に価値の低い攻撃駒を特定して取り除き、その背後にいるX線攻撃駒を
        // ビットボード 'attackers' に追加する。

        // DEV_AUX: candidate board-price LVA; retain upstream board-only SEE approximation.
        bb = Bitboard(ZERO);
        PieceType selected = NO_PIECE_TYPE;
        int cheapest = 100000000;
#if defined(DEV_AUX_HAND_SEE) && defined(EVAL_MATERIAL) && MATERIAL_LEVEL == 1
        const auto& aux_see_prices = CapturePieceValue;
#else
        const auto& aux_see_prices = PieceValue;
#endif
        for (int pt = 1; pt <= 14; ++pt) {
            if (pt == int(KING)) continue;
            auto candidates = stmAttackers & pieces(PieceType(pt));
            if (candidates && aux_see_prices[pt] < cheapest) {
                cheapest = aux_see_prices[pt]; selected = PieceType(pt); bb = candidates;
            }
        }
        if (!bb) return (attackers & ~pieces(stm)) ? res ^ 1 : res;
        if ((swap = aux_see_prices[selected] - swap) < res) break;
