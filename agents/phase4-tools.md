# Phase 4 native tool definitions

This JSON block is loaded directly into the model request. Descriptions are part
of the measured prompt surface.

```json
[
  {
    "type": "function",
    "function": {
      "name": "list_tests",
      "description": "Find parent-checkout tests and fixtures relevant to a module or repository path. Returns allowed test layouts, ranked test files, test names, and short convention excerpts. Start here before authoring.",
      "parameters": {
        "type": "object",
        "properties": {
          "module_or_path": {
            "type": "string",
            "description": "A changed module, dotted module name, source path, or behavior term, for example src/flask/app.py or flask.app."
          }
        },
        "required": ["module_or_path"],
        "additionalProperties": false
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "read_file",
      "description": "Read a numbered window from one parent-checkout file. The inclusive window is capped at 160 lines; request another window when output is explicitly truncated.",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {"type": "string", "description": "Repository-relative path at the broken parent."},
          "start": {"type": "integer", "minimum": 1, "description": "First one-based line to return."},
          "end": {"type": "integer", "minimum": 1, "description": "Last one-based line to return, inclusive."}
        },
        "required": ["path", "start", "end"],
        "additionalProperties": false
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "search",
      "description": "Search tracked text in the parent checkout with a regular expression. Returns bounded path:line matches. Narrow the pattern if output is truncated.",
      "parameters": {
        "type": "object",
        "properties": {
          "pattern": {"type": "string", "description": "A non-empty extended regular expression, preferably a symbol, fixture, error phrase, or API name."}
        },
        "required": ["pattern"],
        "additionalProperties": false
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "write_test",
      "description": "Stage exactly one new pytest file. Replaces the previously staged candidate. Rejects unsafe paths, paths outside this repository's configured test layout, and existing files; it cannot edit source or existing tests.",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {"type": "string", "description": "Repository-relative path for one new test file."},
          "content": {"type": "string", "description": "Complete pytest source for the new file."}
        },
        "required": ["path", "content"],
        "additionalProperties": false
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "run_test",
      "description": "Run the currently staged test once in a fresh isolated checkout at parent or fix. Returns exit code, per-test status, and actionable bounded failure output. Run fix first, repair failures, then confirm parent fails for the intended assertion.",
      "parameters": {
        "type": "object",
        "properties": {
          "endpoint": {"type": "string", "enum": ["parent", "fix"], "description": "Checkout to test."}
        },
        "required": ["endpoint"],
        "additionalProperties": false
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "check_gates",
      "description": "Run the complete G1-G5 verifier on the staged test and return structured per-gate evidence plus a suggested repair. This is expensive validation signal and is hard-capped at five calls per case.",
      "parameters": {
        "type": "object",
        "properties": {},
        "additionalProperties": false
      }
    }
  }
]
```
