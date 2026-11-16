"""Vocabulary validator: every rule, accepted and rejected values and boundaries. No database."""

import copy
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from app.services import vocabulary_validator as v
from app.services.vocabulary_validator import Failure, validate_file, validate_files

BACKEND = Path(__file__).resolve().parents[1]
BLANKS = [" ", "\t", "\n", "\r", "\f", "\v", " \t\n\r\f\v", " ", "　"]


def new_id():
    return str(uuid.uuid4())


def make_entry(**overrides):
    entry = {
        "id": new_id(),
        "word": "banana",
        "grade": "K",
        "definition": "A long yellow fruit with a soft inside.",
        "example": "I ate a banana with my lunch.",
        "syllables": "ba · na · na",
        "content_version": "2026.1",
        "options": [
            {"text": "A long yellow fruit", "correct": True},
            {"text": "A kind of shoe", "correct": False},
            {"text": "A farm animal", "correct": False},
            {"text": "A type of weather", "correct": False},
        ],
        "explanation": "A banana is a fruit you can peel and eat. Great job!",
    }
    entry.update(overrides)
    return entry


def write(tmp_path, content, name="grade-K.json"):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    elif isinstance(content, str):
        path.write_text(content, encoding="utf-8")
    else:
        path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    return path


def check(tmp_path, entry, name="grade-K.json"):
    return validate_file(write(tmp_path, [entry], name))


def fields(failures):
    return [f.field for f in failures]


def only_failure(failures, field):
    assert len(failures) == 1, [str(f) for f in failures]
    assert failures[0].field == field
    return failures[0]


def with_option(index, **changes):
    options = copy.deepcopy(make_entry()["options"])
    options[index].update(changes)
    return options


def accepted(tmp_path, **overrides):
    assert check(tmp_path, make_entry(**overrides)) == []


def rejected(tmp_path, field, **overrides):
    return only_failure(check(tmp_path, make_entry(**overrides)), field)


# --- Public interface and output ---


def test_valid_file_returns_no_failures(tmp_path):
    assert validate_file(write(tmp_path, [make_entry(), make_entry(word="cat", syllables="cat", example="A cat.")])) == []


def test_validate_files_of_valid_files_returns_no_failures(tmp_path):
    a = write(tmp_path, [make_entry()], "grade-K.json")
    b = write(tmp_path, [make_entry(grade="1")], "grade-1.json")
    assert validate_files([a, b]) == []


def test_validate_files_of_no_paths_returns_no_failures():
    assert validate_files([]) == []


def test_validate_file_accepts_a_string_path(tmp_path):
    assert validate_file(str(write(tmp_path, [make_entry()]))) == []


def test_entry_failure_string_has_file_index_id_field_and_message(tmp_path):
    entry = make_entry(grade="3", word="cat", syllables="cat", example="A cat.")
    path = write(tmp_path, [make_entry(), entry])
    (failure,) = validate_file(path)
    assert isinstance(failure, Failure)
    assert (failure.file, failure.entry_index, failure.entry_id, failure.field) == (str(path), 1, entry["id"], "grade")
    assert str(failure) == f"{path}: entry 1 [{entry['id']}]: grade: {failure.message}"


def test_entry_failure_string_omits_id_when_there_is_no_usable_id(tmp_path):
    path = write(tmp_path, [make_entry(id=5)])
    (failure,) = validate_file(path)
    assert failure.entry_id is None
    assert str(failure) == f"{path}: entry 0: id: {failure.message}"


def test_entry_id_is_kept_when_it_is_a_string_even_if_invalid(tmp_path):
    (failure,) = check(tmp_path, make_entry(id="banana"))
    assert failure.entry_id == "banana"
    assert "[banana]" in str(failure)


def test_file_failure_string_format(tmp_path):
    path = tmp_path / "grade-K.json"
    (failure,) = validate_file(path)
    assert failure.entry_index is None and failure.field is None and failure.entry_id is None
    assert str(failure) == f"{path}: file: {failure.message}"


def test_failures_are_ordered_by_file_then_entry_then_field_order(tmp_path):
    first = make_entry(explanation="", word="cat1", example="x")
    second = make_entry(id="nope", content_version="")
    a = write(tmp_path, [first, second], "grade-K.json")
    b = write(tmp_path, [make_entry(definition="")], "grade-1.json")
    out = [(Path(f.file).name, f.entry_index, f.field) for f in validate_files([a, b])]
    assert out == [
        ("grade-K.json", 0, "word"), ("grade-K.json", 0, "explanation"),
        ("grade-K.json", 1, "id"), ("grade-K.json", 1, "content_version"),
        ("grade-1.json", 0, "grade"), ("grade-1.json", 0, "definition"),
    ]


