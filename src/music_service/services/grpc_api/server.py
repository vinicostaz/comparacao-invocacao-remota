from __future__ import annotations

import os
from concurrent import futures

import grpc

from music_service.config import database_path
from music_service.repository import MusicRepository, NotFoundError
from music_service.services.grpc_api.generated import music_pb2, music_pb2_grpc


repository = MusicRepository(database_path())
repository.initialize()


def user_message(item: dict) -> music_pb2.User:
    return music_pb2.User(id=item["id"], name=item["name"], age=item["age"])


def song_message(item: dict) -> music_pb2.Song:
    return music_pb2.Song(id=item["id"], name=item["name"], artist=item["artist"])


def playlist_message(item: dict, include_songs: bool = False) -> music_pb2.Playlist:
    songs = repository.list_songs_by_playlist(item["id"]) if include_songs else []
    return music_pb2.Playlist(
        id=item["id"],
        user_id=item["user_id"],
        name=item["name"],
        songs=[song_message(song) for song in songs],
    )


def abort(context: grpc.ServicerContext, error: ValueError):
    code = grpc.StatusCode.NOT_FOUND if isinstance(error, NotFoundError) else grpc.StatusCode.INVALID_ARGUMENT
    context.abort(code, str(error))


class MusicService(music_pb2_grpc.MusicServiceServicer):
    def Health(self, request, context):
        return music_pb2.Empty()

    def ListUsers(self, request, context):
        return music_pb2.UserList(items=[user_message(item) for item in repository.list_users()])

    def GetUser(self, request, context):
        try:
            return user_message(repository.get_user(request.id))
        except ValueError as error:
            return abort(context, error)

    def CreateUser(self, request, context):
        try:
            return user_message(repository.create_user(request.name, request.age))
        except ValueError as error:
            return abort(context, error)

    def UpdateUser(self, request, context):
        try:
            return user_message(
                repository.update_user(request.id, request.user.name, request.user.age)
            )
        except ValueError as error:
            return abort(context, error)

    def DeleteUser(self, request, context):
        try:
            return music_pb2.DeleteResponse(success=repository.delete_user(request.id))
        except ValueError as error:
            return abort(context, error)

    def ListSongs(self, request, context):
        return music_pb2.SongList(items=[song_message(item) for item in repository.list_songs()])

    def GetSong(self, request, context):
        try:
            return song_message(repository.get_song(request.id))
        except ValueError as error:
            return abort(context, error)

    def CreateSong(self, request, context):
        try:
            return song_message(repository.create_song(request.name, request.artist))
        except ValueError as error:
            return abort(context, error)

    def UpdateSong(self, request, context):
        try:
            return song_message(
                repository.update_song(request.id, request.song.name, request.song.artist)
            )
        except ValueError as error:
            return abort(context, error)

    def DeleteSong(self, request, context):
        try:
            return music_pb2.DeleteResponse(success=repository.delete_song(request.id))
        except ValueError as error:
            return abort(context, error)

    def ListPlaylists(self, request, context):
        return music_pb2.PlaylistList(
            items=[playlist_message(item) for item in repository.list_playlists()]
        )

    def GetPlaylist(self, request, context):
        try:
            return playlist_message(repository.get_playlist(request.id), include_songs=True)
        except ValueError as error:
            return abort(context, error)

    def CreatePlaylist(self, request, context):
        try:
            item = repository.create_playlist(request.user_id, request.name, list(request.song_ids))
            return playlist_message(item, include_songs=True)
        except ValueError as error:
            return abort(context, error)

    def UpdatePlaylist(self, request, context):
        try:
            item = repository.update_playlist(
                request.id,
                request.playlist.user_id,
                request.playlist.name,
                list(request.playlist.song_ids),
            )
            return playlist_message(item, include_songs=True)
        except ValueError as error:
            return abort(context, error)

    def DeletePlaylist(self, request, context):
        try:
            return music_pb2.DeleteResponse(success=repository.delete_playlist(request.id))
        except ValueError as error:
            return abort(context, error)

    def ListPlaylistsByUser(self, request, context):
        try:
            items = repository.list_playlists_by_user(request.id)
            return music_pb2.PlaylistList(items=[playlist_message(item) for item in items])
        except ValueError as error:
            return abort(context, error)

    def ListSongsByPlaylist(self, request, context):
        try:
            items = repository.list_songs_by_playlist(request.id)
            return music_pb2.SongList(items=[song_message(item) for item in items])
        except ValueError as error:
            return abort(context, error)

    def ListPlaylistsBySong(self, request, context):
        try:
            items = repository.list_playlists_by_song(request.id)
            return music_pb2.PlaylistList(items=[playlist_message(item) for item in items])
        except ValueError as error:
            return abort(context, error)


def serve() -> None:
    port = int(os.getenv("GRPC_PORT", "50051"))
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=32))
    music_pb2_grpc.add_MusicServiceServicer_to_server(MusicService(), server)
    server.add_insecure_port(f"127.0.0.1:{port}")
    server.start()
    print(f"gRPC em 127.0.0.1:{port}", flush=True)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

