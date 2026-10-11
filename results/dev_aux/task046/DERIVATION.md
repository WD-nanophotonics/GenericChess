# Successful reads, next attempts and termination

For the reviewed heapq.merge implementation, let G be supplied streams (empty included), k nonempty, n total rows, and p yielded rows. Constructing the generator or requesting islice length0 never enters its body. This is the special unstarted p0 control from Task038, not all zero-result queries.

Once started, the merge initializer attempts next once on every stream, yielding k successful reads and G-k StopIteration events. Each resumed request after a yielded row attempts next on the stream that supplied that row. If it is exhausted, heap removal exposes a previously primed head rather than fetching another stream anew; the one-stream tail uses yield-from but has the same per-output accounting.

An early return immediately after p>=1 outputs therefore makes A=G+p-1 next attempts. Successful reads remain R=k+sum(successor exists in same group for each of first p-1 emitted ranks). Failed attempts equal A-R; p alone does not specify successful reads for multigroup ranks.

An actually exhausted nonempty merge makes one further next attempt after its last emitted row, so A=G+n and R=n. This also follows by counting n successes plus exactly one EOF per supplied stream (G total). An actually exhausted all-empty merge has A=G,R=0; an empty stream collection has G0 and no attempts. Stopping an islice after n outputs instead has A=G+n-1 when n>0, with the last EOF unrequested. Thus same yielded prefix can represent different termination cost.

Task038's numerical JSON remains valid for successful reads and the precise islice controls it executed. Correct its DERIVATION sentence 'For p=0 no merge work is entered' to the explicit unstarted/islice0 case. All-empty negative queries may enter the body and construct iterators/heap despite zero successfully borrowed rows. These laws count Python iterator calls, not total cost, allocation failure, hard cancellation delay, or search gains. No product/candidate change follows; default caller DEFER remains.
