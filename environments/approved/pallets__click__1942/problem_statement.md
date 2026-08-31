# pallets/click#1942

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #1940 — https://github.com/pallets/click/issues/1940

I have a machine where the system locale is set to `de_DE.UTF-8`. The output of `bash --version` here is:
~~~
GNU bash, Version 5.1.4(1)-release (x86_64-pc-linux-gnu)
Copyright (C) 2020 Free Software Foundation, Inc.
Lizenz GPLv3+: GNU GPL Version 3 oder jünger <http://gnu.org/licenses/gpl.html>

Dies ist freie Software. Sie darf verändert und verteilt werden.
Es wird keine Garantie gewährt, soweit das Gesetz es zulässt.
~~~

This causes clicks shell completion activation to die with an exception because of the capitalized `V` in `Version`:
~~~
Traceback (most recent call last):
  File "/home/losinski/.local/bin/template-test", line 8, in <module>
    sys.exit(main())
  File "/home/losinski/.local/lib/python3.9/site-packages/click/core.py", line 1137, in __call__
    return self.main(*args, **kwargs)
  File "/home/losinski/.local/lib/python3.9/site-packages/click/core.py", line 1057, in main
    self._main_shell_completion(extra, prog_name, complete_var)
  File "/home/losinski/.local/lib/python3.9/site-packages/click/core.py", line 1132, in _main_shell_completion
    rv = shell_complete(self, ctx_args, prog_name, complete_var, instruction)
  File "/home/losinski/.local/lib/python3.9/site-packages/click/shell_completion.py", line 45, in shell_complete
    echo(comp.source())
  File "/home/losinski/.local/lib/python3.9/site-packages/click/shell_completion.py", line 324, in source
    self._check_version()
  File "/home/losinski/.local/lib/python3.9/site-packages/click/shell_completion.py", line 319, in _check_version
    raise RuntimeError(
RuntimeError: Couldn't detect Bash version, shell completion is not supported.
~~~

A quickfix would be to set `LANG=C` as environment on the `bash --version` call here: https://github.com/pallets/click/blob/main/src/click/shell_completion.py#L305. Another option would be
~~~
bash -c 'echo ${BASH_VERSION}'
5.1.4(1)-release
~~~


Environment:

- Python version: 3.9.2
- Click version: 8.0.1


## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/click`
- Pull request: https://github.com/pallets/click/pull/1942
- Pull request title: bash version detection is locale independent
- Merged at: 2021-07-03T14:03:38Z
- Parent commit (bug present): `3d0d8b5af1abc30a59fc0f1bec3a0e95d61a4101`
- Fix commit (bug absent): `976d25bf2a664f066b43296862285a2e8214abd0`
- Changed source paths: src/click/shell_completion.py
