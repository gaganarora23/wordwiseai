import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from tests.helpers import _insert, insert_child, insert_session_with_words, insert_word

VALID = {"nickname": "Sam", "grade": "3", "daily_goal": 5}
PROFILE_KEYS = {"id", "nickname", "grade", "daily_goal", "created_at", "updated_at"}


def count(db_session, table, where="TRUE", **params):
    return db_session.execute(text(f"SELECT count(*) FROM {table} WHERE {where}"), params).scalar_one()


def make_profile_with_progress(db_session):
    """A child with a session, an answer, a result and a mastery row; returns the child id."""
    child_id = insert_child(db_session)
    word_id = insert_word(db_session, word="progress")
    session_id = insert_session_with_words(
        db_session, child_id=child_id, word_ids=[word_id], status="completed", phase="quiz",
        current_position=1, completed_at=datetime.now(UTC),
    )
    _insert(db_session, "answers", {
        "session_id": session_id, "word_id": word_id, "selected_option": 1, "is_correct": True, "hint_used": False,
    })
    _insert(db_session, "quiz_results", {"session_id": session_id, "score": 1, "correct_count": 1, "incorrect_count": 0})
    _insert(db_session, "word_mastery", {"child_id": child_id, "word_id": word_id})
    return child_id


# --- create (#17) ---

def test_create_returns_201_and_a_flat_profile(client):
    response = client.post("/api/v1/profiles", json=VALID)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == PROFILE_KEYS
    assert (body["nickname"], body["grade"], body["daily_goal"]) == ("Sam", "3", 5)
    uuid.UUID(body["id"])


def test_created_profile_is_persisted(client, db_session):
    profile_id = client.post("/api/v1/profiles", json=VALID).json()["id"]
    assert count(db_session, "children", "id = :id", id=profile_id) == 1


@pytest.mark.parametrize("nickname", ["A", "x" * 20])
def test_nickname_of_one_and_twenty_characters_is_accepted(client, nickname):
    assert client.post("/api/v1/profiles", json={**VALID, "nickname": nickname}).status_code == 201


def test_nickname_is_trimmed(client):
    assert client.post("/api/v1/profiles", json={**VALID, "nickname": "  Sam  "}).json()["nickname"] == "Sam"


@pytest.mark.parametrize("grade", ["K", "1", "12"])
def test_kindergarten_and_grades_one_to_twelve_are_accepted(client, grade):
    assert client.post("/api/v1/profiles", json={**VALID, "grade": grade}).status_code == 201


@pytest.mark.parametrize("daily_goal", [5, 10])
def test_daily_goal_of_five_and_ten_is_accepted(client, daily_goal):
    assert client.post("/api/v1/profiles", json={**VALID, "daily_goal": daily_goal}).status_code == 201


@pytest.mark.parametrize("invalid", [
    {"nickname": ""},
    {"nickname": "   "},
    {"nickname": "x" * 21},
    {"grade": "13"},
    {"grade": "0"},
    {"grade": "k"},
    {"daily_goal": 7},
    {"daily_goal": 0},
    {"nickname": None},
    {"extra": "field"},
])
def test_invalid_create_returns_422_and_stores_nothing(client, db_session, invalid):
    response = client.post("/api/v1/profiles", json={**VALID, **invalid})

    assert response.status_code == 422
    assert count(db_session, "children") == 0


@pytest.mark.parametrize("missing", ["nickname", "grade", "daily_goal"])
def test_missing_field_returns_422(client, missing):
    body = {k: v for k, v in VALID.items() if k != missing}
    assert client.post("/api/v1/profiles", json=body).status_code == 422


def test_list_is_empty_when_there_are_no_profiles(client):
    response = client.get("/api/v1/profiles")
    assert response.status_code == 200
    assert response.json() == []


def test_list_returns_every_profile(client):
    names = ["Ann", "Ben", "Cy"]
    for name in names:
        client.post("/api/v1/profiles", json={**VALID, "nickname": name})

    listed = client.get("/api/v1/profiles").json()

    assert [p["nickname"] for p in listed] == names
    assert all(set(p) == PROFILE_KEYS for p in listed)


def test_get_returns_the_profile(client):
    created = client.post("/api/v1/profiles", json=VALID).json()
    response = client.get(f"/api/v1/profiles/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_id_returns_404(client):
    assert client.get(f"/api/v1/profiles/{uuid.uuid4()}").status_code == 404


def test_get_malformed_id_returns_422(client):
    assert client.get("/api/v1/profiles/not-a-uuid").status_code == 422


# --- update (#18) ---

def test_update_returns_the_changed_profile_and_moves_updated_at(client):
    created = client.post("/api/v1/profiles", json=VALID).json()
    changed = {"nickname": "Samantha", "grade": "K", "daily_goal": 10}

    response = client.put(f"/api/v1/profiles/{created['id']}", json=changed)

    assert response.status_code == 200
    body = response.json()
    assert (body["nickname"], body["grade"], body["daily_goal"]) == ("Samantha", "K", 10)
    assert body["id"] == created["id"]
    assert body["created_at"] == created["created_at"]
    assert body["updated_at"] > created["updated_at"]
    assert client.get(f"/api/v1/profiles/{created['id']}").json() == body


@pytest.mark.parametrize("invalid", [{"nickname": ""}, {"nickname": "x" * 21}, {"grade": "13"}, {"daily_goal": 7}, {"extra": 1}])
def test_invalid_update_returns_422_and_leaves_the_profile_unchanged(client, invalid):
    created = client.post("/api/v1/profiles", json=VALID).json()

    response = client.put(f"/api/v1/profiles/{created['id']}", json={**VALID, **invalid})

    assert response.status_code == 422
    assert client.get(f"/api/v1/profiles/{created['id']}").json() == created


def test_update_unknown_id_returns_404(client):
    assert client.put(f"/api/v1/profiles/{uuid.uuid4()}", json=VALID).status_code == 404


def test_update_malformed_id_returns_422(client):
    assert client.put("/api/v1/profiles/nope", json=VALID).status_code == 422


# --- delete (#18) ---

def test_delete_returns_204_then_get_returns_404(client):
    profile_id = client.post("/api/v1/profiles", json=VALID).json()["id"]

    response = client.delete(f"/api/v1/profiles/{profile_id}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/api/v1/profiles/{profile_id}").status_code == 404


def test_delete_unknown_id_returns_404(client):
    assert client.delete(f"/api/v1/profiles/{uuid.uuid4()}").status_code == 404


def test_deleting_twice_returns_404_the_second_time(client):
    profile_id = client.post("/api/v1/profiles", json=VALID).json()["id"]
    assert client.delete(f"/api/v1/profiles/{profile_id}").status_code == 204
    assert client.delete(f"/api/v1/profiles/{profile_id}").status_code == 404


def test_delete_removes_the_profiles_rows_and_leaves_another_profile_untouched(client, db_session):
    doomed = make_profile_with_progress(db_session)
    kept = make_profile_with_progress(db_session)
    db_session.commit()
    tables = ["sessions", "session_words", "answers", "quiz_results", "word_mastery"]
    before = {t: count(db_session, t) for t in tables}
    assert all(n == 2 for n in before.values())

    assert client.delete(f"/api/v1/profiles/{doomed}").status_code == 204

    db_session.expire_all()
    after = {t: count(db_session, t) for t in tables}
    assert after == {t: 1 for t in tables}
    assert count(db_session, "children") == 1
    assert count(db_session, "word_mastery", "child_id = :id", id=kept) == 1
    assert client.get(f"/api/v1/profiles/{kept}").status_code == 200
