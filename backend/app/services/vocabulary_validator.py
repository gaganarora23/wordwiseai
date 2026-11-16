"""Validate per-grade vocabulary JSON files (format: ``backend/data/README.md``).

Pure Python: no database, no settings, no network. Nothing here raises for bad
input; every problem becomes a ``Failure``. Anything that validates satisfies the
``words`` table constraints (migration 0001), so the loader can insert it as is.

Command line, from ``backend/``::

    uv run python -m app.services.vocabulary_validator [PATH ...]
"""

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

# Kept in step with GRADES in app/models/child.py (a test asserts it); not imported so
# that this module needs neither SQLAlchemy nor a database.
GRADES = ("K", *(str(n) for n in range(1, 13)))
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

FILE_NAME = re.compile(r"grade-(K|[1-9]|1[0-2])\.json")
UUID_FORM = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
NIL_UUID = "00000000-0000-0000-0000-000000000000"
WORD_FORM = re.compile(r"[A-Za-z]+(?:[-' ][A-Za-z]+)*")
SYLLABLES_FORM = re.compile(r"[A-Za-z]+(?: · [A-Za-z]+)*")
VERSION_FORM = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
UTF8_BOM = b"\xef\xbb\xbf"

# Entry keys in format order; failures are ordered by this.
KEYS = ("id", "word", "grade", "definition", "example", "syllables", "content_version", "options", "explanation")
OPTION_KEYS = ("text", "correct")
UNKNOWN_RANK = len(KEYS)


@dataclass(frozen=True)
class Failure:
    file: str
    entry_index: int | None
    entry_id: str | None
    field: str | None
    message: str

    def __str__(self) -> str:
        if self.entry_index is None:
            return f"{self.file}: file: {self.message}"
        who = f"entry {self.entry_index}" + (f" [{self.entry_id}]" if self.entry_id else "")
        return f"{self.file}: {who}: {self.field}: {self.message}" if self.field else f"{self.file}: {who}: {self.message}"


class _Dict(dict):
    """A parsed JSON object that remembers keys that appeared more than once."""

    duplicates: tuple


def _parse_object(pairs):
    result = _Dict()
    seen, duplicates = set(), []
    for key, value in pairs:
        if key in seen and key not in duplicates:
            duplicates.append(key)
        seen.add(key)
        result[key] = value
    result.duplicates = tuple(duplicates)
    return result


def _reject_constant(name):
    raise ValueError(f"{name} is not valid JSON")


class _FileResult:
    def __init__(self, path):
        self.path = str(path)
        self.items = []  # (entry index or -1 for the file, rank, Failure); sorted at the end
        self.entry_count = 0
        self.ids = {}  # valid, in-file-unique id -> entry index

    def file_failure(self, message):
        self.items.append((-1, 0, Failure(self.path, None, None, None, message)))

    def entry_failure(self, index, rank, entry_id, field, message):
        self.items.append((index, rank, Failure(self.path, index, entry_id, field, message)))

    def failures(self):
        return [item[2] for item in sorted(self.items, key=lambda item: (item[0], item[1]))]  # stable


def _is_str(value):
    return isinstance(value, str)


def _usable_word(entry):
    """The entry's word when it is itself valid, so cross-field checks do not pile on top of a bad word."""
    word = entry.get("word")
    if _is_str(word) and len(word) <= 40 and WORD_FORM.fullmatch(word) and "word" not in entry.duplicates:
        return word
    return None


def _text_problem(value, max_length):
    """First rule a free-text value breaks (type, blank, length, edges, control characters), or None."""
    if not _is_str(value):
        return "must be a string"
    if value.strip() == "":
        return "must not be blank"
    if len(value) > max_length:
        return f"must be at most {max_length} characters"
    if value != value.strip():
        return "must not start or end with whitespace"
    if any(unicodedata.category(c).startswith("C") for c in value):
        return "must not contain newlines, tabs or other control characters"
    return None


def _pattern_problem(value, max_length, pattern, rule):
    if not _is_str(value):
        return "must be a string"
    if value.strip() == "":
        return "must not be blank"
    if len(value) > max_length:
        return f"must be at most {max_length} characters"
    if not pattern.fullmatch(value):
        return rule
    return None


