#! /usr/bin/python2
from glob import glob
from os.path import expanduser, join, basename
from os import remove, devnull
from shutil import copy
from sys import argv
from subprocess import Popen, STDOUT

tmp_dir = expanduser(join("~", ".mutt", "temp", "attachments"))

for f in glob(join(tmp_dir, "*")):
    remove(f)

basename = basename(argv[1])
copy(argv[1], tmp_dir)
Popen(["xdg-open", join(tmp_dir, basename)],
      stderr=STDOUT,
      stdout=open(devnull, "wb"))
