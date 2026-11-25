"""Regras de negócio + armazenamento em memória do serviço de streaming.

É o MESMO módulo usado pelos quatro servidores Python (REST, GraphQL, SOAP e gRPC):
cada servidor só traduz o protocolo para chamadas a este repositório. A versão Java
(br.streaming.comum.RepositorioStreaming) implementa as mesmas regras e os mesmos
dados iniciais, para que a comparação entre tecnologias e linguagens seja justa.
"""
from __future__ import annotations

import threading
from typing import Iterable, Optional

from comum.modelo import Musica, Playlist, Usuario

# Tamanho dos dados iniciais (idênticos na versão Java).
USUARIOS_INICIAIS = 100
MUSICAS_INICIAIS = 200
PLAYLISTS_INICIAIS = 200
MUSICAS_POR_PLAYLIST = 10


class NaoEncontrado(Exception):
    """Recurso inexistente (REST 404 | GraphQL NOT_FOUND | SOAP Fault | gRPC NOT_FOUND)."""


class RequisicaoInvalida(Exception):
    """Dados de entrada inválidos (REST 400 | GraphQL BAD_REQUEST | SOAP Fault | gRPC INVALID_ARGUMENT)."""


class RepositorioStreaming:

    def __init__(self) -> None:
        self._usuarios: dict[int, Usuario] = {}
        self._musicas: dict[int, Musica] = {}
        self._playlists: dict[int, Playlist] = {}
        self._proximo_usuario_id = 1
        self._proxima_musica_id = 1
        self._proxima_playlist_id = 1
        self._lock = threading.RLock()

    @classmethod
    def com_dados_iniciais(cls) -> "RepositorioStreaming":
        """Cria um repositório já populado com os dados usados nos testes."""
        repo = cls()
        for i in range(1, USUARIOS_INICIAIS + 1):
            repo.criar_usuario(f"Usuario {i}", 18 + (i * 7) % 50)
        for j in range(1, MUSICAS_INICIAIS + 1):
            repo.criar_musica(f"Musica {j}", f"Artista {(j - 1) % 25 + 1}")
        for k in range(1, PLAYLISTS_INICIAIS + 1):
            ids = [(k - 1 + t * 17) % MUSICAS_INICIAIS + 1 for t in range(MUSICAS_POR_PLAYLIST)]
            repo.criar_playlist((k - 1) % USUARIOS_INICIAIS + 1, f"Playlist {k}", ids)
        return repo

    # ------------------------------------------------------------------ usuários

    def criar_usuario(self, nome: Optional[str], idade: Optional[int]) -> Usuario:
        nome = _exigir_texto(nome, "nome")
        idade = _exigir_idade(idade)
        with self._lock:
            u = Usuario(self._proximo_usuario_id, nome, idade)
            self._proximo_usuario_id += 1
            self._usuarios[u.id] = u
            return u

    def listar_usuarios(self) -> list[Usuario]:
        with self._lock:
            return list(self._usuarios.values())

    def obter_usuario(self, id: int) -> Usuario:
        with self._lock:
            return self._buscar_usuario(id)

    def atualizar_usuario(self, id: int, nome: Optional[str], idade: Optional[int]) -> Usuario:
        nome = _exigir_texto(nome, "nome")
        idade = _exigir_idade(idade)
        with self._lock:
            self._buscar_usuario(id)
            u = Usuario(id, nome, idade)
            self._usuarios[id] = u
            return u

    def remover_usuario(self, id: int) -> None:
        """Remove o usuário e, por composição, todas as playlists dele."""
        with self._lock:
            self._buscar_usuario(id)
            del self._usuarios[id]
            self._playlists = {pid: p for pid, p in self._playlists.items() if p.usuario_id != id}

    # ------------------------------------------------------------------- músicas

    def criar_musica(self, nome: Optional[str], artista: Optional[str]) -> Musica:
        nome = _exigir_texto(nome, "nome")
        artista = _exigir_texto(artista, "artista")
        with self._lock:
            m = Musica(self._proxima_musica_id, nome, artista)
            self._proxima_musica_id += 1
            self._musicas[m.id] = m
            return m

    def listar_musicas(self) -> list[Musica]:
        with self._lock:
            return list(self._musicas.values())

    def obter_musica(self, id: int) -> Musica:
        with self._lock:
            return self._buscar_musica(id)

    def atualizar_musica(self, id: int, nome: Optional[str], artista: Optional[str]) -> Musica:
        nome = _exigir_texto(nome, "nome")
        artista = _exigir_texto(artista, "artista")
        with self._lock:
            self._buscar_musica(id)
            m = Musica(id, nome, artista)
            self._musicas[id] = m
            return m

    def remover_musica(self, id: int) -> None:
        """Remove a música do catálogo e de todas as playlists que a continham."""
        with self._lock:
            self._buscar_musica(id)
            del self._musicas[id]
            for p in list(self._playlists.values()):
                if id in p.musica_ids:
                    restantes = tuple(m for m in p.musica_ids if m != id)
                    self._playlists[p.id] = Playlist(p.id, p.nome, p.usuario_id, restantes)

    # ----------------------------------------------------------------- playlists

    def criar_playlist(self, usuario_id: int, nome: Optional[str],
                       musica_ids: Optional[Iterable[int]]) -> Playlist:
        nome = _exigir_texto(nome, "nome")
        with self._lock:
            self._buscar_usuario(usuario_id)
            ids = self._validar_musicas(musica_ids)
            p = Playlist(self._proxima_playlist_id, nome, usuario_id, ids)
            self._proxima_playlist_id += 1
            self._playlists[p.id] = p
            return p

    def listar_playlists_do_usuario(self, usuario_id: int) -> list[Playlist]:
        """Consulta do enunciado: todas as playlists de um determinado usuário."""
        with self._lock:
            self._buscar_usuario(usuario_id)
            return [p for p in self._playlists.values() if p.usuario_id == usuario_id]

    def obter_playlist(self, id: int) -> Playlist:
        with self._lock:
            return self._buscar_playlist(id)

    def atualizar_playlist(self, id: int, nome: Optional[str],
                           musica_ids: Optional[Iterable[int]]) -> Playlist:
        nome = _exigir_texto(nome, "nome")
        with self._lock:
            atual = self._buscar_playlist(id)
            ids = self._validar_musicas(musica_ids)
            p = Playlist(id, nome, atual.usuario_id, ids)
            self._playlists[id] = p
            return p

    def remover_playlist(self, id: int) -> None:
        with self._lock:
            self._buscar_playlist(id)
            del self._playlists[id]

    # ----------------------------------------------------------------- consultas

    def listar_musicas_da_playlist(self, playlist_id: int) -> list[Musica]:
        """Consulta do enunciado: todas as músicas de uma determinada playlist."""
        with self._lock:
            p = self._buscar_playlist(playlist_id)
            return [self._musicas[m] for m in p.musica_ids if m in self._musicas]

    def listar_playlists_com_musica(self, musica_id: int) -> list[Playlist]:
        """Consulta do enunciado: todas as playlists que contêm uma determinada música."""
        with self._lock:
            self._buscar_musica(musica_id)
            return [p for p in self._playlists.values() if musica_id in p.musica_ids]

    # ---------------------------------------------------------------- auxiliares

    def _buscar_usuario(self, id: int) -> Usuario:
        u = self._usuarios.get(id)
        if u is None:
            raise NaoEncontrado(f"Usuário {id} não encontrado")
        return u

    def _buscar_musica(self, id: int) -> Musica:
        m = self._musicas.get(id)
        if m is None:
            raise NaoEncontrado(f"Música {id} não encontrada")
        return m

    def _buscar_playlist(self, id: int) -> Playlist:
        p = self._playlists.get(id)
        if p is None:
            raise NaoEncontrado(f"Playlist {id} não encontrada")
        return p

    def _validar_musicas(self, musica_ids: Optional[Iterable[int]]) -> tuple[int, ...]:
        ids = tuple(musica_ids or ())
        for m in ids:
            if m not in self._musicas:
                raise RequisicaoInvalida(f"Música {m} não existe")
        return ids


def _exigir_texto(valor: Optional[str], campo: str) -> str:
    if valor is None or not str(valor).strip():
        raise RequisicaoInvalida(f"Campo '{campo}' é obrigatório")
    return str(valor).strip()


def _exigir_idade(idade: Optional[int]) -> int:
    if idade is None:
        raise RequisicaoInvalida("Campo 'idade' é obrigatório")
    if idade < 0:
        raise RequisicaoInvalida("Campo 'idade' não pode ser negativo")
    return int(idade)
