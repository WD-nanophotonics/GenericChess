"""Native clear-quiet/one-screen contact theorem, not a game solver."""
def histogram(width,height):
    if any(type(x) is not int or x<2 for x in (width,height)):
        raise ValueError('two-dimensional integer rectangle required')
    counts={t:0 for t in range(1,5)}
    for length,other in ((width,height),(height,width)):
        pairs=(length-2)*(length-1)
        numerator=length*(length-1)*(length-2)
        assert numerator%3==0
        firing=numerator//3
        counts[1]+=other*firing
        counts[2]+=other*(other-1)*firing
        counts[3]+=other*(other-1)*(length*pairs-firing)
        counts[4]+=other*((length-2)*pairs-firing)
    total=width*height*(width*height-1)*(width*height-2)
    return {'histogram':counts,'unreachable':total-sum(counts.values()),'total':total}
