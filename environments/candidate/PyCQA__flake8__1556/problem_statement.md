# PyCQA/flake8#1556

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #1554 — https://github.com/PyCQA/flake8/issues/1554

### how did you install flake8?

```console
$ pip install flake8==4.0.1
```


### unmodified output of `flake8 --bug-report`

```json
{
  "dependencies": [],
  "platform": {
    "python_implementation": "CPython",
    "python_version": "3.9.7",
    "system": "Linux"
  },
  "plugins": [
    {
      "is_local": false,
      "plugin": "mccabe",
      "version": "0.6.1"
    },
    {
      "is_local": false,
      "plugin": "pycodestyle",
      "version": "2.8.0"
    },
    {
      "is_local": false,
      "plugin": "pyflakes",
      "version": "2.4.0"
    }
  ],
  "version": "4.0.1"
}
```


### describe the problem

When running `flake8 --help`, the `--count` options is described as:
```
  --count               Print total number of errors and warnings to standard error and set the exit code to 1 if total is not empty.
```


The count is printed to `stdout`, not `stderr`, according to the [documentation](https://flake8.pycqa.org/en/latest/user/options.html#cmdoption-flake8-count), this [issue](https://github.com/PyCQA/flake8/issues/455), and my own experience.

## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `PyCQA/flake8`
- Pull request: https://github.com/PyCQA/flake8/pull/1556
- Pull request title: Clarify that `--count` writes to standard output
- Merged at: 2022-02-10T14:36:07Z
- Parent commit (bug present): `62ce3e491860aa34cfd3438715ade74a8a45bfac`
- Fix commit (bug absent): `95028ff250a6cef028e7e4b514263bc221e42802`
- Changed source paths: src/flake8/main/options.py
