from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
    age INTEGER NOT NULL CHECK(age BETWEEN 0 AND 130)
);

CREATE TABLE IF NOT EXISTS songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
    artist TEXT NOT NULL CHECK(length(trim(artist)) > 0)
);

CREATE TABLE IF NOT EXISTS playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK(length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS playlist_songs (
    playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    song_id INTEGER NOT NULL REFERENCES songs(id) ON DELETE RESTRICT,
    PRIMARY KEY (playlist_id, song_id)
);

CREATE INDEX IF NOT EXISTS idx_playlists_user ON playlists(user_id);
CREATE INDEX IF NOT EXISTS idx_playlist_songs_song ON playlist_songs(song_id);
"""


class NotFoundError(ValueError):
    pass


class ValidationError(ValueError):
    pass


class MusicRepository:
    """Repositorio SQLite usado por todos os protocolos.

    Cada operacao abre uma conexao curta. Isso evita compartilhar objetos de
    conexao entre threads dos quatro servidores e mantem a camada de dominio
    identica para a comparacao.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    @staticmethod
    def _rows(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
        return [dict(row) for row in rows]

    @staticmethod
    def _require_nonempty(value: str, field: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValidationError(f"{field} nao pode ser vazio")
        return cleaned

    @staticmethod
    def _require_age(age: int) -> int:
        if age < 0 or age > 130:
            raise ValidationError("idade deve estar entre 0 e 130")
        return age

    def list_users(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            return self._rows(connection.execute("SELECT id, name, age FROM users ORDER BY id"))

    def get_user(self, user_id: int) -> dict[str, Any]:
        with self.connect() as connection:
            row = connection.execute("SELECT id, name, age FROM users WHERE id=?", (user_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"usuario {user_id} nao encontrado")
        return dict(row)

    def create_user(self, name: str, age: int) -> dict[str, Any]:
        name = self._require_nonempty(name, "nome")
        age = self._require_age(age)
        with self.connect() as connection:
            cursor = connection.execute("INSERT INTO users(name, age) VALUES (?, ?)", (name, age))
            user_id = cursor.lastrowid
        return self.get_user(int(user_id))

    def update_user(self, user_id: int, name: str, age: int) -> dict[str, Any]:
        self.get_user(user_id)
        name = self._require_nonempty(name, "nome")
        age = self._require_age(age)
        with self.connect() as connection:
            connection.execute("UPDATE users SET name=?, age=? WHERE id=?", (name, age, user_id))
        return self.get_user(user_id)

    def delete_user(self, user_id: int) -> bool:
        with self.connect() as connection:
            cursor = connection.execute("DELETE FROM users WHERE id=?", (user_id,))
        if cursor.rowcount == 0:
            raise NotFoundError(f"usuario {user_id} nao encontrado")
        return True

    def list_songs(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            return self._rows(connection.execute("SELECT id, name, artist FROM songs ORDER BY id"))

    def get_song(self, song_id: int) -> dict[str, Any]:
        with self.connect() as connection:
            row = connection.execute("SELECT id, name, artist FROM songs WHERE id=?", (song_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"musica {song_id} nao encontrada")
        return dict(row)

    def create_song(self, name: str, artist: str) -> dict[str, Any]:
        name = self._require_nonempty(name, "nome")
        artist = self._require_nonempty(artist, "artista")
        with self.connect() as connection:
            cursor = connection.execute("INSERT INTO songs(name, artist) VALUES (?, ?)", (name, artist))
            song_id = cursor.lastrowid
        return self.get_song(int(song_id))

    def update_song(self, song_id: int, name: str, artist: str) -> dict[str, Any]:
        self.get_song(song_id)
        name = self._require_nonempty(name, "nome")
        artist = self._require_nonempty(artist, "artista")
        with self.connect() as connection:
            connection.execute("UPDATE songs SET name=?, artist=? WHERE id=?", (name, artist, song_id))
        return self.get_song(song_id)

    def delete_song(self, song_id: int) -> bool:
        with self.connect() as connection:
            try:
                cursor = connection.execute("DELETE FROM songs WHERE id=?", (song_id,))
            except sqlite3.IntegrityError as error:
                raise ValidationError("musica pertence a uma playlist") from error
        if cursor.rowcount == 0:
            raise NotFoundError(f"musica {song_id} nao encontrada")
        return True

    def list_playlists(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            return self._rows(
                connection.execute("SELECT id, user_id, name FROM playlists ORDER BY id")
            )

    def get_playlist(self, playlist_id: int, include_songs: bool = False) -> dict[str, Any]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id, user_id, name FROM playlists WHERE id=?", (playlist_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError(f"playlist {playlist_id} nao encontrada")
        result = dict(row)
        if include_songs:
            result["songs"] = self.list_songs_by_playlist(playlist_id)
        return result

    def _validate_playlist_relations(self, user_id: int, song_ids: list[int]) -> list[int]:
        self.get_user(user_id)
        unique_song_ids = list(dict.fromkeys(song_ids))
        if not unique_song_ids:
            raise ValidationError("playlist deve conter pelo menos uma musica")
        for song_id in unique_song_ids:
            self.get_song(song_id)
        return unique_song_ids

    def create_playlist(self, user_id: int, name: str, song_ids: list[int]) -> dict[str, Any]:
        name = self._require_nonempty(name, "nome")
        song_ids = self._validate_playlist_relations(user_id, song_ids)
        with self.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO playlists(user_id, name) VALUES (?, ?)", (user_id, name)
            )
            playlist_id = int(cursor.lastrowid)
            connection.executemany(
                "INSERT INTO playlist_songs(playlist_id, song_id) VALUES (?, ?)",
                [(playlist_id, song_id) for song_id in song_ids],
            )
        return self.get_playlist(playlist_id, include_songs=True)

    def update_playlist(
        self, playlist_id: int, user_id: int, name: str, song_ids: list[int]
    ) -> dict[str, Any]:
        self.get_playlist(playlist_id)
        name = self._require_nonempty(name, "nome")
        song_ids = self._validate_playlist_relations(user_id, song_ids)
        with self.connect() as connection:
            connection.execute(
                "UPDATE playlists SET user_id=?, name=? WHERE id=?",
                (user_id, name, playlist_id),
            )
            connection.execute("DELETE FROM playlist_songs WHERE playlist_id=?", (playlist_id,))
            connection.executemany(
                "INSERT INTO playlist_songs(playlist_id, song_id) VALUES (?, ?)",
                [(playlist_id, song_id) for song_id in song_ids],
            )
        return self.get_playlist(playlist_id, include_songs=True)

    def delete_playlist(self, playlist_id: int) -> bool:
        with self.connect() as connection:
            cursor = connection.execute("DELETE FROM playlists WHERE id=?", (playlist_id,))
        if cursor.rowcount == 0:
            raise NotFoundError(f"playlist {playlist_id} nao encontrada")
        return True

    def list_playlists_by_user(self, user_id: int) -> list[dict[str, Any]]:
        self.get_user(user_id)
        with self.connect() as connection:
            return self._rows(
                connection.execute(
                    "SELECT id, user_id, name FROM playlists WHERE user_id=? ORDER BY id",
                    (user_id,),
                )
            )

    def list_songs_by_playlist(self, playlist_id: int) -> list[dict[str, Any]]:
        self.get_playlist(playlist_id)
        with self.connect() as connection:
            return self._rows(
                connection.execute(
                    """
                    SELECT s.id, s.name, s.artist
                    FROM songs s
                    JOIN playlist_songs ps ON ps.song_id=s.id
                    WHERE ps.playlist_id=?
                    ORDER BY s.id
                    """,
                    (playlist_id,),
                )
            )

    def list_playlists_by_song(self, song_id: int) -> list[dict[str, Any]]:
        self.get_song(song_id)
        with self.connect() as connection:
            return self._rows(
                connection.execute(
                    """
                    SELECT p.id, p.user_id, p.name
                    FROM playlists p
                    JOIN playlist_songs ps ON ps.playlist_id=p.id
                    WHERE ps.song_id=?
                    ORDER BY p.id
                    """,
                    (song_id,),
                )
            )

