# Task011: immutable published rollback correspondence

Question: does published sandbox558b497ba9ab4bd5464274571923959e628cbc03
contain exactly the Runtime candidate independently executed in Tasks007/008/010?

Compare the entire Runtime AST of the immutable Git blob to b4108a68a7ee06327be39cb3a222939644085a52
with only the bridge-key conjunct removed in SearchPathRuntime.push. Verify the
own working source still equals its pinned baseline AST. Enumerate all product
changes between these pins and inspect other changes separately.
No engine experiment, old regression rerun, primary checkout mutation or timing.
A mismatch restricts transfer to explicit function/context; exact match permits
transfer of already executed finite Runtime evidence, not primary test execution
or all-product acceptance. This new evidence binds publication, unlike Task008's
earlier mutable working-file observation.
