#!/usr/bin/env python3

r"""
Call each Py in order, to support a workflow such as:


clear
clear  # Bash freaks without the repeat
cd ~/Desktop/Chase

python3 -i run-break-fix.py
import pdb, sys
if getattr(sys, 'last_traceback', None):
    pdb .pm()  # Twitter freaks without the blank
# Python freaks without the trailing blank line


"""

import pdb
import sys

import chase
import mark

chase.main()
mark.main()
