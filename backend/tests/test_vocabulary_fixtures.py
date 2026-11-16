"""Development fixture vocabulary (#12): content rules, validation, loading, and isolation from release data.

The checks are functions over a directory so the negative tests can run them on a temp copy.
"""

import json
import re
import shutil
import uuid

import pytest
from sqlalchemy import text

from app.services import vocabulary_ingestion
from app.services import vocabulary_validator as validator
from app.services.vocabulary_validator import DATA_DIR, GRADES, validate_files
from tests.helpers import VOCABULARY_FIXTURES_DIR
from tests.test_vocabulary_ingestion import entry, grade_file, run_cli, stdout_lines, table

ID_PREFIX = "f1f1f1f1-"
LABEL = "fixture-1"
EXPECTED_COUNTS = {g: 10 if g == "5" else 12 for g in GRADES}
EXPECTED_NAMES = {f"grade-{g}.json" for g in GRADES} | {"README.md"}
MODULE_VALIDATOR = "app.services.vocabulary_validator"


def load_all(directory):
    """{grade: [entries]} for the grade files that exist in the directory."""
    return {g: json.loads((directory / f"grade-{g}.json").read_text(encoding="utf-8")) for g in GRADES if (directory / f"grade-{g}.json").exists()}


def check_coverage(directory):
    """Fail naming the grade when a grade file is missing or has the wrong number of entries."""
    data = load_all(directory)
    for grade in GRADES:
        assert grade in data, f"grade {grade} has no fixture file"
        assert len(data[grade]) == EXPECTED_COUNTS[grade], f"grade {grade} has {len(data[grade])} entries, expected {EXPECTED_COUNTS[grade]}"


def check_labels(directory):
    """Fail naming the entry when the content version or the id does not follow the reserved pattern."""
    for grade, entries in load_all(directory).items():
        gg = "00" if grade == "K" else f"{int(grade):02d}"
        for position, e in enumerate(entries, start=1):
            expected = f"f1f1f1f1-00{gg}-4000-8000-0000000000{position:02d}"
            assert e["content_version"] == LABEL, f"grade {grade} entry {position}: content_version {e['content_version']!r}"
            assert e["id"] == expected, f"grade {grade} entry {position}: id {e['id']} is not {expected}"


def syllable_count(e):
    return len(e["syllables"].split(" · "))


@pytest.fixture
def fixture_copy(tmp_path):
    """A temp copy of the fixtures; tests change this, never the committed files."""
    target = tmp_path / "vocabulary"
    shutil.copytree(VOCABULARY_FIXTURES_DIR, target)
    return target


def rewrite(directory, grade, change):
    path = directory / f"grade-{grade}.json"
    entries = json.loads(path.read_text(encoding="utf-8"))
    change(entries)
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


# --- Files and content ---


def test_directory_holds_exactly_the_13_grade_files_and_a_readme():
    assert {p.name for p in VOCABULARY_FIXTURES_DIR.iterdir()} == EXPECTED_NAMES


def test_fixtures_directory_is_resolved_from_the_file_location_and_is_outside_data():
    assert VOCABULARY_FIXTURES_DIR.is_absolute() and VOCABULARY_FIXTURES_DIR.is_dir()
    assert DATA_DIR not in VOCABULARY_FIXTURES_DIR.parents and VOCABULARY_FIXTURES_DIR != DATA_DIR


def test_entry_counts_are_12_per_grade_and_10_for_grade_5_in_total_154():
    check_coverage(VOCABULARY_FIXTURES_DIR)
    assert sum(len(v) for v in load_all(VOCABULARY_FIXTURES_DIR).values()) == 154


def test_every_entry_has_the_fixture_label_and_the_reserved_id():
    check_labels(VOCABULARY_FIXTURES_DIR)


def test_words_are_distinct_across_all_files_ignoring_case():
    words = [e["word"].lower() for entries in load_all(VOCABULARY_FIXTURES_DIR).values() for e in entries]
    assert len(words) == len(set(words))


@pytest.mark.parametrize("grade", GRADES)
def test_every_correct_position_is_used_at_least_twice_per_grade(grade):
    entries = load_all(VOCABULARY_FIXTURES_DIR)[grade]
    positions = [[o["correct"] for o in e["options"]].index(True) + 1 for e in entries]
    assert all(positions.count(p) >= 2 for p in (1, 2, 3, 4)), positions


@pytest.mark.parametrize("grade", GRADES)
def test_every_grade_has_a_one_syllable_word_and_a_longer_word(grade):
    counts = [syllable_count(e) for e in load_all(VOCABULARY_FIXTURES_DIR)[grade]]
    assert 1 in counts and max(counts) >= 2


def test_all_syllable_counts_from_1_to_5_or_more_and_a_multi_part_word_are_present():
    entries = [e for es in load_all(VOCABULARY_FIXTURES_DIR).values() for e in es]
    counts = {syllable_count(e) for e in entries}
    assert {1, 2, 3, 4} <= counts and max(counts) >= 5
    ice_cream = next(e for e in load_all(VOCABULARY_FIXTURES_DIR)["2"] if e["word"] == "ice cream")
    assert ice_cream["syllables"] == "ice · cream"
    assert any(re.search(r"[ -]", e["word"]) for e in entries)


