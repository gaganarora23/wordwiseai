# Vocabulary data

One JSON file per grade. The validator checks the files and the loader (#11) inserts them into the `words` table, so anything that validates is accepted by the database constraints.

## Files

- Name: `grade-<G>.json` where `<G>` is exactly `K` or `1` to `12`: `grade-K.json`, `grade-10.json`. Rejected: `grade-k.json`, `grade-01.json`, `grade-13.json`, `grade-0.json`, `K.json`, `grade-3.JSON`. The same rule applies to files in subfolders (for example `fixtures/`).
- Encoding: UTF-8 without a byte order mark.
- Content: a JSON array of one or more entry objects. Every `grade` in the file equals the `<G>` of its name.
- Duplicate keys inside any object are errors (JSON parsers would silently keep the last one).

## Entry

An entry has exactly these keys and no others (no question ID: question and option IDs are derived by the API later).

```json
{
  "id": "0b8f5c3e-6a1d-4f27-9c55-3d2f7e8a1b40",
  "word": "banana",
  "grade": "K",
  "definition": "A long yellow fruit with a soft inside.",
  "example": "I ate a banana with my lunch.",
  "syllables": "ba · na · na",
  "content_version": "2026.1",
  "options": [
    {"text": "A long yellow fruit", "correct": true},
    {"text": "A kind of shoe", "correct": false},
    {"text": "A farm animal", "correct": false},
    {"text": "A type of weather", "correct": false}
  ],
  "explanation": "A banana is a fruit you can peel and eat. Great job!"
}
```

Lengths are counted in characters. "Blank" means empty or only whitespace (Python `str.strip()`, which is stricter than the database check, on purpose: spaces, tabs, newlines, U+00A0 and U+3000 all count as whitespace).

| Field | Rule |
|---|---|
| `id` | String, canonical lowercase hyphenated UUID (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`, hex `0-9a-f`). Not the nil UUID. Unique within the file and across all files validated together. |
| `word` | String, 1 to 40 characters, letters `A-Za-z` with single internal hyphens, apostrophes or spaces (`^[A-Za-z]+(?:[-' ][A-Za-z]+)*$`). Unique within the file, ignoring case (`Cat` and `cat` collide). |
| `grade` | String, exactly the grade of the file name. |
| `definition` | String, 1 to 300 characters, not blank, no leading or trailing whitespace, no newline, tab or other control characters. |
| `example` | Same rules as `definition`, and it contains the `word`, ignoring case. |
| `syllables` | String, at most 60 characters: letters only, parts joined by exactly ` · ` (space, U+00B7 middle dot, space); one syllable is a single part (`cat`). The parts joined together equal the `word` without hyphens, apostrophes and spaces, ignoring case (`ba · na · na` for `banana`). |
| `content_version` | String, 1 to 32 characters, `^[A-Za-z0-9][A-Za-z0-9._-]*$` (`2026.1`, `fixture-1`). |
| `options` | Array of exactly 4 objects with exactly the keys `text` and `correct`. Exactly one has `"correct": true` (a JSON boolean). |
| `options[i].text` | Same rules as `definition`, 1 to 150 characters. The four texts are distinct ignoring case. |
| `explanation` | Same rules as `definition`, 1 to 300 characters. |

The same word in two different grade files is not checked here.

In the database an entry becomes one `words` row: `option_1` to `option_4` in array order and `correct_option` the 1-based position of the correct option.

## Running the validator

From `backend/`:

```
uv run python -m app.services.vocabulary_validator [PATH ...]
```

A path is a file or a directory (searched recursively for `*.json`, sorted). With no path it validates this `data/` folder. It needs no database and no `DATABASE_URL`.

- Exit `0` and `OK: <n> file(s), <m> entry(ies)` when everything is valid.
- Exit `1` when there are problems: one line per problem on stderr (`<file>: entry <index> [<id>]: <field>: <message>`, or `<file>: file: <message>`), then `FAILED: <k> failure(s) in <n> file(s)`.
- Exit `2` when no JSON files are found (the message names the path) or the command is used wrongly.

From Python: `validate_file(path)` and `validate_files(paths)` in `app/services/vocabulary_validator.py` return a list of `Failure` (`file`, `entry_index`, `entry_id`, `field`, `message`); the list is empty when valid.