def test_failure_order_follows_input_file_order_not_name_order(tmp_path):
    a = write(tmp_path, [make_entry(grade="1", word="")], "grade-1.json")
    b = write(tmp_path, [make_entry(word="")], "grade-K.json")
    assert [Path(f.file).name for f in validate_files([b, a])] == ["grade-K.json", "grade-1.json"]


def test_five_broken_places_give_exactly_five_failures(tmp_path):
    entries = [
        make_entry(word="cat1"), make_entry(word="cat", syllables="cat", example="A cat.", definition=""),
        make_entry(word="dog", syllables="dog", example="A dog.", content_version="v 1"),
        make_entry(word="pig", syllables="pig", example="A pig.", explanation=" "),
        make_entry(word="cow", syllables="cow", example="A cow.", options=[]),
    ]
    failures = validate_file(write(tmp_path, entries))
    assert len(failures) == 5
    assert [f.entry_index for f in failures] == [0, 1, 2, 3, 4]


def test_a_field_breaking_several_rules_yields_one_failure(tmp_path):
    only_failure(check(tmp_path, make_entry(definition=" " * 400)), "definition")


def test_an_entry_with_several_bad_fields_yields_one_failure_per_field(tmp_path):
    failures = check(tmp_path, make_entry(word="", definition="", explanation=""))
    assert fields(failures) == ["word", "definition", "explanation"]


def test_validator_never_raises_for_missing_path_directory_or_odd_input(tmp_path):
    assert len(validate_file(tmp_path / "grade-K.json")) == 1
    assert len(validate_file(tmp_path)) == 1


@pytest.mark.skipif(os.name != "posix" or os.geteuid() == 0, reason="needs POSIX permissions and a non-root user")
def test_unreadable_file_gives_one_file_level_failure(tmp_path):
    path = write(tmp_path, [make_entry()])
    path.chmod(0)
    try:
        (failure,) = validate_file(path)
    finally:
        path.chmod(0o644)
    assert failure.entry_index is None


# --- File-level rules ---


def test_nonexistent_path_gives_one_file_level_failure(tmp_path):
    (failure,) = validate_file(tmp_path / "grade-K.json")
    assert failure.entry_index is None and "does not exist" in failure.message


def test_directory_instead_of_file_gives_one_file_level_failure(tmp_path):
    folder = tmp_path / "grade-K.json"
    folder.mkdir()
    (failure,) = validate_file(folder)
    assert failure.entry_index is None


@pytest.mark.parametrize("name", ["grade-K.json", "grade-1.json", "grade-9.json", "grade-10.json", "grade-12.json", "fixtures/grade-5.json"])
def test_valid_file_names_are_accepted(tmp_path, name):
    grade = re.search(r"grade-(.+)\.json", name).group(1)
    assert validate_file(write(tmp_path, [make_entry(grade=grade)], name)) == []


@pytest.mark.parametrize("name", ["grade-k.json", "grade-01.json", "grade-13.json", "grade-0.json", "K.json", "grade-3.JSON", "grade-.json", "grade-K.json.txt", "words.json", "fixtures/grade-13.json"])
def test_invalid_file_names_give_one_file_level_failure_and_entries_are_still_checked(tmp_path, name):
    failures = validate_file(write(tmp_path, [make_entry(grade="K"), make_entry(word="")], name))
    file_level = [f for f in failures if f.entry_index is None]
    assert len(file_level) == 1 and "grade-" in file_level[0].message
    assert [(f.entry_index, f.field) for f in failures if f.entry_index is not None] == [(1, "word")]


def test_bad_file_name_skips_the_grade_match_rule_but_not_the_grade_value_rule(tmp_path):
    failures = validate_file(write(tmp_path, [make_entry(grade="K"), make_entry(grade="13", word="cat", syllables="cat", example="A cat.")], "grade-13.json"))
    assert [(f.entry_index, f.field) for f in failures] == [(None, None), (1, "grade")]


def test_invalid_utf8_gives_one_file_level_failure_and_no_entry_checks(tmp_path):
    (failure,) = validate_file(write(tmp_path, b'[{"word": "\xff\xfe"}]'))
    assert failure.entry_index is None and "UTF-8" in failure.message


