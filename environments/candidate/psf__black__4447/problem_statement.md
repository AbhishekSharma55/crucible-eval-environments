# psf/black#4447

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #4446 — https://github.com/psf/black/issues/4446

**Describe the bug**

Black running on M1 MacBooks does drop a few Characters of Python Source Code, when given these particular 120 Characters, but only sometimes. Sometimes you call Black and it works. Sometimes you call, and it chokes

**To Reproduce**

Visit an M1 MacBook and feed these 4 Lines of Python Code into Black

For example, take these 4 Lines, formatted exactly as shown

```python
import argparse
import string


S1 = f"{argparse.OPTIONAL[:9]=}"
S2 = (string.ascii_uppercase + string.ascii_lowercase)
```

And try calling Black, more than once, on this same input with no arguments

```sh
black file.py
```

The resulting error is:

> INTERNAL ERROR: Black produced code that is not equivalent

It drops the : 9 ] = part of the F String Slice. Oops

**Expected behavior**

No Internal Error

**Environment**

- Black's version:  24.8.0 (compiled: yes)
- OS and Python version: Python (CPython) 3.12.5 at macOS 14.6.1 23G93 on Apple M1 Pro Chip inside MacBook Pro 16-inch, 2021

**Additional context**

Below is a Terminal transcript of reproducing this occasional Internal Error

Look closely and you'll see some runs on the same input fail like this, but some runs don't fail. This bug combines ( a ) that the results can and are inconsistent, and ( b ) that some of the results are Internal Errors

```
(PIPS) % 
(PIPS) % 
(PIPS) % cp -p p1.py p2.py && black p2.py
error: cannot format p2.py: INTERNAL ERROR: Black produced code that is not equivalent to the source.  Please report a bug on https://github.com/psf/black/issues.  This diff might be helpful: /var/folders/6j/yj_0gg5d7dg02zhp0vwfx0580000gp/T/blk_kyph83rd.log

Oh no! 💥 💔 💥
1 file failed to reformat.
(PIPS) % 
(PIPS) % cat /var/folders/6j/yj_0gg5d7dg02zhp0vwfx0580000gp/T/blk_kyph83rd.log
--- src
+++ dst
@@ -34,11 +34,11 @@
             values=
             Constant(
                 kind=
                 None,  # NoneType
                 value=
-                'argparse.OPTIONAL[:9]=',  # str
+                'argparse.OPTIONAL[',  # str
             )  # /Constant
             FormattedValue(
                 conversion=
                 114,  # int
                 format_spec=
(PIPS) % 
(PIPS) % cat p1.py
import argparse
import string


S1 = f"{argparse.OPTIONAL[:9]=}"
S2 = (string.ascii_uppercase + string.ascii_lowercase)
(PIPS) % 
(PIPS) % 
(PIPS) % cp -p p1.py p2.py && black p2.py
error: cannot format p2.py: INTERNAL ERROR: Black produced code that is not equivalent to the source.  Please report a bug on https://github.com/psf/black/issues.  This diff might be helpful: /var/folders/6j/yj_0gg5d7dg02zhp0vwfx0580000gp/T/blk_wzw1ae9e.log

Oh no! 💥 💔 💥
1 file failed to reformat.
(PIPS) % 
(PIPS) % cp -p p1.py p2.py && black p2.py
reformatted p2.py

All done! ✨ 🍰 ✨
1 file reformatted.
(PIPS) % 
(PIPS) % black --version
black, 24.8.0 (compiled: yes)
Python (CPython) 3.12.5
(PIPS) % 
(PIPS) % md5sum p1.py
+ openssl dgst -md5 p1.py
+ tr '()=' ' '
+ awk '{print $3, $2}'
ee23bcabee4f1f5677c443bd6b4b2449 p1.py
(PIPS) % 
```

This Bug only repros for me on my M1 MacBook

I've not found anywhere else where it will repro. I tried a Linux, but it didn't repro there. Every time I've tried it three times in a row at my M1 MacBook, I do repro 1 or 2 or 3 Failures

I first saw this go boom on 962 Lines

Thank you for believing I could help. Am I helping? Can I help more?

## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `psf/black`
- Pull request: https://github.com/psf/black/pull/4447
- Pull request title: Prevent use on Python 3.12.5
- Merged at: 2024-09-07T23:41:06Z
- Parent commit (bug present): `ac28187bf4a4ac159651c73d3a50fe6d0f653eac`
- Fix commit (bug absent): `9e13708be845188424c718d3a3b26c2e6a4fd7a1`
- Changed source paths: src/black/__init__.py
