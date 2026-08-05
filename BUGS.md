# Bug Tracker

All bugs identified on **2026-07-10** were resolved in branch `feature/enhace-parsing-1`.
See `BUGS.md` git history for the full record of what was fixed and how.

## 2026-08-05

- **Fixed:** `FilterResult.filter` dispatch regression introduced by the
  filename-truncation commit (`0384012`): the per-rule dispatch chain had
  moved out of the loop and into the truncation `if` block, so filtering
  returned an empty result for every normal-length filter. Covered by
  end-to-end regression tests in `test/logic/test_filter_dispatch.py`.
- **Fixed:** `FileAnalyzer.detect_lang` only returned `UNDEFINED` by
  accident (`UNDEFINED`'s empty label matched everything via
  `endswith("")`); rewritten as explicit prefix/longest-suffix matching.

**Current status: 129 tests / 0 failures** (`pytest test/` from `app/`)