def test_bom_gives_one_file_level_failure_and_no_entry_checks(tmp_path):
    (failure,) = validate_file(write(tmp_path, b"\xef\xbb\xbf" + json.dumps([make_entry(word="")]).encode()))
    assert failure.entry_index is None and "BOM" in failure.message


@pytest.mark.parametrize("content", [b"", b"   \n\t ", b'[{"id": 1,}]', b'[1,]', b"[", b"nope", b"[NaN]"])
def test_empty_whitespace_or_malformed_json_gives_one_not_valid_json_failure(tmp_path, content):
    (failure,) = validate_file(write(tmp_path, content))
    assert failure.entry_index is None and "not valid JSON" in failure.message


def test_deeply_nested_json_gives_a_failure_not_an_exception(tmp_path):
    (failure,) = validate_file(write(tmp_path, "[" * 100000))
    assert failure.entry_index is None


@pytest.mark.parametrize("content", ['{"a": 1}', '"x"', "5", "null", "true"])
def test_top_level_that_is_not_an_array_gives_one_failure(tmp_path, content):
    (failure,) = validate_file(write(tmp_path, content))
    assert failure.entry_index is None and "array" in failure.message


def test_empty_array_gives_a_no_entries_failure(tmp_path):
    (failure,) = validate_file(write(tmp_path, "[]"))
    assert failure.entry_index is None and "no entries" in failure.message


@pytest.mark.parametrize("element", ["5", "null", '"x"', "[]", "true"])
def test_array_element_that_is_not_an_object_fails_and_the_rest_are_checked(tmp_path, element):
    content = f"[{json.dumps(make_entry())}, {element}, {json.dumps(make_entry(word=''))}]"
    failures = validate_file(write(tmp_path, content))
    assert [(f.entry_index, f.field) for f in failures] == [(1, None), (2, "word")]


def test_repeated_key_in_an_entry_names_the_entry_and_the_key(tmp_path):
    good = json.dumps(make_entry())
    text = '[' + good + ', {"word": "cat", "word": "dog"}]'
    failures = validate_file(write(tmp_path, text))
    dup = [f for f in failures if f.field == "word"]
    assert len(dup) == 1 and dup[0].entry_index == 1 and "duplicate key" in dup[0].message


def test_repeated_key_is_a_failure_even_when_the_last_value_is_valid(tmp_path):
    entry = json.dumps(make_entry())
    text = entry[:-1] + ', "word": "banana"}'
    failures = validate_file(write(tmp_path, "[" + text + "]"))
    assert [(f.field, f.message) for f in failures] == [("word", "duplicate key")]


def test_repeated_key_inside_an_option_object_fails(tmp_path):
    text = json.dumps(make_entry()).replace('{"text": "A kind of shoe", "correct": false}', '{"text": "A kind of shoe", "text": "x", "correct": false}')
    failures = validate_file(write(tmp_path, "[" + text + "]"))
    assert [(f.field, f.message) for f in failures] == [("options[1].text", "duplicate key")]


# --- Keys ---


@pytest.mark.parametrize("key", v.KEYS)
def test_missing_key_fails_naming_the_key_as_required(tmp_path, key):
    entry = make_entry()
    del entry[key]
    f = only_failure(check(tmp_path, entry), key)
    assert "required" in f.message


def test_several_missing_keys_give_several_failures(tmp_path):
    entry = make_entry()
    for key in ("word", "example", "explanation"):
        del entry[key]
    assert fields(check(tmp_path, entry)) == ["word", "example", "explanation"]


@pytest.mark.parametrize("key", ["hint", "question", "Word", "question_id", ""])
def test_unknown_entry_key_fails_naming_it(tmp_path, key):
    f = only_failure(check(tmp_path, make_entry(**{key: "x"})), key)
    assert "unknown key" in f.message


@pytest.mark.parametrize("key", ["hint", "id", "Text"])
def test_unknown_key_in_an_option_object_fails(tmp_path, key):
    f = only_failure(check(tmp_path, make_entry(options=with_option(2, **{key: "x"}))), f"options[2].{key}")
    assert "unknown key" in f.message


def test_repeated_key_inside_an_unknown_keys_object_fails(tmp_path):
    text = json.dumps(make_entry())[:-1] + ', "extra": {"a": 1, "a": 2}}'
    assert sorted(fields(validate_file(write(tmp_path, "[" + text + "]")))) == ["extra", "extra.a"]


# --- id ---


