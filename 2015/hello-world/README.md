# hello-world

Pat met GitHub in 2015, and spoke of Python.

I work with bots. Each bot shows me four panes: Paste, Trace, Watch, and Help. The bots written in Python look like this:

# 1. Paste
```
    import os
    [w for w in os.walk('.')]
```
# 2. Trace
```
    >>> import ctypes, sys; sys.version_info[:3] + (ctypes.sizeof(ctypes.c_void_p) * 8, sys.executable)
    (3, 5, 0, 64, '/Library/Frameworks/Python.framework/Versions/3.5/bin/python3')
    >>> import pdb; pdb.set_trace()
    --Return--
    > <stdin>(1)<module>()->None
    (Pdb)
```
# 3. Watch
```
    import argparse
    alice = 1; bob = 2; carol = 3
    print(argparse.Namespace(bob=bob, carol=carol, alice=alice)) 
```
# 4. Help

Google Search of the https://docs.python.org/3/tutorial/ and https://docs.python.org/3/library/

