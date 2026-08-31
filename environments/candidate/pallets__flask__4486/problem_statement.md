# pallets/flask#4486

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #4485 — https://github.com/pallets/flask/issues/4485

When the session modified such that it ends up empty, the session cookie is deleted by sending an expired cookie. This 'deletion cookie' is missing the HttpOnly flag. The bug is [in the call to delete_cookie](https://github.com/pallets/flask/blob/b655a9db30d8e78d2fe1044d6301a432f214a16b/src/flask/sessions.py#L392), which is missing the httponly kwarg. 

```
from flask import Flask, session

app = Flask(__name__)
app.secret_key = "whatever"
app.config['SESSION_COOKIE_HTTPONLY'] = True # the default

@app.route('/')
def index():
    session['foo'] = 1  # sets session.modified
    session.pop('foo')  # afterwards, the session is empty again
    return ""

app.run()
```

expected behavior: the HttpOnly flag should be present on the 'deletion cookie'.

Environment:

- Python version: 3.10.2
- Flask version: 2.0.3


## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/flask`
- Pull request: https://github.com/pallets/flask/pull/4486
- Pull request title: Preserve HttpOnly flag when deleting session cookie
- Merged at: 2022-03-15T13:38:35Z
- Parent commit (bug present): `b655a9db30d8e78d2fe1044d6301a432f214a16b`
- Fix commit (bug absent): `0ef1e65f6ab0da680d171d49e1a56a2b0ecee05d`
- Changed source paths: src/flask/sessions.py
