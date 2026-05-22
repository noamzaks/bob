# Build using `bob build -f Tomatofile.py`.

from bob.prelude import *

rule("echo hi > $out").build("dummy.txt")

include("another/Tomatofile.py")
