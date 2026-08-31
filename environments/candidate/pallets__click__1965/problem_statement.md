# pallets/click#1965

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #1959 — https://github.com/pallets/click/issues/1959

The following lines cause a `TypeError` if one provide `help=None`:

https://github.com/pallets/click/blob/8b48450d5d63c747600e069d4c3e2274f41c8360/src/click/decorators.py#L244-L245

By the way, why is `cleandoc` called by the decorator and not by `Option` itself? The docstring says "all keyword arguments are forwarded unchanged (except ``cls``)".

The same problem appears when passing `cls=None` (also with `@argument`):

https://github.com/pallets/click/blob/8b48450d5d63c747600e069d4c3e2274f41c8360/src/click/decorators.py#L246-L247

I encountered this problem while writing a wrapper for the above decorators that explicitly list arguments for a better IDE support.

## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/click`
- Pull request: https://github.com/pallets/click/pull/1965
- Pull request title: Across the codebase, handle the case a keyword argument is provided but set to `None`
- Merged at: 2022-02-20T17:00:13Z
- Parent commit (bug present): `166b31261f55ba3126456bbc2ff9e16142115e56`
- Fix commit (bug absent): `c9c406bebdf2b027864216fb881278a8bfa14bb8`
- Changed source paths: src/click/core.py, src/click/decorators.py
