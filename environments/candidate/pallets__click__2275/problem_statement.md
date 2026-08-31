# pallets/click#2275

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #2166 — https://github.com/pallets/click/issues/2166

I found out, that a shell completion doesn't work on scripts with a dot in their name, mainly the scripts themselves (without an entry point linked) or entry points with a dot in their name (less common). The main problem is that the dot is copied into the name of the completion variable.

MWE:
Let's have a script `/tmp/example.py`
```python
import click


@click.command()
def main():
    pass


if __name__ == '__main__':
    main()
```

Completion on this script doesn't do anything using any of reasonable variable names:
```sh
_EXAMPLE_COMPLETE=bash_source python3 /tmp/example.py
_EXAMPLEPY_COMPLETE=bash_source python3 /tmp/example.py
_EXAMPLE_PY_COMPLETE=bash_source python3 /tmp/example.py
```

I found out, click requires the variable `_EXAMPLE.PY_COMPLETE` to be set, which is not possible (at least) in bash.

It would help if the dot was replaced by an underscore, the same way a dash is handled.

Environment:

- Python version: 3.9.9
- Click version: 8.0.3


## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/click`
- Pull request: https://github.com/pallets/click/pull/2275
- Pull request title: Normalize dots in script names
- Merged at: 2023-06-30T00:34:42Z
- Parent commit (bug present): `bdb81e4693c3ca79ab85149964022933235234bf`
- Fix commit (bug absent): `6c3a1fcc19963bcc9422bf98f1c56108193ab232`
- Changed source paths: src/click/core.py
