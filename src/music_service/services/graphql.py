from __future__ import annotations

from typing import Optional

import strawberry
from fastapi import FastAPI
from graphql import GraphQLError
from strawberry.fastapi import GraphQLRouter

from music_service.config import database_path
from music_service.repository import MusicRepository


repository = MusicRepository(database_path())
repository.initialize()


def graphql_error(error: ValueError) -> GraphQLError:
    return GraphQLError(str(error), extensions={"code": error.__class__.__name__})


@strawberry.type
class User:
    id: int
    name: str
    age: int

    @strawberry.field
    def playlists(self) -> list["Playlist"]:
        return [Playlist.from_dict(item) for item in repository.list_playlists_by_user(self.id)]

    @staticmethod
    def from_dict(item: dict) -> "User":
        return User(id=item["id"], name=item["name"], age=item["age"])


@strawberry.type
class Song:
    id: int
    name: str
    artist: str

    @strawberry.field
    def playlists(self) -> list["Playlist"]:
        return [Playlist.from_dict(item) for item in repository.list_playlists_by_song(self.id)]

    @staticmethod
    def from_dict(item: dict) -> "Song":
        return Song(id=item["id"], name=item["name"], artist=item["artist"])


@strawberry.type
class Playlist:
    id: int
    user_id: int
    name: str

    @strawberry.field
    def owner(self) -> User:
        return User.from_dict(repository.get_user(self.user_id))

    @strawberry.field
    def songs(self) -> list[Song]:
        return [Song.from_dict(item) for item in repository.list_songs_by_playlist(self.id)]

    @staticmethod
    def from_dict(item: dict) -> "Playlist":
        return Playlist(id=item["id"], user_id=item["user_id"], name=item["name"])


@strawberry.input
class UserInput:
    name: str
    age: int


@strawberry.input
class SongInput:
    name: str
    artist: str


@strawberry.input
class PlaylistInput:
    user_id: int
    name: str
    song_ids: list[int]


@strawberry.type
class DeleteResult:
    success: bool


@strawberry.type
class Query:
    @strawberry.field
    def users(self) -> list[User]:
        return [User.from_dict(item) for item in repository.list_users()]

    @strawberry.field
    def user(self, id: int) -> Optional[User]:
        try:
            return User.from_dict(repository.get_user(id))
        except ValueError as error:
            raise graphql_error(error) from error

    @strawberry.field
    def songs(self) -> list[Song]:
        return [Song.from_dict(item) for item in repository.list_songs()]

    @strawberry.field
    def song(self, id: int) -> Optional[Song]:
        try:
            return Song.from_dict(repository.get_song(id))
        except ValueError as error:
            raise graphql_error(error) from error

    @strawberry.field
    def playlists(self, user_id: int | None = None, song_id: int | None = None) -> list[Playlist]:
        try:
            if user_id is not None and song_id is not None:
                raise ValueError("use apenas um filtro por vez")
            if user_id is not None:
                items = repository.list_playlists_by_user(user_id)
            elif song_id is not None:
                items = repository.list_playlists_by_song(song_id)
            else:
                items = repository.list_playlists()
            return [Playlist.from_dict(item) for item in items]
        except ValueError as error:
            raise graphql_error(error) from error

    @strawberry.field
    def playlist(self, id: int) -> Optional[Playlist]:
        try:
            return Playlist.from_dict(repository.get_playlist(id))
        except ValueError as error:
            raise graphql_error(error) from error


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_user(self, input: UserInput) -> User:
        try:
            return User.from_dict(repository.create_user(input.name, input.age))
        except ValueError as error:
            raise graphql_error(error) from error

    @strawberry.mutation
    def update_user(self, id: int, input: UserInput) -> User:
        try:
            return User.from_dict(repository.update_user(id, input.name, input.age))
        except ValueError as error:
            raise graphql_error(error) from error

    @strawberry.mutation
    def delete_user(self, id: int) -> DeleteResult:
        try:
            return DeleteResult(success=repository.delete_user(id))
        except ValueError as error:
            raise graphql_error(error) from error

    @strawberry.mutation
    def create_song(self, input: SongInput) -> Song:
        try:
            return Song.from_dict(repository.create_song(input.name, input.artist))
        except ValueError as error:
            raise graphql_error(error) from error

    @strawberry.mutation
    def update_song(self, id: int, input: SongInput) -> Song:
        try:
            return Song.from_dict(repository.update_song(id, input.name, input.artist))
        except ValueError as error:
            raise graphql_error(error) from error

    @strawberry.mutation
    def delete_song(self, id: int) -> DeleteResult:
        try:
            return DeleteResult(success=repository.delete_song(id))
        except ValueError as error:
            raise graphql_error(error) from error

    @strawberry.mutation
    def create_playlist(self, input: PlaylistInput) -> Playlist:
        try:
            return Playlist.from_dict(
                repository.create_playlist(input.user_id, input.name, input.song_ids)
            )
        except ValueError as error:
            raise graphql_error(error) from error

    @strawberry.mutation
    def update_playlist(self, id: int, input: PlaylistInput) -> Playlist:
        try:
            return Playlist.from_dict(
                repository.update_playlist(id, input.user_id, input.name, input.song_ids)
            )
        except ValueError as error:
            raise graphql_error(error) from error

    @strawberry.mutation
    def delete_playlist(self, id: int) -> DeleteResult:
        try:
            return DeleteResult(success=repository.delete_playlist(id))
        except ValueError as error:
            raise graphql_error(error) from error


schema = strawberry.Schema(query=Query, mutation=Mutation)
app = FastAPI(title="Servico de Streaming de Musicas - GraphQL")
app.include_router(GraphQLRouter(schema), prefix="/graphql")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "protocol": "GraphQL"}

