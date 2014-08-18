#! /usr/bin/python2
import os
import sys
from subprocess import PIPE, Popen

os.environ["PARINIT"] = "85rTbgqR0d1 B=.,?!_A_a Q=_s>|+"

for line in sys.stdin:
    line = line.strip()
    print line
    if not line:
        break
sys.stdout.flush()

p = Popen("par", stdin=PIPE)
for line in sys.stdin:
    p.stdin.write(line)
