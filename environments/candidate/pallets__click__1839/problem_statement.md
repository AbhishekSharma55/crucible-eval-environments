# pallets/click#1839

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #1838 — https://github.com/pallets/click/issues/1838

In [_termui_impl.py](https://github.com/pallets/click/blob/972becff259e4ffcd220a6cad5096f36a89fdd6d/src/click/_termui_impl.py#L556) `urllib.unquote()` is called. But [urllib](https://docs.python.org/3/library/urllib.html) is a package now. Equivalent functionality is available in the urllib.parse module.

## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/click`
- Pull request: https://github.com/pallets/click/pull/1839
- Pull request title: update urllib unquote import
- Merged at: 2021-04-08T14:19:44Z
- Parent commit (bug present): `972becff259e4ffcd220a6cad5096f36a89fdd6d`
- Fix commit (bug absent): `3f7319081113a0bdfa8fa0b8c4ff018a8f5e5278`
- Changed source paths: src/click/_termui_impl.py
