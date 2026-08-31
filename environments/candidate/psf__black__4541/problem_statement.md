# psf/black#4541

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #4540 — https://github.com/psf/black/issues/4540

**Describe the bug**

`is_fstring_start` using `builtin.any` for prefix matching is too slow and slows down fstring tokenization.

```python
def is_fstring_start(token: str) -> bool:
    return builtins.any(token.startswith(prefix) for prefix in fstring_prefix) # using `any` with `<genexpr>` is too slow
```

**To Reproduce**

Run this minimal reproducing script:
```
import cProfile, pstats, io
from blib2to3.pgen2 import tokenize

profiler = cProfile.Profile()
example = io.StringIO(','.join(['f"X"']*10000)).readline
profiler.enable()
tokenize.tokenize(example, lambda *_: None)
profiler.disable()

pstats.Stats(profiler).sort_stats(pstats.SortKey.TIME).print_stats("black", "src", 10)
```

The profiling output looks like this:

```
         720011 function calls in 0.133 seconds

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
    40001    0.040    0.000    0.124    0.000 black/src/blib2to3/pgen2/tokenize.py:559(generate_tokens)
   190000    0.021    0.000    0.036    0.000 black/src/blib2to3/pgen2/tokenize.py:466(<genexpr>)
        1    0.008    0.008    0.133    0.133 black/src/blib2to3/pgen2/tokenize.py:280(tokenize_loop)
    10000    0.004    0.000    0.048    0.000 black/src/blib2to3/pgen2/tokenize.py:463(is_fstring_start)
    59997    0.003    0.000    0.003    0.000 black/src/blib2to3/pgen2/tokenize.py:528(current)
    10000    0.001    0.000    0.002    0.000 black/src/blib2to3/pgen2/tokenize.py:534(leave_fstring)
    10000    0.001    0.000    0.002    0.000 black/src/blib2to3/pgen2/tokenize.py:531(enter_fstring)
        1    0.000    0.000    0.133    0.133 black/src/blib2to3/pgen2/tokenize.py:260(tokenize)
        2    0.000    0.000    0.000    0.000 black/src/blib2to3/pgen2/tokenize.py:525(is_in_fstring_expression)
        1    0.000    0.000    0.000    0.000 black/src/blib2to3/pgen2/tokenize.py:522(__init__)
```
The `<genexpr>` in `is_fstring_start` typically occupies around 15-20% of the time, which is too much and easily optimizable.


**Environment**

- Black's version: [main]
- OS and Python version: [Mac/Python 3.12.6]

**Proposed Solution**
change the `fstring_prefix` to a tuple and use `token.startswith(fstring_prefix)` directly

cc. @JelleZijlstra @tusharsadhwani 

## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `psf/black`
- Pull request: https://github.com/psf/black/pull/4541
- Pull request title: Speed up `blib2to3` tokenization using generic python function
- Merged at: 2024-12-30T01:17:50Z
- Parent commit (bug present): `9431e98522ec91087f0e2b5fcd71a7a807f52ed7`
- Fix commit (bug absent): `fdabd424e237f89d8b3f53cf8157902bbf850e45`
- Changed source paths: src/blib2to3/pgen2/tokenize.py
