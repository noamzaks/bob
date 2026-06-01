from bob.prelude import *

rule("echo hi > $out").build("dummy.txt")
