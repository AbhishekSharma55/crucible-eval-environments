# pallets/click#1801

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #805 — https://github.com/pallets/click/issues/805

I'd love to see strike-through support for [`style`](http://click.pocoo.org/5/api/#click.style). AFAIK, most modern terminals support this.

From what I understand, this is "code number 9", and can be tested via `echo -e "\e[9mtest\e[0m"`.

## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `pallets/click`
- Pull request: https://github.com/pallets/click/pull/1801
- Pull request title: Added strikethrough support for style
- Merged at: 2021-03-02T16:48:55Z
- Parent commit (bug present): `6f705ddc21ede17c3427a8f624537a8ce5586701`
- Fix commit (bug absent): `81bddecfd32fda82fc8421cd316e55a2db8575d1`
- Changed source paths: src/click/termui.py
