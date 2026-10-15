"""Independent, mechanically sized closed K/R/N/B actor control.

No pawns, castling, drops or history adjudication. Public Core owns actual
history/terminals in the experiment. This module only checks legal transitions.
"""
class RoyalActor:
    def __init__(self,width):
        if type(width) is not int or not 3<=width<=8:
            raise ValueError('width must be3..8')
        self.width=width;self.size=width*width

    @staticmethod
    def side(piece):return int(piece.islower())

    def king(self,state,side):return state[:-1].index('k' if side else 'K')

    def hit(self,state,a,b):
        w=self.width;piece=state[a].upper();dx=b%w-a%w;dy=b//w-a//w
        if piece=='K':return max(abs(dx),abs(dy))==1
        if piece=='N':return sorted((abs(dx),abs(dy)))==[1,2]
        if piece=='R':
            if (dx==0)==(dy==0):return False
        elif piece=='B':
            if abs(dx)!=abs(dy) or not dx:return False
        else:return False
        step=(dx>0)-(dx<0)+w*((dy>0)-(dy<0));q=a+step
        while q!=b:
            if state[q]!='.':return False
            q+=step
        return True

    def attacked(self,state,square,side):
        return any(p!='.' and self.side(p)==side and self.hit(state,i,square) for i,p in enumerate(state[:-1]))

    def valid(self,state):
        if len(state)!=self.size+1 or type(state[-1]) is not int or state[-1] not in (0,1):return False
        if state[:-1].count('K')!=1 or state[:-1].count('k')!=1:return False
        if any(p not in '.KRNBkrnb' for p in state[:-1]):return False
        return not self.attacked(state,self.king(state,1-state[-1]),state[-1])

    def moves(self,state):
        side=state[-1];out=[];w=self.width
        for a,p in enumerate(state[:-1]):
            if p=='.' or self.side(p)!=side:continue
            for b,q in enumerate(state[:-1]):
                if a==b or q!='.' and (self.side(q)==side or q.upper()=='K'):continue
                if not self.hit(state,a,b):continue
                child=list(state);child[a]='.';child[b]=p;child[-1]=1-side;child=tuple(child)
                if self.attacked(child,self.king(child,side),1-side):continue
                u=chr(97+a%w)+str(a//w+1)+chr(97+b%w)+str(b//w+1)
                out.append((u,child))
        return sorted(out)

    def fen(self,state):
        w=self.width;rows=[]
        for y in range(w-1,-1,-1):
            row='';empty=0
            for piece in state[w*y:w*y+w]:
                if piece=='.':empty+=1
                else:
                    if empty:row+=str(empty);empty=0
                    row+=piece
            if empty:row+=str(empty)
            rows.append(row)
        return '/'.join(rows)+(' w ' if state[-1]==0 else ' b ')+'- - 0 1'
