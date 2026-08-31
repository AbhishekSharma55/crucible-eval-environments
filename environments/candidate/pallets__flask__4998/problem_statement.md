# pallets/flask#4998

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #4993 — https://github.com/pallets/flask/issues/4993

`locked_cached_property` is a modification of `cached_property` that acquires a lock before interacting with its data. Due to the way descriptors work, even though the property is "cached", each access still invokes the descriptor's `__get__` method and acquires the lock. Therefore, when using thread-like workers that share the lock, requests can block each other. These blocks should be very brief, as they're only immediately returning the cached property, but it's still inefficient.

It is currently applied to `app.jinja_env`, `app.logger`, `app.name`, `app.jinja_loader`, and `blueprint.jinja_loader`. I'm not entirely sure we need locks on them at all, but just in case we could use locks within the methods.

## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/flask`
- Pull request: https://github.com/pallets/flask/pull/4998
- Pull request title: deprecate `locked_cached_property`
- Merged at: 2023-02-23T18:59:28Z
- Parent commit (bug present): `c690f529f28a8fd7ecdac90939944475613760a5`
- Fix commit (bug absent): `4c288bc97ea371817199908d0d9b12de9dae327e`
- Changed source paths: src/flask/app.py, src/flask/helpers.py, src/flask/scaffold.py
