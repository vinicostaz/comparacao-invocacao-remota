from __future__ import annotations

import argparse
from pathlib import Path

from music_service.config import database_path
from music_service.repository import MusicRepository


def seed(path: Path, users: int = 100, songs: int = 1000, playlists: int = 300) -> None:
    repository = MusicRepository(path)
    repository.initialize()
    with repository.connect() as connection:
        connection.execute("DELETE FROM playlist_songs")
        connection.execute("DELETE FROM playlists")
        connection.execute("DELETE FROM songs")
        connection.execute("DELETE FROM users")
        connection.execute("DELETE FROM sqlite_sequence")

        connection.executemany(
            "INSERT INTO users(name, age) VALUES (?, ?)",
            [(f"Usuario {index:03d}", 18 + (index % 55)) for index in range(1, users + 1)],
        )
        connection.executemany(
            "INSERT INTO songs(name, artist) VALUES (?, ?)",
            [(f"Musica {index:04d}", f"Artista {(index % 80) + 1:03d}") for index in range(1, songs + 1)],
        )
        connection.executemany(
            "INSERT INTO playlists(user_id, name) VALUES (?, ?)",
            [((index % users) + 1, f"Playlist {index:03d}") for index in range(1, playlists + 1)],
        )
        links: list[tuple[int, int]] = []
        for playlist_id in range(1, playlists + 1):
            start = ((playlist_id - 1) * 17) % songs
            for offset in range(20):
                links.append((playlist_id, ((start + offset * 7) % songs) + 1))
        connection.executemany(
            "INSERT INTO playlist_songs(playlist_id, song_id) VALUES (?, ?)", links
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Cria massa de dados deterministica")
    parser.add_argument("--db", type=Path, default=database_path())
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument("--songs", type=int, default=1000)
    parser.add_argument("--playlists", type=int, default=300)
    args = parser.parse_args()
    seed(args.db, args.users, args.songs, args.playlists)
    print(f"Banco criado em {args.db}")


if __name__ == "__main__":
    main()