def _validate_entry(entry, index, expected_grade, result, seen_words):
    entry_id = entry.get("id") if _is_str(entry.get("id")) else None
    duplicates = set(entry.duplicates)

    def fail(field, message):
        result.entry_failure(index, KEYS.index(field), entry_id, field, message)

    def problem_of(key):
        """Problem with one top-level field, or None."""
        value = entry[key]
        if key == "id":
            if not _is_str(value):
                return "must be a string"
            if not UUID_FORM.fullmatch(value):
                return "must be a lowercase hyphenated UUID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)"
            if value == NIL_UUID:
                return "must not be the nil UUID"
            if value in result.ids:
                return f"duplicate id, first used by entry {result.ids[value]}"
            return None
        if key == "word":
            problem = _pattern_problem(value, 40, WORD_FORM, "must be letters with single internal hyphens, apostrophes or spaces")
            if problem is None and (seen := seen_words.get(value.strip().casefold())) is not None:
                return f"duplicate word, first used by entry {seen}"
            return problem
        if key == "grade":
            if not _is_str(value):
                return "must be a string"
            if value not in GRADES:
                return "must be one of K, 1 to 12"
            if expected_grade is not None and value != expected_grade:
                return f"must be {expected_grade!r} to match the file name"
            return None
        if key in ("definition", "example"):
            problem = _text_problem(value, 300)
            if problem is None and key == "example" and (word := _usable_word(entry)):
                if word.casefold() not in value.casefold():
                    return "must contain the word"
            return problem
        if key == "syllables":
            problem = _pattern_problem(value, 60, SYLLABLES_FORM, "must be letters joined by ' · ' (space, middle dot, space)")
            if problem is None and (word := _usable_word(entry)):
                if "".join(value.split(" · ")).casefold() != re.sub(r"[-' ]", "", word).casefold():
                    return "parts joined must equal the word without hyphens, apostrophes and spaces"
            return problem
        if key == "content_version":
            return _pattern_problem(value, 32, VERSION_FORM, "must start with a letter or digit and use only letters, digits, '.', '_' and '-'")
        if key == "explanation":
            return _text_problem(value, 300)
        return None

    for key in KEYS:
        if key == "options":
            _validate_options(entry, index, entry_id, result, duplicates)
        elif key not in entry:
            fail(key, "required")
        elif key in duplicates:
            fail(key, "duplicate key")
        elif (problem := problem_of(key)) is not None:
            fail(key, problem)
        elif key == "id":
            result.ids[entry["id"]] = index
        elif key == "word":
            seen_words[entry["word"].strip().casefold()] = index
    for key in entry:
        if key not in KEYS:
            result.entry_failure(index, UNKNOWN_RANK, entry_id, key, "unknown key")


def _validate_options(entry, index, entry_id, result, entry_duplicates):
    rank = KEYS.index("options")

    def fail(field, message):
        result.entry_failure(index, rank, entry_id, field, message)

    if "options" not in entry:
        return fail("options", "required")
    if "options" in entry_duplicates:
        return fail("options", "duplicate key")
    options = entry["options"]
    if not isinstance(options, list):
        return fail("options", "must be an array of exactly 4 options")
    if len(options) != 4:
        return fail("options", f"must have exactly 4 options, found {len(options)}")
    correct, seen_texts = 0, {}
    for i, option in enumerate(options):
        if not isinstance(option, dict):
            fail(f"options[{i}]", "must be an object with keys text and correct")
            continue
        for key in OPTION_KEYS:
            field = f"options[{i}].{key}"
            if key not in option:
                fail(field, "required")
            elif key in getattr(option, "duplicates", ()):
                fail(field, "duplicate key")
            elif key == "correct":
                if isinstance(option[key], bool):
                    correct += option[key]
                else:
                    fail(field, "must be true or false")
            elif (problem := _text_problem(option[key], 150)) is not None:
                fail(field, problem)
            else:
                folded = option[key].strip().casefold()
                if folded in seen_texts:
                    fail(field, f"duplicate of options[{seen_texts[folded]}].text")
                else:
                    seen_texts[folded] = i
        for key in option:
            if key not in OPTION_KEYS:
                fail(f"options[{i}].{key}", "unknown key")
    if correct != 1:
        fail("options", f"exactly one option must have correct: true, found {correct}")


def _nested_duplicates(entry, index, entry_id, result):
    """Duplicate keys inside values that are not options (e.g. inside an unknown key's object)."""
    stack = [(key, value) for key, value in entry.items() if key not in KEYS]
    while stack:
        path, value = stack.pop(0)
        if isinstance(value, _Dict):
            for key in value.duplicates:
                result.entry_failure(index, UNKNOWN_RANK, entry_id, f"{path}.{key}", "duplicate key")
            stack.extend((f"{path}.{key}", child) for key, child in value.items())
        elif isinstance(value, list):
            stack.extend((f"{path}[{i}]", child) for i, child in enumerate(value))


