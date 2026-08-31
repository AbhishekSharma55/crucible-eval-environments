Author a missing regression test for this case.

Case: {{CASE_ID}}
Repository: {{REPO}}
Broken parent: {{PARENT_SHA}}
Fixed commit: {{FIX_SHA}}

Linked issues:
{{ISSUES}}

Pull request title:
{{PR_TITLE}}

Pull request body:
{{PR_BODY}}

Gold source patch (the behavior change to exercise; do not copy new identifiers
into a parent-side missing-symbol test):
{{GOLD_PATCH}}

Changed source paths:
{{SOURCE_PATHS}}

Begin by calling `list_tests` for the most relevant module or path. Inspect
parent-side conventions and fixtures before staging the test.
