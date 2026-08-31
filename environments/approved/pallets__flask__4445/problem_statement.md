# pallets/flask#4445

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #3396 — https://github.com/pallets/flask/issues/3396

I'm trying to add default headers to Flask's test client requests by overriding `FlaskClient.open`. When following redirects, the second request raises an error that an `EnvironBuilder` instance is being passed to `url_parse`.

### Expected Behavior

```python
from flask import Flask, redirect, url_for
from flask.testing import FlaskClient

app = Flask(__name__)

class CustomClient(FlaskClient):
    def open(self, *args, **kwargs):
        kwargs["headers"] = {"Extra-Key": "extra value"}
        return super().open(*args, **kwargs)

@app.route("/")
def home():
    return redirect(url_for("test"))

@app.route("/test")
def test():
    return "Hello, World!"

app.test_client_class = CustomClient
c = app.test_client()
rv = c.get("/", follow_redirects=True)
print(rv.data)
```

### Actual Behavior
```pytb
Traceback (most recent call last):
  File "/home/david/Projects/flask/example.py", line 21, in <module>
    rv = c.get("/", follow_redirects=True)
  File "/home/david/.virtualenvs/flask/lib/python3.8/site-packages/werkzeug/test.py", line 1029, in get
    return self.open(*args, **kw)
  File "/home/david/Projects/flask/example.py", line 9, in open
    return super().open(*args, **kwargs)
  File "/home/david/Projects/flask/src/flask/testing.py", line 222, in open
    return Client.open(
  File "/home/david/.virtualenvs/flask/lib/python3.8/site-packages/werkzeug/test.py", line 1016, in open
    environ, response = self.resolve_redirect(
  File "/home/david/.virtualenvs/flask/lib/python3.8/site-packages/werkzeug/test.py", line 948, in resolve_redirect
    return self.open(builder, as_tuple=True, buffered=buffered)
  File "/home/david/Projects/flask/example.py", line 9, in open
    return super().open(*args, **kwargs)
  File "/home/david/Projects/flask/src/flask/testing.py", line 215, in open
    builder = EnvironBuilder(self.application, *args, **kwargs)
  File "/home/david/Projects/flask/src/flask/testing.py", line 73, in __init__
    url = url_parse(path)
  File "/home/david/.virtualenvs/flask/lib/python3.8/site-packages/werkzeug/urls.py", line 457, in url_parse
    i = url.find(s(":"))
AttributeError: 'EnvironBuilder' object has no attribute 'find'
```
### Environment

* Python version: 3.6.9
* Flask version: 1.1.1
* Werkzeug version: 0.16.0


## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/flask`
- Pull request: https://github.com/pallets/flask/pull/4445
- Pull request title: overriding FlaskClient.open works with redirects
- Merged at: 2022-02-09T19:39:48Z
- Parent commit (bug present): `7c5f17a55e8cd233db17f4944a482cc497a6e7c6`
- Fix commit (bug absent): `e06dad62f6b49dff935f241114b3590774e2786a`
- Changed source paths: src/flask/testing.py