def test_lowercase_v4_uuid_id_is_accepted(tmp_path):
    accepted(tmp_path, id="0b8f5c3e-6a1d-4f27-9c55-3d2f7e8a1b40")


@pytest.mark.parametrize("bad", [
    "0B8F5C3E-6A1D-4F27-9C55-3D2F7E8A1B40", "{0b8f5c3e-6a1d-4f27-9c55-3d2f7e8a1b40}",
    "0b8f5c3e6a1d4f279c553d2f7e8a1b40", "urn:uuid:0b8f5c3e-6a1d-4f27-9c55-3d2f7e8a1b40",
    "0b8f5c3e-6a1d-4f27-9c55-3d2f7e8a1b4", "0b8f5c3e-6a1d-4f27-9c55-3d2f7e8a1b400",
    "00000000-0000-0000-0000-000000000000", 5, None, "", "banana", True,
    "0b8f5c3e-6a1d-4f27-9c55-3d2f7e8a1b4g", "0b8f5c3e-6a1d-4f27-9c55-3d2f7e8a1b40\n", " 0b8f5c3e-6a1d-4f27-9c55-3d2f7e8a1b40",
])
def test_invalid_id_is_rejected(tmp_path, bad):
    rejected(tmp_path, "id", id=bad)


def test_id_length_boundaries_are_35_and_37_rejected_36_accepted(tmp_path):
    good = new_id()
    assert len(good) == 36
    accepted(tmp_path, id=good)
    rejected(tmp_path, "id", id=good[:-1])
    rejected(tmp_path, "id", id=good + "0")


def test_duplicate_id_in_a_file_fails_on_later_entries_and_names_the_first(tmp_path):
    shared = new_id()
    entries = [make_entry(id=shared), make_entry(id=shared, word="cat", syllables="cat", example="A cat."), make_entry(id=shared, word="dog", syllables="dog", example="A dog.")]
    failures = validate_file(write(tmp_path, entries))
    assert [(f.entry_index, f.field) for f in failures] == [(1, "id"), (2, "id")]
    assert all("entry 0" in f.message for f in failures)


def test_duplicate_id_across_files_fails_on_the_later_file_and_names_the_earlier(tmp_path):
    shared = new_id()
    a = write(tmp_path, [make_entry(id=shared)], "grade-K.json")
    b = write(tmp_path, [make_entry(id=new_id(), grade="1"), make_entry(id=shared, grade="1", word="cat", syllables="cat", example="A cat.")], "grade-1.json")
    (failure,) = validate_files([a, b])
    assert (failure.file, failure.entry_index, failure.field) == (str(b), 1, "id")
    assert str(a) in failure.message and "entry 0" in failure.message
    (failure,) = validate_files([b, a])
    assert failure.file == str(a)  # the later file in input order is the one reported


def test_cross_file_duplicate_failure_sits_in_entry_order_with_the_other_failures(tmp_path):
    shared = new_id()
    a = write(tmp_path, [make_entry(id=shared)], "grade-K.json")
    b = write(tmp_path, [make_entry(grade="1", word=""), make_entry(id=shared, grade="1")], "grade-1.json")
    assert [(f.entry_index, f.field) for f in validate_files([a, b])] == [(0, "word"), (1, "id")]


def test_duplicate_id_comparison_is_exact_so_uppercase_is_an_invalid_id_not_a_duplicate(tmp_path):
    shared = new_id()
    failures = validate_file(write(tmp_path, [make_entry(id=shared), make_entry(id=shared.upper(), word="cat", syllables="cat", example="A cat.")]))
    assert [(f.entry_index, f.field) for f in failures] == [(1, "id")]
    assert "duplicate" not in failures[0].message


# --- word ---


@pytest.mark.parametrize("word,syllables", [
    ("a", "a"), ("banana", "ba · na · na"), ("Banana", "ba · na · na"), ("ice-cream", "ice · cream"),
    ("don't", "don · t"), ("ice cream", "ice · cream"), ("x" * 40, "x" * 40), ("a-b-c", "a · b · c"),
])
def test_valid_word_is_accepted(tmp_path, word, syllables):
    accepted(tmp_path, word=word, syllables=syllables, example=f"I like {word}.")


@pytest.mark.parametrize("bad", ["", " ", " cat", "cat ", "ca  t", "cat1", "1", "-cat", "cat-", "ca--t", "ca'-t", "café", "naïve", None, 5, "x" * 41, "cat\n", "ca\tt", "ca_t", ["cat"]])
def test_invalid_word_is_rejected(tmp_path, bad):
    rejected(tmp_path, "word", word=bad, syllables="cat", example="A cat.")


