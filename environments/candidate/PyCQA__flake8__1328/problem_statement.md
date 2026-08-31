# PyCQA/flake8#1328

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #1327 — https://github.com/PyCQA/flake8/issues/1327

Since PyCQA/pycodestyle#970, the E111 rule does not show the indent size when using pycodestyle through flake8. Whereas the check first printed `E111 indentation is not a multiple of four`, it now prints `E111 indentation is not a multiple of  `. This does seem to happen because flake8 overwrites the `indent_size_str` variable [here](https://github.com/PyCQA/flake8/blob/3.9.1/src/flake8/processor.py#L89). 

## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `PyCQA/flake8`
- Pull request: https://github.com/PyCQA/flake8/pull/1328
- Pull request title: correct and deprecate the value of indent_size_str
- Merged at: 2021-05-08T19:11:38Z
- Parent commit (bug present): `84c95766e679710d9a0fa910a1cd276c87be42c5`
- Fix commit (bug absent): `7231422eb767f0c3ed41a23f5e3dd4f903293168`
- Changed source paths: src/flake8/processor.py
