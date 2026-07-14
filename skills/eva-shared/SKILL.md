---
name: eva-shared
description: |
  EvaSkill 2.1.5 shared support package. Install alongside eva, eva-think, eva-audience-finder, eva-create, eva-learn, eva-brief, eva-link, eva-review, and eva-lens so sibling Eva skills can read shared schemas, references, examples, and validation scripts. Do not use directly for user tasks.
---

# Eva Shared

This is not a user-facing Eva entry.

`eva-shared` exists so the installer copies the shared Eva 2.1.5 source files into the same `skills/` folder as the sibling Eva skills. The sibling skills read this directory through relative paths such as:

```text
../eva-shared/schemas/asset-types.json
../eva-shared/references/shared/04_light-interaction_轻交互协议.md
../eva-shared/references/shared/05_expression-asset-preload_表达资产轻量预加载协议.md
```

## Hard Boundary

- Do not answer user requests from this skill.
- Do not route tasks to this skill.
- Do not treat this as Think, Create, Learn, Brief, Link, Memory, or Harness.
- If this skill is invoked directly, stop and tell the user to use `/eva` or the relevant Eva entry.

## Direct Invocation Response

```text
eva-shared 只是 Eva 2.1.5 的共享真源包，不是可直接使用的入口。请用 /eva、eva-think、eva-audience-finder、eva-create、eva-learn、eva-brief、eva-link、eva-review 或 eva-lens。
```
