# pallets/click#1937

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #1936 — https://github.com/pallets/click/issues/1936

<!--
This issue tracker is a tool to address bugs in Click itself. Please use
Pallets Discord or Stack Overflow for questions about your own code.

Replace this comment with a clear outline of what the bug is.
-->

<!--
Describe how to replicate the bug.

Include a minimal reproducible example that demonstrates the bug.
Include the full traceback if there was an exception.
-->

When running completion example, try to do completion with completion `group select-user` and it will produce the following error.

```
completion group select-user bTraceback (most recent call last):      
  File "/Users/thomas/.pyenv/versions/3.8.5/bin/completion", line 11, in <module>
    load_entry_point('click-example-completion', 'console_scripts', 'completion')()
  File "/Users/thomas/.pyenv/versions/3.8.5/lib/python3.8/site-packages/click/core.py", line 1137, in __call__
    return self.main(*args, **kwargs)
  File "/Users/thomas/.pyenv/versions/3.8.5/lib/python3.8/site-packages/click/core.py", line 1057, in main
    self._main_shell_completion(extra, prog_name, complete_var)
  File "/Users/thomas/.pyenv/versions/3.8.5/lib/python3.8/site-packages/click/core.py", line 1132, in _main_shell_completion
    rv = shell_complete(self, ctx_args, prog_name, complete_var, instruction)
  File "/Users/thomas/.pyenv/versions/3.8.5/lib/python3.8/site-packages/click/shell_completion.py", line 49, in shell_complete
    echo(comp.complete())
  File "/Users/thomas/.pyenv/versions/3.8.5/lib/python3.8/site-packages/click/shell_completion.py", line 291, in complete
    completions = self.get_completions(args, incomplete)
  File "/Users/thomas/.pyenv/versions/3.8.5/lib/python3.8/site-packages/click/shell_completion.py", line 273, in get_completions
    return obj.shell_complete(ctx, incomplete)
  File "/Users/thomas/.pyenv/versions/3.8.5/lib/python3.8/site-packages/click/core.py", line 2403, in shell_complete
    if results and isinstance(results[0], str):
TypeError: 'generator' object is not subscriptable
```

<!--
Describe the expected behavior that should have happened but didn't.
-->

Environment:

- Python version:
- Click version:


## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/click`
- Pull request: https://github.com/pallets/click/pull/1937
- Pull request title: fix completion example
- Merged at: 2021-05-27T14:42:16Z
- Parent commit (bug present): `1517c6b13d789d216d6f8f00656652a3881ee4ca`
- Fix commit (bug absent): `ba578d7ae304d6e1ff57ab5874d72e34572129c1`
- Changed source paths: examples/completion/completion.py
