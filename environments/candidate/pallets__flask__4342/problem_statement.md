# pallets/flask#4342

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #3898 — https://github.com/pallets/flask/issues/3898

`g` has been stored on `AppContext` since AppContext's introduction in 0.9. We still have a property `g` attached on `RequestContext`. Is there any reason to keep it? Why not switch to `current_app.g`, or just the global `g`?

https://github.com/laggardkernel/flask/commit/a10005bb0d7668d81c64c02051366035ee421367

### Environment

* Python version: 3.8.7
* Flask version: 1.1.2
* Werkzeug version: 1.0.1


## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/flask`
- Pull request: https://github.com/pallets/flask/pull/4342
- Pull request title: deprecate `RequestContext.g`
- Merged at: 2021-11-16T15:38:42Z
- Parent commit (bug present): `04c6a85518c600fc34705dee30dd17c188ef1aaa`
- Fix commit (bug absent): `9486b6cf57bd6a8a261f67091aca8ca78eeec1e3`
- Changed source paths: src/flask/ctx.py