def test_duplicate_word_in_a_file_is_case_insensitive_and_names_the_first(tmp_path):
    entries = [make_entry(), make_entry(), make_entry(word="BANANA")]
    entries[1]["id"] = new_id()
    entries[2]["id"] = new_id()
    entries[2]["syllables"] = "BA · NA · NA"
    failures = validate_file(write(tmp_path, entries))
    assert [(f.entry_index, f.field) for f in failures] == [(1, "word"), (2, "word")]
    assert all("entry 0" in f.message for f in failures)


def test_same_word_in_two_files_is_not_flagged(tmp_path):
    a = write(tmp_path, [make_entry()], "grade-K.json")
    b = write(tmp_path, [make_entry(grade="1")], "grade-1.json")
    assert validate_files([a, b]) == []


# --- grade ---


@pytest.mark.parametrize("grade", ["K", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"])
def test_grade_matching_the_file_name_is_accepted(tmp_path, grade):
    assert check(tmp_path, make_entry(grade=grade), f"grade-{grade}.json") == []


@pytest.mark.parametrize("bad", ["K", 3, "03", "k", "Kindergarten", "13", "0", "", None, "3 ", "4", True])
def test_invalid_grade_in_a_grade_3_file_is_rejected(tmp_path, bad):
    only_failure(check(tmp_path, make_entry(grade=bad), "grade-3.json"), "grade")


def test_grade_outside_k_to_12_says_invalid_even_when_the_file_name_matches_it(tmp_path):
    failures = check(tmp_path, make_entry(grade="13"), "grade-13.json")
    f = only_failure([x for x in failures if x.entry_index is not None], "grade")
    assert "one of" in f.message


# --- definition, example, explanation (shared text rules) ---


@pytest.mark.parametrize("key", ["definition", "example", "explanation"])
def test_text_field_boundaries(tmp_path, key):
    extra = {"example": "banana "}.get(key, "")
    ok = (extra + "a" * 300)[:300]
    accepted(tmp_path, **{key: ok})
    accepted(tmp_path, **{key: "banana" if key == "example" else "a"})
    rejected(tmp_path, key, **{key: (extra + "a" * 301)[:301]})
    rejected(tmp_path, key, **{key: ""})


@pytest.mark.parametrize("key", ["definition", "example", "explanation"])
@pytest.mark.parametrize("bad", [None, 5, True, ["x"], {"a": 1}])
def test_text_field_of_wrong_type_is_rejected(tmp_path, key, bad):
    rejected(tmp_path, key, **{key: bad})


@pytest.mark.parametrize("key", ["definition", "example", "explanation"])
@pytest.mark.parametrize("bad", ["\ttext", "text\n", " text", "text ", "a\nb", "a\rb", "a\tb", "a\u0000b", "\u00a0text"])
def test_text_field_with_edge_whitespace_or_control_characters_is_rejected(tmp_path, key, bad):
    # Examples must contain the word, so rejection is attributed to the whitespace rule.
    value = bad.replace("text", "banana").replace("a\nb", "banana\n").replace("a\rb", "banana\r").replace("a\tb", "banana\t").replace("a\u0000b", "banana\u0000")
    if "banana" not in value:
        value = "banana" + value
    f = rejected(tmp_path, key, **{key: value})
    assert "word" not in f.message


@pytest.mark.parametrize("key", ["definition", "example", "explanation"])
def test_text_field_may_contain_interior_spaces(tmp_path, key):
    accepted(tmp_path, **{key: "a banana in the box"})


@pytest.mark.parametrize("example", ["Banana", "I ate a banana.", "I ate a BANANA.", "bananas are good", "A banana"])
def test_example_containing_the_word_case_insensitively_is_accepted(tmp_path, example):
    accepted(tmp_path, example=example)


@pytest.mark.parametrize("example", ["I ate a fruit.", "banan", "ba na na"])
def test_example_without_the_word_is_rejected(tmp_path, example):
    f = rejected(tmp_path, "example", example=example)
    assert "word" in f.message


def test_example_matches_a_multi_word_word_as_a_whole(tmp_path):
    accepted(tmp_path, word="ice cream", syllables="ice · cream", example="I like ice cream.")
    rejected(tmp_path, "example", word="ice cream", syllables="ice · cream", example="I like ice.")


# --- syllables ---


@pytest.mark.parametrize("word,syllables", [("cat", "cat"), ("banana", "ba · na · na"), ("banana", "BA · na · NA"), ("banana", "ba · nana"), ("ice-cream", "ice · cream"), ("ice-cream", "i · ce · cre · am")])
def test_valid_syllables_are_accepted(tmp_path, word, syllables):
    accepted(tmp_path, word=word, syllables=syllables, example=f"A {word}.")


@pytest.mark.parametrize("bad", ["ba-na-na", "ba . na . na", "ba·na·na", "ba  ·  na", "ba · · na", "· na", "ba · ", " ba · na · na", "ba · na · na ", "ba1 · na · na", "", None, 5, "ba · na", "ba · na · na · na", "ba · na\n", "ba ·\tna · na", "ba · na · nä"])
def test_invalid_syllables_are_rejected(tmp_path, bad):
    rejected(tmp_path, "syllables", syllables=bad)


def test_syllables_that_do_not_spell_the_word_are_rejected(tmp_path):
    f = rejected(tmp_path, "syllables", syllables="ba · na")
    assert "word" in f.message


def hyphenated(letters):
    """A word of 15 hyphen-joined parts and its syllables string; the syllables are 3 * 14 + letters long."""
    parts = ["a"] * 14 + ["a" * (letters - 14)]
    return "-".join(parts), " · ".join(parts)


def test_syllables_of_exactly_60_characters_are_accepted(tmp_path):
    word, syllables = hyphenated(18)
    assert len(syllables) == 60 and len(word) <= 40
    accepted(tmp_path, word=word, syllables=syllables, example=word)


def test_syllables_of_61_characters_are_rejected(tmp_path):
    word, syllables = hyphenated(19)
    assert len(syllables) == 61 and len(word) <= 40
    f = rejected(tmp_path, "syllables", word=word, syllables=syllables, example=word)
    assert "60" in f.message


# --- content_version ---


@pytest.mark.parametrize("ok", ["2026.1", "fixture-1", "a", "1", "A_b.c-d", "x" * 32])
def test_valid_content_version_is_accepted(tmp_path, ok):
    accepted(tmp_path, content_version=ok)


@pytest.mark.parametrize("bad", ["", " ", ".1", "v 1", "x" * 33, None, 1, "-1", "_a", "v1\n", "v\t1", "é1"])
def test_invalid_content_version_is_rejected(tmp_path, bad):
    rejected(tmp_path, "content_version", content_version=bad)


# --- options ---


def test_four_options_with_one_correct_are_accepted(tmp_path):
    accepted(tmp_path)


@pytest.mark.parametrize("position", [0, 1, 2, 3])
def test_the_correct_option_may_be_in_any_position(tmp_path, position):
    options = [{"text": f"Option number {i}", "correct": i == position} for i in range(4)]
    accepted(tmp_path, options=options)


@pytest.mark.parametrize("count", [0, 1, 2, 3, 5, 6])
def test_wrong_number_of_options_is_rejected(tmp_path, count):
    options = [{"text": f"Option number {i}", "correct": i == 0} for i in range(count)]
    rejected(tmp_path, "options", options=options)


@pytest.mark.parametrize("bad", [None, "options", 4, {"text": "x", "correct": True}, True])
def test_options_that_are_not_an_array_are_rejected(tmp_path, bad):
    rejected(tmp_path, "options", options=bad)


@pytest.mark.parametrize("correct_flags", [[False] * 4, [True, True, False, False], [True] * 4, [True, True, True, False]])
def test_zero_or_several_correct_options_are_rejected(tmp_path, correct_flags):
    options = [{"text": f"Option number {i}", "correct": flag} for i, flag in enumerate(correct_flags)]
    f = rejected(tmp_path, "options", options=options)
    assert "exactly one" in f.message


@pytest.mark.parametrize("bad", [0, 1, "true", "false", None, "yes", [True]])
def test_correct_must_be_a_json_boolean(tmp_path, bad):
    only_failure(check(tmp_path, make_entry(options=with_option(1, correct=bad))), "options[1].correct")


@pytest.mark.parametrize("bad", [None, 5, True, ["x"], {"a": 1}])
def test_option_text_of_wrong_type_is_rejected(tmp_path, bad):
    only_failure(check(tmp_path, make_entry(options=with_option(3, text=bad))), "options[3].text")


@pytest.mark.parametrize("key", ["text", "correct"])
def test_option_missing_a_key_fails_on_that_key(tmp_path, key):
    options = make_entry()["options"]
    del options[2][key]
    f = only_failure(check(tmp_path, make_entry(options=options)), f"options[2].{key}")
    assert "required" in f.message


@pytest.mark.parametrize("bad", [5, None, "x", [], True])
def test_option_that_is_not_an_object_is_rejected(tmp_path, bad):
    options = make_entry()["options"]
    options[1] = bad
    only_failure(check(tmp_path, make_entry(options=options)), "options[1]")


def test_option_text_boundaries(tmp_path):
    accepted(tmp_path, options=with_option(0, text="a" * 150))
    accepted(tmp_path, options=with_option(0, text="a"))
    only_failure(check(tmp_path, make_entry(options=with_option(0, text="a" * 151))), "options[0].text")
    only_failure(check(tmp_path, make_entry(options=with_option(0, text=""))), "options[0].text")


@pytest.mark.parametrize("bad", ["\ttext", "text\n", " text", "text ", "a\nb", "a\rb", "a\tb"])
def test_option_text_with_edge_whitespace_or_control_characters_is_rejected(tmp_path, bad):
    only_failure(check(tmp_path, make_entry(options=with_option(2, text=bad))), "options[2].text")


def test_option_text_may_contain_interior_spaces(tmp_path):
    accepted(tmp_path, options=with_option(2, text="a farm animal"))


@pytest.mark.parametrize("duplicate", ["A KIND OF SHOE", "a kind of shoe"])
def test_duplicate_option_text_fails_on_the_later_option_and_names_the_earlier(tmp_path, duplicate):
    options = make_entry()["options"]
    options[3]["text"] = duplicate
    f = only_failure(check(tmp_path, make_entry(options=options)), "options[3].text")
    assert "options[1]" in f.message


def test_duplicate_option_text_ignores_surrounding_whitespace_but_that_is_its_own_failure(tmp_path):
    options = make_entry()["options"]
    options[3]["text"] = " A kind of shoe"
    only_failure(check(tmp_path, make_entry(options=options)), "options[3].text")


def test_several_bad_options_each_give_a_failure(tmp_path):
    options = make_entry()["options"]
    options[0]["text"] = ""
    options[2]["correct"] = 1
    assert fields(check(tmp_path, make_entry(options=options))) == ["options[0].text", "options[2].correct"]


# --- blank values, every kind ---


@pytest.mark.parametrize("blank", BLANKS)
@pytest.mark.parametrize("field", ["word", "definition", "example", "syllables", "content_version", "explanation"])
def test_blank_value_is_rejected_for_every_text_field(tmp_path, field, blank):
    only_failure(check(tmp_path, make_entry(**{field: blank})), field)


@pytest.mark.parametrize("blank", BLANKS)
def test_blank_option_text_is_rejected(tmp_path, blank):
    only_failure(check(tmp_path, make_entry(options=with_option(1, text=blank))), "options[1].text")


@pytest.mark.parametrize("field", ["word", "syllables", "content_version"])
@pytest.mark.parametrize("bad", ["a\nb", "a\tb", "a\rb"])
def test_interior_newline_or_tab_is_rejected_in_single_line_fields(tmp_path, field, bad):
    rejected(tmp_path, field, **{field: bad})


# --- README ---


def test_readme_example_entry_validates(tmp_path):
    readme = (BACKEND / "data" / "README.md").read_text(encoding="utf-8")
    block = re.search(r"```json\n(.*?)\n```", readme, re.S).group(1)
    path = write(tmp_path, "[" + block + "]", "grade-K.json")
    assert validate_file(path) == []


# --- Command line ---


def run_cli(*args, env_extra=None, drop=(), cwd=BACKEND):
    env = {k: val for k, val in os.environ.items() if k not in drop}
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, "-m", "app.services.vocabulary_validator", *args],
        capture_output=True, text=True, cwd=cwd, env=env, timeout=60,
    )


