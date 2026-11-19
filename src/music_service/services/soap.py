from __future__ import annotations

import os
import operator
import sys
from socketserver import ThreadingMixIn
from wsgiref.simple_server import make_server
from wsgiref.simple_server import WSGIServer

# O Spyne 2.14 inclui uma copia antiga de six cujo import hook falha no
# Python 3.12. Os aliases abaixo apontam apenas os modulos de compatibilidade
# para o pacote six atual, sem alterar o protocolo ou a serializacao SOAP.
import six
import six.moves
import six.moves.collections_abc
import six.moves.http_cookies
import six.moves.urllib.parse

if not hasattr(six, "get_function_name"):
    six.get_function_name = operator.attrgetter("__name__")

sys.modules.setdefault("spyne.util.six", six)
sys.modules.setdefault("spyne.util.six.moves", six.moves)
sys.modules.setdefault("spyne.util.six.moves.collections_abc", six.moves.collections_abc)
sys.modules.setdefault("spyne.util.six.moves.http_cookies", six.moves.http_cookies)
sys.modules.setdefault("spyne.util.six.moves.urllib", six.moves.urllib)
sys.modules.setdefault("spyne.util.six.moves.urllib.parse", six.moves.urllib.parse)

from spyne import Application, Array, Boolean, ComplexModel, Integer, ServiceBase, Unicode, rpc
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

from music_service.config import database_path
from music_service.repository import MusicRepository


repository = MusicRepository(database_path())
repository.initialize()


class UserType(ComplexModel):
    id = Integer
    name = Unicode
    age = Integer


class SongType(ComplexModel):
    id = Integer
    name = Unicode
    artist = Unicode


class PlaylistType(ComplexModel):
    id = Integer
    user_id = Integer
    name = Unicode


def user_type(item: dict) -> UserType:
    return UserType(id=item["id"], name=item["name"], age=item["age"])


def song_type(item: dict) -> SongType:
    return SongType(id=item["id"], name=item["name"], artist=item["artist"])


def playlist_type(item: dict) -> PlaylistType:
    return PlaylistType(id=item["id"], user_id=item["user_id"], name=item["name"])


def parse_song_ids(value: str) -> list[int]:
    try:
        return [int(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as error:
        raise ValueError("song_ids deve ser uma lista CSV de inteiros") from error


class MusicSoapService(ServiceBase):
    @rpc(_returns=Unicode)
    def health(ctx):
        return "ok"

    @rpc(_returns=Array(UserType))
    def list_users(ctx):
        return [user_type(item) for item in repository.list_users()]

    @rpc(Integer, _returns=UserType)
    def get_user(ctx, user_id):
        return user_type(repository.get_user(user_id))

    @rpc(Unicode, Integer, _returns=UserType)
    def create_user(ctx, name, age):
        return user_type(repository.create_user(name, age))

    @rpc(Integer, Unicode, Integer, _returns=UserType)
    def update_user(ctx, user_id, name, age):
        return user_type(repository.update_user(user_id, name, age))

    @rpc(Integer, _returns=Boolean)
    def delete_user(ctx, user_id):
        return repository.delete_user(user_id)

    @rpc(_returns=Array(SongType))
    def list_songs(ctx):
        return [song_type(item) for item in repository.list_songs()]

    @rpc(Integer, _returns=SongType)
    def get_song(ctx, song_id):
        return song_type(repository.get_song(song_id))

    @rpc(Unicode, Unicode, _returns=SongType)
    def create_song(ctx, name, artist):
        return song_type(repository.create_song(name, artist))

    @rpc(Integer, Unicode, Unicode, _returns=SongType)
    def update_song(ctx, song_id, name, artist):
        return song_type(repository.update_song(song_id, name, artist))

    @rpc(Integer, _returns=Boolean)
    def delete_song(ctx, song_id):
        return repository.delete_song(song_id)

    @rpc(_returns=Array(PlaylistType))
    def list_playlists(ctx):
        return [playlist_type(item) for item in repository.list_playlists()]

    @rpc(Integer, _returns=PlaylistType)
    def get_playlist(ctx, playlist_id):
        return playlist_type(repository.get_playlist(playlist_id))

    @rpc(Integer, Unicode, Unicode, _returns=PlaylistType)
    def create_playlist(ctx, user_id, name, song_ids):
        item = repository.create_playlist(user_id, name, parse_song_ids(song_ids))
        return playlist_type(item)

    @rpc(Integer, Integer, Unicode, Unicode, _returns=PlaylistType)
    def update_playlist(ctx, playlist_id, user_id, name, song_ids):
        item = repository.update_playlist(
            playlist_id, user_id, name, parse_song_ids(song_ids)
        )
        return playlist_type(item)

    @rpc(Integer, _returns=Boolean)
    def delete_playlist(ctx, playlist_id):
        return repository.delete_playlist(playlist_id)

    @rpc(Integer, _returns=Array(PlaylistType))
    def list_playlists_by_user(ctx, user_id):
        return [playlist_type(item) for item in repository.list_playlists_by_user(user_id)]

    @rpc(Integer, _returns=Array(SongType))
    def list_songs_by_playlist(ctx, playlist_id):
        return [song_type(item) for item in repository.list_songs_by_playlist(playlist_id)]

    @rpc(Integer, _returns=Array(PlaylistType))
    def list_playlists_by_song(ctx, song_id):
        return [playlist_type(item) for item in repository.list_playlists_by_song(song_id)]


soap_application = Application(
    [MusicSoapService],
    tns="urn:music-service",
    in_protocol=Soap11(validator="lxml"),
    out_protocol=Soap11(),
)
application = WsgiApplication(soap_application)


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def main() -> None:
    host = os.getenv("SOAP_HOST", "127.0.0.1")
    port = int(os.getenv("SOAP_PORT", "8003"))
    print(f"SOAP em http://{host}:{port}/?wsdl", flush=True)
    make_server(host, port, application, server_class=ThreadingWSGIServer).serve_forever()


if __name__ == "__main__":
    main()

