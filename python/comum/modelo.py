"""Modelo de domínio do serviço de streaming (igual ao pacote br.streaming.comum.modelo do Java).

As classes são imutáveis (frozen): uma atualização substitui o objeto inteiro no
repositório, então é seguro serializar um objeto enquanto outra thread escreve.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Usuario:
    id: int
    nome: str
    idade: int


@dataclass(frozen=True)
class Musica:
    id: int
    nome: str
    artista: str


@dataclass(frozen=True)
class Playlist:
    id: int
    nome: str
    usuario_id: int               # dono da playlist
    musica_ids: tuple[int, ...]   # músicas da playlist, em ordem (relacionamento N:N)