def test_cli_valid_file_exits_0_with_ok_line(tmp_path):
    path = write(tmp_path, [make_entry(), make_entry(word="cat", syllables="cat", example="A cat.")])
    result = run_cli(str(path))
    assert result.returncode == 0
    assert result.stdout == "OK: 1 file(s), 2 entry(ies)\n"
    assert result.stderr == ""


def test_cli_invalid_file_exits_1_with_failure_lines_and_summary_on_stderr(tmp_path):
    entry = make_entry(word="cat1", explanation="")
    path = write(tmp_path, [entry])
    result = run_cli(str(path))
    assert result.returncode == 1
    lines = result.stderr.splitlines()
    assert [str(f) for f in validate_file(path)] == lines[:-1]
    assert lines[-1] == "FAILED: 2 failure(s) in 1 file(s)"
    assert str(path) in lines[0] and "word" in lines[0] and entry["id"] in lines[0]


def test_cli_counts_failing_files_in_the_summary(tmp_path):
    good = write(tmp_path, [make_entry()], "grade-K.json")
    bad1 = write(tmp_path, [make_entry(grade="1", word="")], "grade-1.json")
    bad2 = write(tmp_path, [make_entry(grade="2", word="")], "grade-2.json")
    result = run_cli(str(good), str(bad1), str(bad2))
    assert result.returncode == 1
    assert result.stderr.splitlines()[-1] == "FAILED: 2 failure(s) in 2 file(s)"


