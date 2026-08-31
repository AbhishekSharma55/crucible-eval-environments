# pallets/flask#4742

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #4740 — https://github.com/pallets/flask/issues/4740

Previously, if `FLASK_ENV` was not set, it would default to `"production"`, now it defaults to `"development"`.

Reproduction:

```python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello_world():
    print(f"{app.config.get('ENV')=}")
    return "<p>Hello, World!</p>"
```

Run using gunicorn, `gunicorn flask_demo.app:app` with `FLASK_ENV` unset,

Flask 2.2.1, this handler prints:
`app.config.get('ENV')='development'`

downgrade to 2.1.0:
`app.config.get('ENV')='production'`

I assume this due to  #4720, `src/flask/app.py:693`

Environment:

- Python version: 3.10.4
- Flask version: 2.2.1

## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/flask`
- Pull request: https://github.com/pallets/flask/pull/4742
- Pull request title: fix default value of app.env
- Merged at: 2022-08-04T14:27:50Z
- Parent commit (bug present): `4984753dbf5a247f46e2903011c981d0709973ff`
- Fix commit (bug absent): `45b2c99c1f6a884376d54bbb25223edad65596c5`
- Changed source paths: src/flask/app.py
