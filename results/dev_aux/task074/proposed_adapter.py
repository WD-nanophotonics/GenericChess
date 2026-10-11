class CapsuleRuntime:

    def __init__(self, initial, c, witnesses):
        self.compiled = c
        self.native = compile_native_semantic_rules(c)
        self.capsule = pack_semantic_search_position(c, self.native, SimpleNamespace(compiled=c, state=initial, _search_witnesses=witnesses))
        self.cache = None
        self.term = None
        self.stack = []
        self.legal_provider_calls = 0
        self.legal_provider_fallbacks = 0
        self.legal_provider_operational_failures = 0
        self.views = 0
        self.transitions = 0
        self.rawmap = {}
        assert self.position == initial.position and self.terminal_status == initial.terminal_status

    def attach_stats(self, stats):
        self.stats = stats

    def full_snapshot(self):
        return ns.snapshot(self.native, self.capsule)

    @property
    def position(self):
        if self.cache is None:
            s = self.full_snapshot()
            ids = self.native.type_ids
            board = tuple((None if x is None else Piece(int(x[2]), ids[int(x[0])], ids[int(x[1])], bool(x[3])) for x in s['board']))
            hands = tuple((Hands(tuple(sorted(((ids[i], int(v)) for i, v in enumerate(h) if v)))) for h in s['hands']))
            self.cache = Position(board, hands, int(s['side']), self.compiled.ruleset_fingerprint, s['aux_state'])
            self.ply_count = int(s['ply'])
            self.views += 1
        return self.cache

    @property
    def terminal_status(self):
        if self.term is None:
            t = ns.terminal_status(self.native, self.capsule)
            self.term = TerminalResult(TerminalStatus(t['status']), t['winner'])
        return self.term

    @property
    def state(self):
        return SimpleNamespace(position=self.position, terminal_status=self.terminal_status, ply_count=self.ply_count)

    def in_check(self, owner, checkpoint=None):
        if checkpoint:
            checkpoint()
        return ns.in_check(self.native, self.capsule, owner)

    def legal_actions(self, checkpoint=None):
        if checkpoint:
            checkpoint()
        self.legal_provider_calls += 1
        raw = ns.transient_legal_actions(self.native, self.capsule)
        self.rawmap = {ns.public_action(self.native, a): a for a in raw}
        return tuple(self.rawmap)

    def push(self, action, checkpoint=None):
        if checkpoint:
            checkpoint()
        raw = self.rawmap[action] if action in self.rawmap else pack_semantic_action(self.native, self.position, action)
        old = (self.capsule, self.cache, self.term, self.rawmap, self.ply_count)
        child = ns.make_checked(self.native, self.capsule, raw)
        self.stack.append(old)
        self.capsule = child
        self.cache = self.term = None
        self.rawmap = {}
        self.transitions += 1

    def pop(self):
        self.capsule, self.cache, self.term, self.rawmap, self.ply_count = self.stack.pop()

    def assert_balanced(self):
        assert not self.stack