def test_cli_reports_cross_file_duplicate_ids(tmp_path):
    shared = new_id()
    a = write(tmp_path, [make_entry(id=shared)], "grade-K.json")
    b = write(tmp_path, [make_entry(id=shared, grade="1")], "grade-1.json")
    result = run_cli(str(a), str(b))
    assert result.returncode == 1 and "duplicate id" in result.stderr


def test_cli_directory_is_searched_recursively_and_sorted(tmp_path):
    write(tmp_path, [make_entry(grade="2", word="")], "grade-2.json")
    write(tmp_path, [make_entry(grade="1", word="")], "sub/grade-1.json")
    write(tmp_path, [make_entry()], "grade-K.json")
    (tmp_path / "notes.txt").write_text("ignored")
    result = run_cli(str(tmp_path))
    assert result.returncode == 1
    failing = [line.split(":")[0] for line in result.stderr.splitlines()[:-1]]
    assert failing == sorted(failing) and len(failing) == 2
    assert result.stderr.splitlines()[-1] == "FAILED: 2 failure(s) in 2 file(s)"


def test_cli_valid_directory_counts_every_file(tmp_path):
    write(tmp_path, [make_entry()], "grade-K.json")
    write(tmp_path, [make_entry(grade="1")], "sub/grade-1.json")
    assert run_cli(str(tmp_path)).stdout == "OK: 2 file(s), 2 entry(ies)\n"


