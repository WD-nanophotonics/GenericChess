from collections import Counter
CAPS=dict(P=18,L=4,N=4,S=4,B=2,R=2,G=4,K=2)
def stock(sfen):
 board,turn,hand,num=sfen.split();out=Counter();prom=False
 for c in board:
  if c=='+':assert not prom;prom=True;continue
  if c=='/' or c.isdigit():assert not prom;continue
  assert c.upper() in CAPS;out[c.upper()]+=1;prom=False
 assert not prom;digits=''
 for c in hand:
  if c=='-':continue
  if c.isdigit():digits+=c;continue
  assert c.upper() in CAPS and c.upper()!='K';out[c.upper()]+=int(digits or '1');digits=''
 assert not digits;return dict(out)
def assert_supported(sfen):
 counts=stock(sfen)
 assert all(n<=CAPS[p] for p,n in counts.items()),('unsupported_native_stock',counts,CAPS)
 assert counts.get('K')==2;return counts
