"""Load validated per-grade vocabulary JSON files into the ``words`` table (format: ``backend/data/README.md``).

Validation (``vocabulary_validator``) runs first and needs no database or settings. Only when every
file is valid are settings read and the rows written, in one transaction committed once. Rows are
matched by ``id`` only: new ids are inserted, ids whose stored columns differ are updated in place,
equal rows are not written at all (no UPDATE, so ``xmin`` stays). Rows whose id is not in the files
are never touched, only reported.

Command line, from ``backend/``::

    uv run python -m app.services.vocabulary_ingestion [PATH ...]

Exit codes: 0 loaded (or nothing changed), 1 validation failures (nothing loaded), 2 no JSON files
found or usage error, 3 configuration or database problem.
"""

import argparse
import json
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import ConfigError, load_settings
from app.services.vocabulary_validator import DATA_DIR, GRADES, _check_files, _expand

RELEASE_TARGET = 650
DATA_COLUMNS = (
    "word", "grade", "definition", "example", "syllables", "content_version",
    "option_1", "option_2", "option_3", "option_4", "correct_option", "explanation",
)
ALL_COLUMNS = ("id", *DATA_COLUMNS)

_COLUMN_LIST = ", ".join(ALL_COLUMNS)
_VALUE_LIST = ", ".join(f":{c}" for c in ALL_COLUMNS)
_SET_LIST = ", ".join(f"{c} = EXCLUDED.{c}" for c in DATA_COLUMNS)
_OLD = ", ".join(f"words.{c}" for c in DATA_COLUMNS)
_NEW = ", ".join(f"EXCLUDED.{c}" for c in DATA_COLUMNS)
# The WHERE makes an equal row a no-op: no row is returned and none is written.
UPSERT_SQL = text(
    f"INSERT INTO words ({_COLUMN_LIST}) VALUES ({_VALUE_LIST}) "
    f"ON CONFLICT (id) DO UPDATE SET {_SET_LIST} WHERE ({_OLD}) IS DISTINCT FROM ({_NEW}) "
    "RETURNING (xmax = 0) AS inserted"
)

HELP_DESCRIPTION = """\
Validate vocabulary JSON files and, only if all are valid, load them into the words table in one
transaction. A PATH is a file or a directory (searched recursively for *.json, sorted); with no PATH
backend/data/ is used. Validation needs no database. The command is idempotent: rows are matched by id,
new ids are inserted, changed rows are updated in place and unchanged rows are not written.
Words in the database whose id is not in the files are never deleted or changed; they are listed after
loading. The release target is 650 words: the output says whether the files loaded in this run hold
exactly 650 entries (it counts the entries in the files, not rows in the database) and the exit code is
not affected. DATABASE_URL is read from the environment or the repo-root .env. The database must be
migrated first (uv run alembic upgrade head). Exit codes: 0 loaded, 1 validation failures, 2 no JSON
files found or usage error, 3 configuration or database problem.
"""


class IngestionError(Exception):
    """A configuration or database problem; the message is one line, safe to print."""


def entry_to_row(entry: dict) -> dict:
    """The ``words`` row for a validated entry (see backend/data/README.md)."""
    row = {key: entry[key] for key in ("id", "word", "grade", "definition", "example", "syllables", "content_version", "explanation")}
    for position, option in enumerate(entry["options"], start=1):
        row[f"option_{position}"] = option["text"]
    row["correct_option"] = next(i for i, option in enumerate(entry["options"], start=1) if option["correct"])
    return row


def load_rows(files: Sequence[Path]) -> list[dict]:
    """Rows of already validated files, in file then entry order."""
    return [
        entry_to_row(entry)
        for path in files
        for entry in json.loads(Path(path).read_text(encoding="utf-8"))
    ]


def upsert_word(connection, row: dict) -> str:
    """Write one row: ``created``, ``updated`` or ``unchanged`` (nothing written)."""
    result = connection.execute(UPSERT_SQL, row).first()
    if result is None:
        return "unchanged"
    return "created" if result.inserted else "updated"


def load_words(connection, rows: Sequence[dict]) -> tuple[Counter, list[tuple]]:
    """Upsert every row on ``connection`` (the caller owns the transaction).

    Returns the counts of created/updated/unchanged and the ``(id, word, grade)`` of database rows whose
    id is not among ``rows``, ordered by grade (K, 1 to 12), then word, then id.
    """
    counts = Counter({"created": 0, "updated": 0, "unchanged": 0})
    for row in rows:
        counts[upsert_word(connection, row)] += 1
    ids = [row["id"] for row in rows]
    left = connection.execute(
        text("SELECT id, word, grade FROM words WHERE NOT (id = ANY(CAST(:ids AS uuid[])))"), {"ids": ids}
    ).all()
    left.sort(key=lambda r: (GRADES.index(r.grade), r.word, str(r.id)))
    return counts, [(str(r.id), r.word, r.grade) for r in left]


def _first_line(error: BaseException) -> str:
    message = str(getattr(error, "orig", None) or error).strip()
    return message.splitlines()[0] if message else type(error).__name__


def ingest(rows: Sequence[dict]) -> tuple[Counter, list[tuple]]:
    """Connect, check the schema and load ``rows`` in one transaction. Raises ``IngestionError``."""
    try:
        load_settings()
    except ConfigError as error:
        raise IngestionError(str(error)) from None
    from app.db import get_engine  # after settings are known to be valid

    engine = get_engine()
    try:
        try:
            connection = engine.connect()
        except SQLAlchemyError:  # the message can carry host details, so it is not printed
            raise IngestionError("Cannot connect to the database: check DATABASE_URL and that PostgreSQL is running") from None
        try:
            with connection:
                if not inspect(connection).has_table("words"):
                    raise IngestionError("Database is not migrated: run 'uv run alembic upgrade head' first")
                connection.rollback()  # end the implicit transaction opened by the check
                with connection.begin():  # commits once at the end, rolls everything back on any error
                    return load_words(connection, rows)
        except SQLAlchemyError as error:
            raise IngestionError(f"Database error, nothing was loaded: {_first_line(error)}") from None
    finally:
        engine.dispose()


def format_report(rows: Sequence[dict], file_count: int, counts: Counter, left: Sequence[tuple]) -> list[str]:
    by_grade = Counter(row["grade"] for row in rows)
    lines = [f"Grade {grade}: {by_grade[grade]} word(s)" for grade in GRADES if by_grade[grade]]
    total = len(rows)
    lines.append(f"Total: {total} word(s) in {file_count} file(s)")
    lines.append(f"Created: {counts['created']}, updated: {counts['updated']}, unchanged: {counts['unchanged']}")
    lines.append(f"Not in files (left in place): {len(left)}")
    lines.extend(f"  {word_id} {word} (grade {grade})" for word_id, word, grade in left)
    if total == RELEASE_TARGET:
        lines.append(f"Release target reached: {RELEASE_TARGET} words")
    else:
        lines.append(f"Release target not reached: {total} of {RELEASE_TARGET} words")
    return lines


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.services.vocabulary_ingestion",
        description=HELP_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
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

    failures = [failure for result in _check_files(files) for failure in result.failures()]
    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        print(f"FAILED: {len(failures)} failure(s) in {len({f.file for f in failures})} file(s)", file=sys.stderr)
        return 1

    rows = load_rows(files)
    try:
        counts, left = ingest(rows)
    except IngestionError as error:
        print(str(error), file=sys.stderr)
        return 3
    for line in format_report(rows, len(files), counts, left):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
