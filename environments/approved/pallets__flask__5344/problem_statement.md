# pallets/flask#5344

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #5342 — https://github.com/pallets/flask/issues/5342

https://github.com/pallets/flask/blob/d61198941adcb191ddb591f08d7d912e40bde8bc/src/flask/cli.py#L798

There is no double quote in the first argument of `click.BadParameter` `"--key is not used`.

## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/flask`
- Pull request: https://github.com/pallets/flask/pull/5344
- Pull request title: fix missing quote in `--key` error message
- Merged at: 2023-12-13T23:06:37Z
- Parent commit (bug present): `b97165db75c6f4e99c3307b4a5a1f3b0d9f4de25`
- Fix commit (bug absent): `05eebe36abe923d065133792f14d4ab6c07336a0`
- Changed source paths: src/flask/cli.py
