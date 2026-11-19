from pathlib import Path

import pytest

from music_service.repository import MusicRepository, NotFoundError, ValidationError


@pytest.fixture
def repository(tmp_path: Path) -> MusicRepository:
    repo = MusicRepository(tmp_path / "test.db")
    repo.initialize()
    return repo


def test_crud_and_relationship_queries(repository: MusicRepository) -> None:
    user = repository.create_user("Ana", 25)
    song_a = repository.create_song("Aurora", "Banda A")
    song_b = repository.create_song("Brisa", "Banda B")
    playlist = repository.create_playlist(user["id"], "Favoritas", [song_a["id"], song_b["id"]])

    assert repository.list_playlists_by_user(user["id"])[0]["id"] == playlist["id"]
    assert {song["id"] for song in repository.list_songs_by_playlist(playlist["id"])} == {
        song_a["id"], song_b["id"]
    }
    assert repository.list_playlists_by_song(song_a["id"])[0]["id"] == playlist["id"]

    updated = repository.update_playlist(playlist["id"], user["id"], "Calmas", [song_b["id"]])
    assert updated["name"] == "Calmas"
    assert [song["id"] for song in updated["songs"]] == [song_b["id"]]

    assert repository.delete_playlist(playlist["id"])
    assert repository.delete_song(song_a["id"])
    assert repository.delete_song(song_b["id"])
    assert repository.delete_user(user["id"])


def test_playlist_requires_at_least_one_song(repository: MusicRepository) -> None:
    user = repository.create_user("Bia", 31)
    with pytest.raises(ValidationError):
        repository.create_playlist(user["id"], "Vazia", [])


def test_not_found_is_explicit(repository: MusicRepository) -> None:
    with pytest.raises(NotFoundError):
        repository.get_user(999)

