# pallets/click#1737

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #1736 — https://github.com/pallets/click/issues/1736

Since Python 3.3, the stdlib provides the function `shutil.get_terminal_size()`. Now that the project has dropped Python 2
support, the compatibility shim is no longer necessary.

The stdlib version returns a named tuple. So rather than indexing "0", can use the more self-documenting attribute "columns".

Docs available at: https://docs.python.org/3/library/shutil.html#shutil.get_terminal_size


## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/click`
- Pull request: https://github.com/pallets/click/pull/1737
- Pull request title: Deprecate click.get_terminal_size() in favor of stdlib shutil.
- Merged at: 2021-02-15T20:49:09Z
- Parent commit (bug present): `b28bc4c6439d7b01c011e72c09d80574fe75b85b`
- Fix commit (bug absent): `4f17161652d67f88deedd6b193dd320f69021539`
- Changed source paths: src/click/_compat.py, src/click/_termui_impl.py, src/click/formatting.py, src/click/termui.py
