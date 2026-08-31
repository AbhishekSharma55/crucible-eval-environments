# pallets/click#2944

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #2943 — https://github.com/pallets/click/issues/2943

Programs such as BusyBox, Toybox and Coreutils (also gzib, bzip etc) in multi-call mode derive their identity from the symlink. Resolving the symlink causes them to misbehave.

Environment:

- Python version: python3.12
- Click version: 8.2.1


## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/click`
- Pull request: https://github.com/pallets/click/pull/2944
- Pull request title: Fix _pipepager()/_tempfilepage() to work with multi-call binaries
- Merged at: 2025-10-02T05:54:15Z
- Parent commit (bug present): `413f76f37dcdb2c475a800870d3f8c1c623238d6`
- Fix commit (bug absent): `5f86603a84e12bdec1584c15c9f982740e613c45`
- Changed source paths: src/click/_termui_impl.py
