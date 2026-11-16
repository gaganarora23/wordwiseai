import uuid

import pytest

from tests.helpers import insert_word


def test_returns_only_words_of_the_grade_with_options(client, db_session):
    insert_word(db_session, word="cat", grade="1", option_1="x", option_2="y", option_3="z", option_4="w", correct_option=3)
    insert_word(db_session, word="algebra", grade="8")
    db_session.commit()

    response = client.get("/api/v1/grades/1/words")

    assert response.status_code == 200
    (item,) = response.json()
    assert item["word"] == "cat" and item["grade"] == "1"
    assert set(item) == {"id", "word", "grade", "definition", "example", "syllables", "content_version", "options", "explanation"}
    assert [o["text"] for o in item["options"]] == ["x", "y", "z", "w"]
    assert [o["is_correct"] for o in item["options"]] == [False, False, True, False]


def test_kindergarten_is_supported(client, db_session):
    insert_word(db_session, word="dog", grade="K")
    db_session.commit()
    assert [w["word"] for w in client.get("/api/v1/grades/K/words").json()] == ["dog"]


def test_grade_without_words_returns_empty_list(client):
    response = client.get("/api/v1/grades/12/words")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("grade", ["13", "-1", "abc", "0", "k"])
def test_unknown_grade_returns_422(client, grade):
    assert client.get(f"/api/v1/grades/{grade}/words").status_code == 422


def test_results_are_ordered_by_id(client, db_session):
    ids = sorted(uuid.uuid4() for _ in range(3))
    for word_id, name in zip(reversed(ids), ["c", "b", "a"]):
        insert_word(db_session, id=word_id, word=name, grade="2")
    db_session.commit()

    returned = [w["id"] for w in client.get("/api/v1/grades/2/words").json()]

    assert returned == [str(i) for i in ids]
