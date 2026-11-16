# Development fixture vocabulary

**This is development test content. It is not release content, must never be loaded in production, and must never be counted toward the 650-word release target.** It exists so API and frontend work can be tested before the release vocabulary (#13 to #16) exists.

## Contents

- 13 files: `grade-K.json`, `grade-1.json` to `grade-12.json`. 154 words: 12 per grade, except grade 5 with 10.
- Format: exactly as in [`backend/data/README.md`](../../data/README.md).
- Every word appears in one grade only. Each grade has words of different lengths, and each correct-option position (1 to 4) is used at least twice per grade.

## Rules

- `content_version` is `fixture-1` for every entry. Release content must not use a `fixture-` prefix.
- Ids are `f1f1f1f1-00GG-4000-8000-0000000000NN`: `GG` is the two-digit grade (K is `00`, grades 1 to 12 are `01` to `12`) and `NN` is the two-digit position in the file, starting at `01`. Example: the 3rd word of grade 7 is `f1f1f1f1-0007-4000-8000-000000000003`. Release ids must be random UUIDs and must not start with `f1f1f1f1-`.
- Fixtures live outside `backend/data/` on purpose: the default run of the validator and the loader only looks in `backend/data/`, so fixtures are never loaded or counted by accident. Never copy a fixture file into `backend/data/`.

## Commands

From `backend/`:

```
uv run python -m app.services.vocabulary_validator fixtures/vocabulary
uv run python -m app.services.vocabulary_ingestion fixtures/vocabulary
```

The first prints `OK: 13 file(s), 154 entry(ies)`. The second needs a migrated database and ends with `Release target not reached: 154 of 650 words`.

In tests, use `VOCABULARY_FIXTURES_DIR` from `backend/tests/helpers.py`.
