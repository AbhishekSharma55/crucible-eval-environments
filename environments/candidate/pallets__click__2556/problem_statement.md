# pallets/click#2556

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #2336 — https://github.com/pallets/click/issues/2336

setting `expose_value=false` for an argument causes crash when auto-completing.

To replicate:

```python
# example.py
import click

@click.command
@click.argument('a', expose_value=False)
def main():
    pass

main()
```

```
$ _EXAMPLE_PY_COMPLETE=zsh_complete COMP_CWORD=1 COMP_WORDS="BUG " python example.py BUG
```

you should get something like the following
``` bash
  File "/home/amir/projects/click/bug", line 13, in <module>
    gogo()
  File "/home/amir/projects/click/src/click/core.py", line 1130, in __call__
    return self.main(*args, **kwargs)
  File "/home/amir/projects/click/src/click/core.py", line 1050, in main
    self._main_shell_completion(extra, prog_name, complete_var)
  File "/home/amir/projects/click/src/click/core.py", line 1125, in _main_shell_completion
    rv = shell_complete(self, ctx_args, prog_name, complete_var, instruction)
  File "/home/amir/projects/click/src/click/shell_completion.py", line 49, in shell_complete
    echo(comp.complete())
  File "/home/amir/projects/click/src/click/shell_completion.py", line 291, in complete
    completions = self.get_completions(args, incomplete)
  File "/home/amir/projects/click/src/click/shell_completion.py", line 272, in get_completions
    obj, incomplete = _resolve_incomplete(ctx, args, incomplete)
  File "/home/amir/projects/click/src/click/shell_completion.py", line 575, in _resolve_incomplete
    if _is_incomplete_argument(ctx, param):
  File "/home/amir/projects/click/src/click/shell_completion.py", line 439, in _is_incomplete_argument
    value = ctx.params[param.name]
KeyError: 'a'
```

I think the correct behavior is that nothing should happen or some thing should be printed to stdout. but it shouldn't crash

Environment:

- Python version: 3.10
- Click version: main

## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/click`
- Pull request: https://github.com/pallets/click/pull/2556
- Pull request title: completion doesn't fail with `expose_value=False`
- Merged at: 2023-07-06T18:14:09Z
- Parent commit (bug present): `549947111c4af2191dd4b245e1de2c25d20c36d6`
- Fix commit (bug absent): `b67fe5f70a8c88bf54d6c7058b1154a81d32815c`
- Changed source paths: src/click/shell_completion.py