def test_cli_directory_without_json_files_exits_2_naming_the_path(tmp_path):
    (tmp_path / "notes.txt").write_text("x")
    result = run_cli(str(tmp_path))
    assert result.returncode == 2
    assert str(tmp_path) in result.stderr and "no JSON files" in result.stderr


def test_cli_missing_path_exits_2_naming_the_path(tmp_path):
    missing = tmp_path / "nope.json"
    result = run_cli(str(missing))
    assert result.returncode == 2 and str(missing) in result.stderr


def test_cli_with_no_arguments_validates_backend_data_wherever_it_runs(tmp_path):
    from_backend = run_cli()
    from_elsewhere = run_cli(cwd=tmp_path, env_extra={"PYTHONPATH": str(BACKEND)})
    assert from_backend.returncode == from_elsewhere.returncode
    assert from_backend.stderr == from_elsewhere.stderr
    assert str(v.DATA_DIR) == str(BACKEND / "data")
    # data/ may hold no vocabulary yet (exit 2) or valid files (exit 0), never failures
    assert from_backend.returncode in (0, 2)


def test_cli_usage_error_exits_2():
    result = run_cli("--no-such-option")
    assert result.returncode == 2 and "usage" in result.stderr.lower()


def test_cli_runs_without_a_database_url(tmp_path):
    path = write(tmp_path, [make_entry()])
    result = run_cli(str(path), drop=("DATABASE_URL", "CORS_ORIGINS"))
    assert result.returncode == 0 and result.stdout.startswith("OK:")


def test_module_imports_nothing_that_needs_a_database():
    code = (
        "import sys, app.services.vocabulary_validator;"
        "bad = [m for m in sys.modules if m in ('app.db', 'app.config', 'sqlalchemy', 'psycopg') or m.startswith(('sqlalchemy.', 'psycopg.'))];"
        "print(bad)"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=BACKEND, env={k: val for k, val in os.environ.items() if k != "DATABASE_URL"})
    assert result.returncode == 0 and result.stdout.strip() == "[]", result.stderr
    source = Path(v.__file__).read_text()
    assert not re.search(r"^\s*(from|import)\s+(app\.(db|config)|sqlalchemy|psycopg)", source, re.M)


def test_grades_match_the_model():
    from app.models.child import GRADES

    assert v.GRADES == GRADES
