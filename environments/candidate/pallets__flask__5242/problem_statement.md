# pallets/flask#5242

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #5230 — https://github.com/pallets/flask/issues/5230

The `__version__` attribute is an old pattern from early in Python packaging. Setuptools eventually made it easier to use the pattern by allowing reading the value from the attribute at build time, and some other build backends have done the same.

However, there's no reason to expose this directly in code anymore. It's usually easier to use feature detection (`hasattr`, `try/except`) instead. `importlib.metadata.version("werkzeug")` can be used to get the version at runtime in a standard way, if it's really needed.

## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/flask`
- Pull request: https://github.com/pallets/flask/pull/5242
- Pull request title: deprecate `__version__` attribute
- Merged at: 2023-08-29T13:09:59Z
- Parent commit (bug present): `153433f612585409f3494a3c44160d888c02612d`
- Fix commit (bug absent): `faef9a0fcef307f1a1c380a477b392fa4371d83d`
- Changed source paths: src/flask/__init__.py
