# marshmallow-code/marshmallow#2153

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #2152 — https://github.com/marshmallow-code/marshmallow/issues/2152

As you can see in the title, my CI just broke:
```
/env/lib/python3.11/site-packages/marshmallow_sqlalchemy/schema.py:143: in <module>
    class SQLAlchemySchema(
/env/lib/python3.11/site-packages/marshmallow/schema.py:116: in __new__
    klass._declared_fields = mcs.get_declared_fields(
E   TypeError: SQLAlchemySchemaMeta.get_declared_fields() missing 1 required positional argument: 'dict_cls'
```
Possibly an issue on their end more than yours, but someone had to report it somewhere. :-)

## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `marshmallow-code/marshmallow`
- Pull request: https://github.com/marshmallow-code/marshmallow/pull/2153
- Pull request title: Fix call to get_declared_fields: pass dict_cls
- Merged at: 2023-07-20T22:01:56Z
- Parent commit (bug present): `3d929956b9b841d8039d5f431fb1110b3ba3e14e`
- Fix commit (bug absent): `fc65bc209b876e730ccd42a67877dbf709bffe3b`
- Changed source paths: src/marshmallow/schema.py
