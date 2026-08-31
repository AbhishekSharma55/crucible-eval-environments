# marshmallow-code/marshmallow#1843

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #1837 — https://github.com/marshmallow-code/marshmallow/issues/1837

#1631 broke this . How to fix it easily if i have schema like:

```
from marshmallow import Schema, fields

class Ischema(Schema):
    name = fields.Str()
    load = fields.Number()
    
ss = Ischema()
ss.loads('{"name":"w","load":1}')
Traceback (most recent call last):
  File "<input>", line 1, in <module>
  File "/usr/local/lib/python3.8/site-packages/marshmallow/schema.py", line 748, in loads
    return self.load(data, many=many, partial=partial, unknown=unknown)
TypeError: 'Number' object is not callable
```

## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `marshmallow-code/marshmallow`
- Pull request: https://github.com/marshmallow-code/marshmallow/pull/1843
- Pull request title: Fix: Don't expose Schema fields by name as class/instance attributes
- Merged at: 2021-07-06T20:43:32Z
- Parent commit (bug present): `38b1dddc9e25f820316c8ef8468c77a33092ea2b`
- Fix commit (bug absent): `af9c3d5c9a325750e22161067426fc021472238c`
- Changed source paths: src/marshmallow/schema.py
