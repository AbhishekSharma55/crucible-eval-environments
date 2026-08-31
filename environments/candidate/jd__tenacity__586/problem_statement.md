# jd/tenacity#586

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #554 — https://github.com/jd/tenacity/issues/554

After upgrading Tenacity, mypy reports errors like:

```
error: Argument 1 to "before_sleep_log" has incompatible type "Logger"; expected "LoggerProtocol"  [arg-type]
```

I'm using the normal Python logging logger. 
This should already reproduce the error:
```python
  import logging
  from tenacity.before_sleep import before_sleep_log

  log = logging.getLogger(__name__)
  before_sleep_log(log, logging.INFO)  # mypy arg-type error
```

## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `jd/tenacity`
- Pull request: https://github.com/jd/tenacity/pull/586
- Pull request title: fix: make LoggerProtocol compatible with logging.Logger
- Merged at: 2026-02-19T09:49:00Z
- Parent commit (bug present): `89c5735a81d291eb2fc019e37f13a81dfe763bcf`
- Fix commit (bug absent): `773f4386e596f52d5c5ed39a8f511c7b56936986`
- Changed source paths: tenacity/_utils.py
