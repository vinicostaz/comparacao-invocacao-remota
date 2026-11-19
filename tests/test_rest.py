import importlib

from fastapi.testclient import TestClient


def test_rest_contract(monkeypatch, tmp_path):
    monkeypatch.setenv("MUSIC_DB", str(tmp_path / "rest.db"))
    module = importlib.import_module("music_service.services.rest")
    module = importlib.reload(module)
    client = TestClient(module.app)

    user = client.post("/users", json={"name": "Caio", "age": 27}).json()
    song = client.post("/songs", json={"name": "Mar", "artist": "Duo"}).json()
    playlist = client.post(
        "/playlists",
        json={"user_id": user["id"], "name": "Viagem", "song_ids": [song["id"]]},
    )

    assert playlist.status_code == 201
    assert client.get(f"/playlists?user_id={user['id']}").json()[0]["name"] == "Viagem"
    assert client.get(f"/playlists/{playlist.json()['id']}/songs").json()[0]["name"] == "Mar"
    assert client.get(f"/playlists?song_id={song['id']}").json()[0]["name"] == "Viagem"

