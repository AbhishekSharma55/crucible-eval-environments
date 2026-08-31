# pallets/click#1794

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #1773 — https://github.com/pallets/click/issues/1773

<!--
This issue tracker is a tool to address bugs in Click itself.
Please use the #pocoo IRC channel on freenode, the Discord server or
Stack Overflow for general questions about using Flask or issues
not related to Click.

If you'd like to report a bug in Click, fill out the template below. Provide
any extra information that may be useful / related to your problem.
Ideally, create an [MCVE](https://stackoverflow.com/help/mcve), which helps us
understand the problem and helps check that it is not caused by something in
your code.
-->

I did not encounter a problem due to this, but I found inconsistencies in the code.

### Actual Behavior

The tuple yielded by the `CliRunner.isolation()` contextmanager is incompatible with the 
usage in the `CliRunner.invoke()` method.
In the latter, a `BytesIO` object is assumed, while the actual return value is a boolean (literal).

https://github.com/pallets/click/blob/fbe33bac440d0edef50fc980fb638d2dbbf96b5e/src/click/testing.py#L265


https://github.com/pallets/click/blob/fbe33bac440d0edef50fc980fb638d2dbbf96b5e/src/click/testing.py#L370

I guess the intent was to only return the BytesIO when `self.mix_stderr` is True,
So I'd rather bind bytes_error as None before and just pass it 

```python
bytes_error = None
if self.mix_stderr:
    sys.stderr = sys.stdout
else:
    bytes_error = io.BytesIO()
    ...
...
yield (bytes_output, bytes_error)
```
But I'm unsure of what is expected behaviour here, otherwise I would simply fix it.

```
### Environment
* Click version: 7.0


## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/click`
- Pull request: https://github.com/pallets/click/pull/1794
- Pull request title: CliRunner.isolation() returns type compatible with CliRunner.invoke()
- Merged at: 2021-02-25T18:44:24Z
- Parent commit (bug present): `1b1578dbbc706538914221352edc84d532cdd3a4`
- Fix commit (bug absent): `c76fea1696c0ffe7edff8a36cadd4686cda8cbfb`
- Changed source paths: src/click/testing.py
