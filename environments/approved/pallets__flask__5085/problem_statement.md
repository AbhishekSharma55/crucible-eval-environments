# pallets/flask#5085

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #5084 — https://github.com/pallets/flask/issues/5084

`from flask import Markup` and `flask.Markup` both don’t work. This is merely supposed to be deprecated, not broken, in Flask 2.3.0.

Example A:
```python
import flask

print(flask.Markup('hi'))
```
```
Traceback (most recent call last):
  File "/tmp/flask230/1.py", line 3, in <module>
    print(flask.Markup('hi'))
  File "/tmp/flask230/venv/lib/python3.10/site-packages/flask/__init__.py", line 102, in __getattr__
    raise AttributeError(name)
AttributeError: Markup
```

Example B:
```python
from flask import Markup

print(Markup('hi'))
```
```
Traceback (most recent call last):
  File "/tmp/flask230/2.py", line 1, in <module>
    from flask import Markup
ImportError: cannot import name 'Markup' from 'flask' (/tmp/flask230/venv/lib/python3.10/site-packages/flask/__init__.py)
```

Environment:

- Python version: 3.10.10
- Flask version: 2.3.0

## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/flask`
- Pull request: https://github.com/pallets/flask/pull/5085
- Pull request title: Fix importing Markup from flask
- Merged at: 2023-04-25T20:06:22Z
- Parent commit (bug present): `345f18442ceb29f9e365af99fc85bdc5986323d2`
- Fix commit (bug absent): `0867dce42c1a193bfe7fb5f92f0ccaa622643f48`
- Changed source paths: src/flask/__init__.py
