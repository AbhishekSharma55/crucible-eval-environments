# marshmallow-code/marshmallow#1631

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #1628 — https://github.com/marshmallow-code/marshmallow/issues/1628

I see at `_get_fields` function there is a `pop` parameter that defines what to do with field attributes of schema class:
https://github.com/marshmallow-code/marshmallow/blob/09c5b26bee77be5e23927ddeb472d5ea56733266/src/marshmallow/schema.py#L54-L56
There is also `ordered` parameter here but unlike him `pop` parameter isn't accessible through the API. I think it would be nice to have the corresponding meta parameter that control schema class fields deletion.

## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `marshmallow-code/marshmallow`
- Pull request: https://github.com/marshmallow-code/marshmallow/pull/1631
- Pull request title: Rework Schema._get_fields
- Merged at: 2021-04-09T06:30:51Z
- Parent commit (bug present): `26d2679aa13ce38109881bd2c983dd6fc9e0b889`
- Fix commit (bug absent): `670ae33e7fa4cb5e205f4d905c64ac9d557421f0`
- Changed source paths: src/marshmallow/schema.py
