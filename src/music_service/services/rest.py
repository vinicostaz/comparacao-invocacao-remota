from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from music_service.config import database_path
from music_service.repository import MusicRepository, NotFoundError, ValidationError


class UserInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    age: int = Field(ge=0, le=130)


class SongInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    artist: str = Field(min_length=1, max_length=160)


class PlaylistInput(BaseModel):
    user_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=160)
    song_ids: list[int] = Field(min_length=1)


repository = MusicRepository(database_path())
repository.initialize()
app = FastAPI(
    title="Servico de Streaming de Musicas - REST",
    version="1.0.0",
    description="Implementacao REST usada na comparacao entre protocolos.",
)


def translate_error(error: ValueError) -> HTTPException:
    if isinstance(error, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "protocol": "REST"}


@app.get("/users")
def list_users() -> list[dict]:
    return repository.list_users()


@app.get("/users/{user_id}")
def get_user(user_id: int) -> dict:
    try:
        return repository.get_user(user_id)
    except ValueError as error:
        raise translate_error(error) from error


@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(payload: UserInput) -> dict:
    try:
        return repository.create_user(payload.name, payload.age)
    except ValueError as error:
        raise translate_error(error) from error


@app.put("/users/{user_id}")
def update_user(user_id: int, payload: UserInput) -> dict:
    try:
        return repository.update_user(user_id, payload.name, payload.age)
    except ValueError as error:
        raise translate_error(error) from error


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_user(user_id: int) -> Response:
    try:
        repository.delete_user(user_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as error:
        raise translate_error(error) from error


@app.get("/songs")
def list_songs() -> list[dict]:
    return repository.list_songs()


@app.get("/songs/{song_id}")
def get_song(song_id: int) -> dict:
    try:
        return repository.get_song(song_id)
    except ValueError as error:
        raise translate_error(error) from error


@app.post("/songs", status_code=status.HTTP_201_CREATED)
def create_song(payload: SongInput) -> dict:
    try:
        return repository.create_song(payload.name, payload.artist)
    except ValueError as error:
        raise translate_error(error) from error


@app.put("/songs/{song_id}")
def update_song(song_id: int, payload: SongInput) -> dict:
    try:
        return repository.update_song(song_id, payload.name, payload.artist)
    except ValueError as error:
        raise translate_error(error) from error


@app.delete("/songs/{song_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_song(song_id: int) -> Response:
    try:
        repository.delete_song(song_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as error:
        raise translate_error(error) from error


@app.get("/playlists")
def list_playlists(
    user_id: Annotated[int | None, Query(gt=0)] = None,
    song_id: Annotated[int | None, Query(gt=0)] = None,
) -> list[dict]:
    try:
        if user_id is not None and song_id is not None:
            raise ValidationError("use apenas um filtro por vez")
        if user_id is not None:
            return repository.list_playlists_by_user(user_id)
        if song_id is not None:
            return repository.list_playlists_by_song(song_id)
        return repository.list_playlists()
    except ValueError as error:
        raise translate_error(error) from error


@app.get("/playlists/{playlist_id}")
def get_playlist(playlist_id: int) -> dict:
    try:
        return repository.get_playlist(playlist_id, include_songs=True)
    except ValueError as error:
        raise translate_error(error) from error


@app.get("/playlists/{playlist_id}/songs")
def list_songs_by_playlist(playlist_id: int) -> list[dict]:
    try:
        return repository.list_songs_by_playlist(playlist_id)
    except ValueError as error:
        raise translate_error(error) from error


@app.post("/playlists", status_code=status.HTTP_201_CREATED)
def create_playlist(payload: PlaylistInput) -> dict:
    try:
        return repository.create_playlist(payload.user_id, payload.name, payload.song_ids)
    except ValueError as error:
        raise translate_error(error) from error


@app.put("/playlists/{playlist_id}")
def update_playlist(playlist_id: int, payload: PlaylistInput) -> dict:
    try:
        return repository.update_playlist(
            playlist_id, payload.user_id, payload.name, payload.song_ids
        )
    except ValueError as error:
        raise translate_error(error) from error


@app.delete("/playlists/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_playlist(playlist_id: int) -> Response:
    try:
        repository.delete_playlist(playlist_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as error:
        raise translate_error(error) from error

