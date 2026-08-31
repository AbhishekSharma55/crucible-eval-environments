# marshmallow-code/marshmallow#1903

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #1902 — https://github.com/marshmallow-code/marshmallow/issues/1902

```
DeprecationWarning: The distutils package is deprecated and slated for removal in Python 3.12. 
Use setuptools or check PEP 632 for potential alternatives
```
https://github.com/marshmallow-code/marshmallow/blob/35225039900be03536cfde7abf121d11066e3183/src/marshmallow/__init__.py#L14

Environment:
- CPython 3.10.0
- marshmallow 3.14.0

## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `marshmallow-code/marshmallow`
- Pull request: https://github.com/marshmallow-code/marshmallow/pull/1903
- Pull request title: fix: distutils deprecation warning in Python 3.10
- Merged at: 2021-11-15T04:16:32Z
- Parent commit (bug present): `41afdefd93afd1b95f48f45fd284ff8add3e91b7`
- Fix commit (bug absent): `a63c28edde1e3f1f522aab8a7de231230786ebc1`
- Changed source paths: setup.py, src/marshmallow/__init__.py
