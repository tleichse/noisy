# Working with Claude on this project

## Ground rules
- Read the README (and any GOTCHAS/pitfalls doc) before making changes. If this project doesn't
  have one yet and you hit a non-obvious pitfall (tooling quirk, environment gotcha, footgun in
  a library/framework), add an entry to a GOTCHAS.md file so it isn't rediscovered later.
- Match existing conventions exactly — don't introduce a "cleaner" structure, pattern, or
  abstraction for new code just because it seems better. If you think a break from convention
  is warranted, ask first instead of deciding unilaterally.
- [Domain vocabulary language, if any]: e.g. model/field names, URLs, and user-facing strings
  are in [language X], matching the domain; code structure and internal identifiers follow
  normal [language Y] conventions. Don't translate one into the other.

## UI / design system (if this project has a UI)
- There is a single source of truth for UI patterns (style guide page, design system doc,
  component library, whatever the project uses). Reuse existing components/classes/tokens
  instead of inventing new markup or colors.
- Any change to a visual/status/color-coding convention (e.g. what color represents a given
  state) requires explicit approval before implementing — never pick a new color or component
  on your own judgment, even if it's just reusing an existing framework class. Update the style
  guide/doc in the same change once approved.

## App/module conventions
- Every [domain module/app] follows the same shape: [list the standard files/folders — e.g.
  models, views, urls, forms, admin, factories, tests]. Don't invent new top-level files
  without precedent.
- [List the standard layering rules — e.g. "query logic lives in a custom Manager/QuerySet next
  to the model, not in views/controllers."]
- [List the standard CRUD/URL/naming patterns so new features match existing ones exactly.]

## Task workflow
- Feature ideas start as raw entries in an IDEAS.md (or equivalent backlog file).
- Before non-trivial feature work, check a TASKS.md index (unique IDs, status, area, link to a
  per-task briefing file) for whether it's already tracked. If not, promote it first: assign
  the next ID, write a briefing doc with context/open questions/proposed approach/acceptance
  criteria, add it to the index, and mark it back in IDEAS.md.
- Update task status as work starts (🔧 in progress) and finishes (✅ done — code done, tested,
  changelog entry added). Keep the substantive detail in the task's own file; the index stays thin.

## Changelog
- After finishing a feature, add a CHANGELOG.md entry in the same change: a version/date
  heading with categorized sections (New feature / Bug fix / Enhancement / Ops), bullets in the
  existing `[module-name] short description` style.

## Mandatory delivery gate
- Treat the workflow as a strict sequence: idea in `IDEAS.md` -> approved task with unique ID
  and briefing in `TASKS.md` -> status `IN PROGRESS` -> implementation -> tests/validation ->
  `CHANGELOG.md` entry -> status `DONE`.
- Do not write code, notebooks, tests, or configuration for non-trivial work before the task
  and briefing exist and the task is marked `IN PROGRESS`.
- Treat `IDEAS.md` as a dated notebook: append ideas under `[YYYY-MM-DD]` as bullet points,
  investigate them first, record the recommendation, and only then promote approved ideas to
  tasks while recording the task link in the original bullet.
- Before handoff, verify that the task status, acceptance criteria, tests, changelog, and final
  diff all describe the same actual state.

## Tests
- One test file per concern (models, views, forms, urls, factories, e2e — adapt to the
  project's test layout). Every model/entity has a matching test factory, registered centrally
  rather than declared ad hoc per test file. Reuse existing authenticated-client/session
  fixtures instead of re-implementing login in each test.

## Lint/format
- Trust the project's configured linter/formatter as the source of style truth; run it (or
  trust pre-commit) rather than hand-formatting. Don't fight legacy config files that a newer
  tool has superseded.

## General collaboration style
- For exploratory/opinion questions, give a short recommendation with the main tradeoff —
  don't implement until I agree.
- Don't add error handling, abstractions, or scope beyond what's asked. No speculative future-
  proofing.
- Confirm before destructive or hard-to-reverse actions (force-push, reset --hard, deleting
  branches/files, amending pushed commits) — a prior approval doesn't carry forward to new
  instances of the same action.
- Default to no code comments unless explaining non-obvious *why*.
