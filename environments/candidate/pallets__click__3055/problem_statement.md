# pallets/click#3055

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #3039 — https://github.com/pallets/click/issues/3039

In https://github.com/pallets/click/commit/299efb82e1a3d34d870129dc0c677c6efb42d811 a `Popen()` for the pager changed the command argument (the first argument) from a string to a list.

If changing the command to a sequence, we should also change `shell=True` to `shell=False` (or remove it).

Per the `subprocess` docs at

 * https://docs.python.org/3/library/subprocess.html#popen-constructor

> On POSIX with `shell=True` … If _args_ is a sequence, the first item specifies the command string, and any additional items will be treated as additional arguments to the shell itself. That is to say, Popen does the equivalent of:
> `Popen(['/bin/sh', '-c', args[0], args[1], ...])`

Whereas if `shell=False` the effect is simply "`os.execvpe()`-like behavior" to execute `args[0]` directly with `args[1:]` as its arguments.

This bug is causing failures in the test suite for https://github.com/dbcli/mycli, and we are stuck on click < 8.1.8 as a result.

I don't have a prepared failure case using click other than the mycli test suite, but one example of strange behavior you can replicate easily is that `sh` will swallow arguments that you might think go to the command.  For example:

```bash
sh -c ls --nonsense
```

will work, because `ls` never sees `--nonsense`.

Environment:

- Python version: tested on Python versions 3.9-3.13
- Click version: 8.1.8+


## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/click`
- Pull request: https://github.com/pallets/click/pull/3055
- Pull request title: `Popen()` list-argument pager process without shell=True
- Merged at: 2025-09-24T02:54:10Z
- Parent commit (bug present): `35e6a78646c58a8cc1ba3cda603a6bd4fb87f9d5`
- Fix commit (bug absent): `7d7183604158f064390539d83d4a19a978c6b08a`
- Changed source paths: src/click/_termui_impl.py