_FAILED = object()


def _read_json(result, path):
    """The parsed file content, or ``_FAILED`` after recording one file-level failure."""
    try:
        raw = path.read_bytes()
    except OSError as error:
        result.file_failure(f"cannot read file: {error.strerror or error}")
        return _FAILED
    if raw.startswith(UTF8_BOM):
        result.file_failure("file must be UTF-8 without a byte order mark (BOM)")
        return _FAILED
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        result.file_failure("file is not valid UTF-8")
        return _FAILED
    try:
        return json.loads(text, object_pairs_hook=_parse_object, parse_constant=_reject_constant)
    except (ValueError, RecursionError) as error:
        result.file_failure(f"not valid JSON: {error}")
        return _FAILED


def _check_file(path, ids_seen=None):
    path = Path(path)
    result = _FileResult(path)
    if not path.exists():
        result.file_failure("file does not exist")
        return result
    if not path.is_file():
        result.file_failure("not a file (is it a directory?)")
        return result
    match = FILE_NAME.fullmatch(path.name)
    if match is None:
        result.file_failure("file name must be grade-<G>.json where <G> is K or 1 to 12 (e.g. grade-K.json, grade-10.json)")
    expected_grade = match.group(1) if match else None

    data = _read_json(result, path)
    if data is _FAILED:
        return result
    if not isinstance(data, list):
        result.file_failure("top level must be an array of entries")
        return result
    if not data:
        result.file_failure("no entries")
        return result

    result.entry_count = len(data)
    seen_words = {}
    for index, entry in enumerate(data):
        if not isinstance(entry, _Dict):
            result.entry_failure(index, 0, None, None, "entry must be an object")
            continue
        _validate_entry(entry, index, expected_grade, result, seen_words)
        _nested_duplicates(entry, index, entry["id"] if _is_str(entry.get("id")) else None, result)
    return result


def validate_file(path) -> list[Failure]:
    """Every problem in one vocabulary file; ``[]`` when it is valid. Never raises for bad input."""
    return _check_file(path).failures()


def _check_files(paths):
    results = [_check_file(path) for path in paths]
    first_seen = {}  # id -> (file, entry index)
    for result in results:
        for entry_id, index in sorted(result.ids.items(), key=lambda pair: pair[1]):
            if entry_id in first_seen:
                other_file, other_index = first_seen[entry_id]
                result.entry_failure(
                    index, KEYS.index("id"), entry_id, "id",
                    f"duplicate id, first used in {other_file} entry {other_index}",
                )
            else:
                first_seen[entry_id] = (result.path, index)
    return results


def validate_files(paths) -> list[Failure]:
    """``validate_file`` for each path in order, plus ids repeated across files (reported on the later file)."""
    return [failure for result in _check_files(paths) for failure in result.failures()]


def _expand(paths):
    """Files to validate and the paths that gave none: directories are searched recursively for *.json."""
    files, empty = [], []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            found = sorted(p for p in path.rglob("*.json") if p.is_file())
            files.extend(found)
            if not found:
                empty.append(f"no JSON files found in {path}")
        elif path.exists():
            files.append(path)
        else:
            empty.append(f"no JSON files found: {path} does not exist")
    return files, empty


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.services.vocabulary_validator",
        description="Validate vocabulary JSON files. Directories are searched recursively for *.json; "
        "with no PATH, backend/data/ is validated.",
    )
    parser.add_argument("paths", nargs="*", metavar="PATH")
    args = parser.parse_args(argv)  # a usage error exits with code 2

    files, problems = _expand(args.paths or [DATA_DIR])
    if problems and not files:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 2
    for problem in problems:
        print(f"warning: {problem}", file=sys.stderr)

    results = _check_files(files)
    failures = [failure for result in results for failure in result.failures()]
    if not failures:
        print(f"OK: {len(results)} file(s), {sum(r.entry_count for r in results)} entry(ies)")
        return 0
    for failure in failures:
        print(failure, file=sys.stderr)
    failed_files = len({failure.file for failure in failures})
    print(f"FAILED: {len(failures)} failure(s) in {failed_files} file(s)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
