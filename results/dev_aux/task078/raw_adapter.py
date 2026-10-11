class RawRuntime(CapsuleRuntime):
    def __init__(self,*args):
        self.rawcache=None;self.rawstack=[];self.rawviews=0
        super().__init__(*args)
    @property
    def raw_snapshot(self):
        if self.rawcache is None:
            self.rawcache=ns.snapshot(self.native,self.capsule);self.rawviews+=1
        return self.rawcache
    def push(self,action,checkpoint=None):
        old=self.rawcache
        super().push(action,checkpoint)
        self.rawstack.append(old);self.rawcache=None
    def pop(self):
        super().pop();self.rawcache=self.rawstack.pop()
    def assert_balanced(self):
        super().assert_balanced();assert not self.rawstack

def raw_enemy_count(s,side):
    return sum(p is not None and int(p[2])!=side for p in s['board'])
def raw_inventory(s):
    out={}
    for p in s['board']:
        if p is not None:
            key=(int(p[2]),int(p[1]));out[key]=out.get(key,0)+1
    for o,h in enumerate(s['hands']):
        for t,count in enumerate(h):
            if count:
                key=(o,t);out[key]=out.get(key,0)+int(count)
    return out

def raw_noisy(rt,side,enemies,inventory,poll):
    s=rt.raw_snapshot
    if raw_enemy_count(s,side)<enemies:return True
    if raw_inventory(s)!=inventory:return True
    if rt.terminal_status.is_terminal:return True
    return rt.in_check(int(s['side']),checkpoint=poll)
