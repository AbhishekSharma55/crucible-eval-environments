# pallets/flask#4735

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #4732 — https://github.com/pallets/flask/issues/4732

<!--
This issue tracker is a tool to address bugs in Flask itself. Please use
Pallets Discord or Stack Overflow for questions about your own code.

Replace this comment with a clear outline of what the bug is.

-->

**Describe how to replicate the bug.**

```
self.db = MongoEngine(app)
  File "/Users/rahulm/PycharmProjects/Management-OLO/venv/lib/python3.9/site-packages/flask_mongoengine/__init__.py", line 102, in __init__
    self.init_app(app, config)
  File "/Users/rahulm/PycharmProjects/Management-OLO/venv/lib/python3.9/site-packages/flask_mongoengine/__init__.py", line 113, in init_app
    override_json_encoder(app)
  File "/Users/rahulm/PycharmProjects/Management-OLO/venv/lib/python3.9/site-packages/flask_mongoengine/json.py", line 38, in override_json_encoder
    app.json_encoder = _make_encoder(app.json_encoder)
  File "/Users/rahulm/PycharmProjects/Management-OLO/venv/lib/python3.9/site-packages/flask_mongoengine/json.py", line 8, in _make_encoder
    class MongoEngineJSONEncoder(superclass):
TypeError: NoneType takes no arguments
```

**Describe the expected behavior that should have happened but didn't.**

Should not throw any error while running flask
Environment: MAC M1

- Python version:3.9
- Flask version:2.2.0


### Issue #4733 — https://github.com/pallets/flask/issues/4733

All JSON-related changes in [CHANGES.rst](https://github.com/pallets/flask/blob/main/CHANGES.rst) point to a seemingly random issue #4688. I guess these changes should point to some other PR(s), possibly #4692



Environment:

- Python version: N/A
- Flask version: 2.2.0


## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/flask`
- Pull request: https://github.com/pallets/flask/pull/4735
- Pull request title: show deprecation warning when using json_encoder/decoder
- Merged at: 2022-08-03T17:02:18Z
- Parent commit (bug present): `9a1b25fce4ddd553d7cba01bab3df5841a24aeff`
- Fix commit (bug absent): `723a3a6ffdb2c84eb7883d0852ec7d41fed751c0`
- Changed source paths: src/flask/app.py, src/flask/blueprints.py, src/flask/json/provider.py, src/flask/scaffold.py
