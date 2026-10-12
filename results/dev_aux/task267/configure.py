def configure(e, w):
    assert set(w) == set('PNBRQK') and type(w['K']) is int and (w['K'] == 0)
    assert all((type(w[k]) is int and 32 <= w[k] <= 4096 for k in 'PNBRQ'))
    P.A.guard(deadline, P.stop)
    line = ' '.join((k.lower() + ':' + str(w[k]) for k in 'PNBRQ'))
    config = O / 'variant.ini'
    config.write_text('[aux_short:chess]\npieceValueMg = ' + line + '\npieceValueEg = ' + line + '\n', encoding='utf-8')
    for name, value in [('Threads', 1), ('Hash', 16), ('Use NNUE', 'false'), ('SyzygyPath', '<empty>'), ('VariantPath', str(config)), ('UCI_Variant', 'aux_short')]:
        e.send('setoption name ' + name + ' value ' + str(value))
        reply = e.ready()
        if name == 'UCI_Variant':
            assert any((z.startswith('info string variant aux_short files 8 ranks 8 ') for z in reply))
    probes = []
    for kind in 'PNBRQ':
        fen = '7k/8/8/3' + kind + '4/8/8/8/K7 w - - 0 1'
        e.send('position fen ' + fen)
        e.send('eval')
        rr = e.ready()
        v = [z for z in rr if z.startswith('Final evaluation')]
        assert len(v) == 1
        value = float(v[0].split()[2])
        assert math.isfinite(value) and abs(value - w[kind] / 208) < 0.011
        probes.append(dict(type=kind, fen=fen, measured_white_pawns=value, expected_white_pawns=w[kind] / 208))
    e.send('setoption name UCI_Variant value aux_short')
    reply = e.ready()
    ack = [z for z in reply if z.startswith('info string DEV_AUX alignment ')]
    assert len(ack) == 1
    tokens = ack[0].split()
    assert int(tokens[4]) == 3
    prices = {int(z.split(':')[0]): tuple(map(int, z.split(':')[1:])) for z in tokens[5:]}
    assert prices == {i + 1: (w[k], w[k]) for i, k in enumerate('PNBRQ')}
    e.send('ucinewgame')
    e.ready()
    return (probes, dict(raw=ack[0], prices={str(k): list(v) for k, v in prices.items()}, alignment=3))
