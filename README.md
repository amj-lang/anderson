# anderson

[![version](https://img.shields.io/badge/version-0.9.0-blue)](https://github.com/amj-lang/anderson)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8A2BE2)](https://github.com/amj-lang/anderson)

**Four Claude subagents that plan, grill, implement, and review each other — with two human gates, because green ≠ understood.**

## Pipeline

```
plan ──▶ grill ──▶ plan_review ──[ YOU ]──▶ implement ──▶ diff_review ──[ YOU ]──▶ done
high     [ YOU ]   xhigh (edits)            medium        xhigh (read-only)
                                    ▲              │ fix_first
                                    └──────────────┘
```

| Stage        | Agent          | Model  | Effort | Gate  | Does                                        |
|--------------|----------------|--------|--------|-------|---------------------------------------------|
| plan         | `planner`      | opus   | high   | —     | writes `plan.md`                            |
| plan_review  | `plan-reviewer`| opus   | xhigh  | human | **edits** `plan.md` + `## Diverged because`; verdict `ship`/`fix_first`/`regrill` |
| implement    | `implementer`  | sonnet | medium | —     | writes `audit.md`                           |
| diff_review  | `reviewer`     | opus   | xhigh  | human | **read-only** diff review                   |

Plan-review can return `regrill` to loop back to grill.

## Install

```
/plugin marketplace add amj-lang/anderson
/plugin install anderson@dodge-this
```

Restart Claude Code fully (not just `/reload`), then:

```
/anderson:start brief-views "normalize briefs_table.views[] into brief_views_table"
```

Full docs: [plugins/anderson/README.md](plugins/anderson/README.md).

Licensed under the [MIT License](LICENSE).
