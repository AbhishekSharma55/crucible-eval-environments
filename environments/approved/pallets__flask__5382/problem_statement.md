# pallets/flask#5382

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #5381 — https://github.com/pallets/flask/issues/5381

Providers such as `orjson` and `ujson` do not implement `object_hook`. The "tagged JSON" scheme used to encode types for session data currently calls `loads(data, object_hook=...)`, so providers that ignore that option return the data still tagged. Untagging needs to be implemented without using `object_hook`.

## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/flask`
- Pull request: https://github.com/pallets/flask/pull/5382
- Pull request title: untag without `object_hook`
- Merged at: 2024-01-15T15:52:35Z
- Parent commit (bug present): `c275573147b426fbe1a37c6bce143f7895b603b2`
- Fix commit (bug absent): `5a48a0fe6b02f62f9a0d90257c6a14d280bc9d23`
- Changed source paths: src/flask/json/tag.py