def test_every_example_contains_its_word_and_no_extra_hint_field_exists():
    for entries in load_all(VOCABULARY_FIXTURES_DIR).values():
        for e in entries:
            assert e["word"].lower() in e["example"].lower()
            assert set(e) == {"id", "word", "grade", "definition", "example", "syllables", "content_version", "options", "explanation"}


def test_every_entry_has_four_distinct_option_texts():
    for entries in load_all(VOCABULARY_FIXTURES_DIR).values():
        for e in entries:
            texts = [o["text"].lower() for o in e["options"]]
            assert len(set(texts)) == 4


# --- Validation ---


def test_validator_accepts_the_fixtures_and_prints_the_exact_summary():
    import subprocess
    import sys
    from tests.test_vocabulary_ingestion import BACKEND
    result = subprocess.run([sys.executable, "-m", MODULE_VALIDATOR, "fixtures/vocabulary"], cwd=BACKEND, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "OK: 13 file(s), 154 entry(ies)"
    assert validate_files([VOCABULARY_FIXTURES_DIR / f"grade-{g}.json" for g in GRADES]) == []


# --- Loading (real PostgreSQL) ---


def test_loading_the_fixtures_prints_the_exact_report_and_is_idempotent(clean_db, harness_db_url):
    expected = [f"Grade {g}: {EXPECTED_COUNTS[g]} word(s)" for g in GRADES]
    first = run_cli(["fixtures/vocabulary"], harness_db_url)
    assert first.returncode == 0, first.stderr
    assert stdout_lines(first) == [
        *expected,
        "Total: 154 word(s) in 13 file(s)",
        "Created: 154, updated: 0, unchanged: 0",
        "Not in files (left in place): 0",
        "Release target not reached: 154 of 650 words",
    ]
    with clean_db.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM words")).scalar_one() == 154
        by_grade = dict(connection.execute(text("SELECT grade, count(*) FROM words GROUP BY grade")).all())
    assert by_grade == EXPECTED_COUNTS
    before = table(clean_db)

    second = run_cli(["fixtures/vocabulary"], harness_db_url)
    assert second.returncode == 0, second.stderr
    assert "Created: 0, updated: 0, unchanged: 154" in stdout_lines(second)
    assert stdout_lines(second)[-1] == "Release target not reached: 154 of 650 words"
    assert table(clean_db) == before


def test_output_never_claims_the_release_target_is_reached(clean_db, harness_db_url):
    result = run_cli([VOCABULARY_FIXTURES_DIR], harness_db_url)
    assert "Release target reached" not in result.stdout
    help_text = run_cli(["--help"], harness_db_url).stdout
    assert "fixture" not in help_text.lower()


def test_docs_do_not_describe_fixtures_as_release_content():
    from tests.test_vocabulary_ingestion import BACKEND
    for path in (BACKEND / "data" / "README.md", BACKEND.parent / "README.md", VOCABULARY_FIXTURES_DIR / "README.md"):
        text_ = path.read_text(encoding="utf-8")
        assert "Release target reached" not in text_.replace("`Release target reached: 650 words`", "")
        assert not re.search(r"fixtures?[^.\n]*(are|is) release content", text_, re.IGNORECASE)


# --- Keeping fixtures out of release counts ---


def default_run_files():
    """The files the default (no PATH) run of either CLI would use: the same function, rooted at backend/data/."""
    files, _problems = validator._expand([DATA_DIR])
    files2, _problems2 = vocabulary_ingestion._expand([DATA_DIR])
    assert files == files2
    return files


def test_default_run_files_are_never_fixtures():
    for path in default_run_files():
        assert VOCABULARY_FIXTURES_DIR not in path.resolve().parents
        content = path.read_text(encoding="utf-8")
        assert LABEL not in content
        assert ID_PREFIX not in content


def test_default_data_directory_and_both_clis_use_the_same_dir():
    assert vocabulary_ingestion.DATA_DIR is validator.DATA_DIR
    assert DATA_DIR.name == "data" and DATA_DIR.parent == VOCABULARY_FIXTURES_DIR.parents[1]


def test_no_fixture_file_or_label_is_under_data():
    for path in DATA_DIR.rglob("*"):
        assert "fixture" not in path.name.lower()
        if path.suffix == ".json":
            content = path.read_text(encoding="utf-8")
            assert LABEL not in content and ID_PREFIX not in content


def test_fixture_ids_start_with_the_reserved_prefix_and_never_meet_ids_under_data():
    fixture_ids = {e["id"] for entries in load_all(VOCABULARY_FIXTURES_DIR).values() for e in entries}
    assert len(fixture_ids) == 154 and all(i.startswith(ID_PREFIX) for i in fixture_ids)
    data_ids = {e["id"] for path in DATA_DIR.rglob("*.json") for e in json.loads(path.read_text(encoding="utf-8"))}
    assert fixture_ids.isdisjoint(data_ids)


@pytest.mark.skipif(any(DATA_DIR.rglob("*.json")), reason="backend/data/ already holds release files")
def test_default_ingestion_run_with_only_a_readme_in_data_exits_2_and_leaves_the_database_alone(clean_db, harness_db_url):
    result = run_cli([], harness_db_url)
    assert result.returncode == 2
    assert "no JSON files found in" in result.stderr
    assert result.stdout == ""
    assert table(clean_db) == []


@pytest.mark.skipif(any(DATA_DIR.rglob("*.json")), reason="backend/data/ already holds release files")
def test_default_validator_run_with_only_a_readme_in_data_exits_2():
    import subprocess
    import sys
    from tests.test_vocabulary_ingestion import BACKEND
    result = subprocess.run([sys.executable, "-m", MODULE_VALIDATOR], cwd=BACKEND, capture_output=True, text=True)
    assert result.returncode == 2 and "no JSON files found in" in result.stderr


def test_a_release_run_counts_only_its_own_files_and_leaves_the_fixture_rows_in_place(clean_db, harness_db_url, tmp_path):
    run_cli(["fixtures/vocabulary"], harness_db_url)
    grade_file(tmp_path, "K", [entry(0), entry(1)])
    grade_file(tmp_path, "3", [entry(2, "3")])
    result = run_cli([tmp_path], harness_db_url)
    lines = stdout_lines(result)
    assert result.returncode == 0, result.stderr
    assert lines[:5] == [
        "Grade K: 2 word(s)", "Grade 3: 1 word(s)", "Total: 3 word(s) in 2 file(s)",
        "Created: 3, updated: 0, unchanged: 0", "Not in files (left in place): 154",
    ]
    assert lines[-1] == "Release target not reached: 3 of 650 words"
    assert len([line for line in lines if ID_PREFIX in line]) == 154
    with clean_db.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM words")).scalar_one() == 157


def test_fixtures_can_be_loaded_by_tests_through_the_helper_constant(clean_db, harness_db_url):
    assert run_cli([VOCABULARY_FIXTURES_DIR], harness_db_url).returncode == 0
    with clean_db.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM words WHERE content_version = 'fixture-1'")).scalar_one() == 154


# --- Negative cases on a temp copy ---


def test_a_duplicate_id_across_files_fails_validation_and_ingestion_writes_nothing(fixture_copy, clean_db, harness_db_url):
    other_id = json.loads((fixture_copy / "grade-K.json").read_text(encoding="utf-8"))[0]["id"]

    def change(entries):
        entries[0]["id"] = other_id

    rewrite(fixture_copy, "1", change)
    import subprocess
    import sys
    from tests.test_vocabulary_ingestion import BACKEND
    checked = subprocess.run([sys.executable, "-m", MODULE_VALIDATOR, str(fixture_copy)], cwd=BACKEND, capture_output=True, text=True)
    assert checked.returncode == 1
    assert "duplicate id" in checked.stderr
    loaded = run_cli([fixture_copy], harness_db_url)
    assert loaded.returncode == 1
    assert "duplicate id" in loaded.stderr
    assert table(clean_db) == []


def test_coverage_check_names_the_grade_of_a_deleted_file(fixture_copy):
    (fixture_copy / "grade-9.json").unlink()
    with pytest.raises(AssertionError, match=r"grade 9 has no fixture file"):
        check_coverage(fixture_copy)


def test_coverage_check_names_the_grade_with_only_9_entries(fixture_copy):
    rewrite(fixture_copy, "7", lambda entries: entries.pop())
    rewrite(fixture_copy, "7", lambda entries: entries.pop())
    rewrite(fixture_copy, "7", lambda entries: entries.pop())
    with pytest.raises(AssertionError, match=r"grade 7 has 9 entries, expected 12"):
        check_coverage(fixture_copy)


def test_coverage_check_passes_on_an_unchanged_copy(fixture_copy):
    check_coverage(fixture_copy)
    check_labels(fixture_copy)


@pytest.mark.parametrize("field, value, message", [
    ("content_version", "2026.1", "content_version '2026.1'"),
    ("id", str(uuid.UUID(int=5)), "is not f1f1f1f1-0004-4000-8000-000000000002"),
    ("id", "f1f1f1f1-0004-4000-8000-000000000003", "is not f1f1f1f1-0004-4000-8000-000000000002"),
])
def test_label_check_rejects_a_wrong_version_or_id(fixture_copy, field, value, message):
    def change(entries):
        entries[1][field] = value

    rewrite(fixture_copy, "4", change)
    with pytest.raises(AssertionError, match=re.escape(message)):
        check_labels(fixture_copy)


def test_label_check_rejects_an_id_with_the_wrong_grade_number(fixture_copy):
    def change(entries):
        entries[0]["id"] = entries[0]["id"].replace("-0004-", "-0005-")

    rewrite(fixture_copy, "4", change)
    with pytest.raises(AssertionError, match="grade 4 entry 1"):
        check_labels(fixture_copy)
