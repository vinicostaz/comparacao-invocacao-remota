"""Clientes Python para as 4 tecnologias, com a MESMA interface.

Cada cliente funciona tanto com o servidor Java quanto com o Python da mesma
tecnologia, pois os dois seguem o mesmo contrato. Os resultados são normalizados
em dicionários:
    usuário  -> {"id", "nome", "idade"}
    música   -> {"id", "nome", "artista"}
    playlist -> {"id", "nome", "usuarioId", "musicaIds"}
Erros de recurso inexistente viram NaoEncontradoRemoto; os demais, ErroRemoto.

Estes clientes também servem de exemplo de código de cliente para os slides.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


class ErroRemoto(Exception):
    pass


class NaoEncontradoRemoto(ErroRemoto):
    pass


# ====================================================================== REST
class ClienteRest:
    """REST: um recurso por URL, verbos HTTP, JSON, erros = status HTTP."""

    def __init__(self, base_url: str):
        import requests
        self.base = base_url.rstrip("/")
        self.http = requests.Session()

    def _req(self, metodo, caminho, json=None):
        r = self.http.request(metodo, self.base + caminho, json=json, timeout=10)
        if r.status_code == 404:
            raise NaoEncontradoRemoto(r.json().get("erro"))
        if r.status_code >= 400:
            raise ErroRemoto(f"HTTP {r.status_code}: {r.text}")
        return r.json() if r.content else None

    def listar_usuarios(self): return self._req("GET", "/usuarios")
    def criar_usuario(self, nome, idade): return self._req("POST", "/usuarios", {"nome": nome, "idade": idade})
    def obter_usuario(self, id): return self._req("GET", f"/usuarios/{id}")
    def atualizar_usuario(self, id, nome, idade): return self._req("PUT", f"/usuarios/{id}", {"nome": nome, "idade": idade})
    def remover_usuario(self, id): self._req("DELETE", f"/usuarios/{id}")

    def listar_musicas(self): return self._req("GET", "/musicas")
    def criar_musica(self, nome, artista): return self._req("POST", "/musicas", {"nome": nome, "artista": artista})
    def obter_musica(self, id): return self._req("GET", f"/musicas/{id}")
    def atualizar_musica(self, id, nome, artista): return self._req("PUT", f"/musicas/{id}", {"nome": nome, "artista": artista})
    def remover_musica(self, id): self._req("DELETE", f"/musicas/{id}")

    def criar_playlist(self, usuario_id, nome, musica_ids):
        return self._req("POST", f"/usuarios/{usuario_id}/playlists", {"nome": nome, "musicaIds": musica_ids})
    def listar_playlists_do_usuario(self, usuario_id): return self._req("GET", f"/usuarios/{usuario_id}/playlists")
    def obter_playlist(self, id): return self._req("GET", f"/playlists/{id}")
    def atualizar_playlist(self, id, nome, musica_ids):
        return self._req("PUT", f"/playlists/{id}", {"nome": nome, "musicaIds": musica_ids})
    def remover_playlist(self, id): self._req("DELETE", f"/playlists/{id}")

    def listar_musicas_da_playlist(self, playlist_id): return self._req("GET", f"/playlists/{playlist_id}/musicas")
    def listar_playlists_com_musica(self, musica_id): return self._req("GET", f"/musicas/{musica_id}/playlists")


# =================================================================== GraphQL
U = "id nome idade"
M = "id nome artista"
P = "id nome usuario { id } musicas { id }"


class ClienteGraphQL:
    """GraphQL: um único endpoint (POST /graphql); o cliente escolhe os campos."""

    def __init__(self, url: str):
        import requests
        self.url = url
        self.http = requests.Session()

    def _exec(self, consulta, campo, **variaveis):
        r = self.http.post(self.url, json={"query": consulta, "variables": variaveis}, timeout=10)
        try:
            corpo = r.json()
        except ValueError:
            raise ErroRemoto(f"HTTP {r.status_code}: {r.text[:200]}")
        if corpo.get("errors"):
            e = corpo["errors"][0]
            if (e.get("extensions") or {}).get("classification") == "NOT_FOUND":
                raise NaoEncontradoRemoto(e["message"])
            raise ErroRemoto(e["message"])
        valor = corpo["data"][campo]
        if valor is None:  # obter item inexistente devolve null
            raise NaoEncontradoRemoto(f"{campo} inexistente")
        return valor

    @staticmethod
    def _u(d): return {"id": int(d["id"]), "nome": d["nome"], "idade": d["idade"]}
    @staticmethod
    def _m(d): return {"id": int(d["id"]), "nome": d["nome"], "artista": d["artista"]}
    @staticmethod
    def _p(d): return {"id": int(d["id"]), "nome": d["nome"], "usuarioId": int(d["usuario"]["id"]),
                       "musicaIds": [int(m["id"]) for m in d["musicas"]]}

    def listar_usuarios(self):
        return [self._u(u) for u in self._exec(f"{{ usuarios {{ {U} }} }}", "usuarios")]
    def criar_usuario(self, nome, idade):
        return self._u(self._exec(f"mutation($i: UsuarioInput!) {{ criarUsuario(input: $i) {{ {U} }} }}",
                                  "criarUsuario", i={"nome": nome, "idade": idade}))
    def obter_usuario(self, id):
        return self._u(self._exec(f"query($id: ID!) {{ usuario(id: $id) {{ {U} }} }}", "usuario", id=id))
    def atualizar_usuario(self, id, nome, idade):
        return self._u(self._exec(f"mutation($id: ID!, $i: UsuarioInput!) {{ atualizarUsuario(id: $id, input: $i) {{ {U} }} }}",
                                  "atualizarUsuario", id=id, i={"nome": nome, "idade": idade}))
    def remover_usuario(self, id):
        self._exec("mutation($id: ID!) { removerUsuario(id: $id) }", "removerUsuario", id=id)

    def listar_musicas(self):
        return [self._m(m) for m in self._exec(f"{{ musicas {{ {M} }} }}", "musicas")]
    def criar_musica(self, nome, artista):
        return self._m(self._exec(f"mutation($i: MusicaInput!) {{ criarMusica(input: $i) {{ {M} }} }}",
                                  "criarMusica", i={"nome": nome, "artista": artista}))
    def obter_musica(self, id):
        return self._m(self._exec(f"query($id: ID!) {{ musica(id: $id) {{ {M} }} }}", "musica", id=id))
    def atualizar_musica(self, id, nome, artista):
        return self._m(self._exec(f"mutation($id: ID!, $i: MusicaInput!) {{ atualizarMusica(id: $id, input: $i) {{ {M} }} }}",
                                  "atualizarMusica", id=id, i={"nome": nome, "artista": artista}))
    def remover_musica(self, id):
        self._exec("mutation($id: ID!) { removerMusica(id: $id) }", "removerMusica", id=id)

    def criar_playlist(self, usuario_id, nome, musica_ids):
        return self._p(self._exec(f"mutation($u: ID!, $i: PlaylistInput!) {{ criarPlaylist(usuarioId: $u, input: $i) {{ {P} }} }}",
                                  "criarPlaylist", u=usuario_id, i={"nome": nome, "musicaIds": musica_ids}))
    def listar_playlists_do_usuario(self, usuario_id):
        return [self._p(p) for p in self._exec(f"query($u: ID!) {{ playlistsDoUsuario(usuarioId: $u) {{ {P} }} }}",
                                               "playlistsDoUsuario", u=usuario_id)]
    def obter_playlist(self, id):
        return self._p(self._exec(f"query($id: ID!) {{ playlist(id: $id) {{ {P} }} }}", "playlist", id=id))
    def atualizar_playlist(self, id, nome, musica_ids):
        return self._p(self._exec(f"mutation($id: ID!, $i: PlaylistInput!) {{ atualizarPlaylist(id: $id, input: $i) {{ {P} }} }}",
                                  "atualizarPlaylist", id=id, i={"nome": nome, "musicaIds": musica_ids}))
    def remover_playlist(self, id):
        self._exec("mutation($id: ID!) { removerPlaylist(id: $id) }", "removerPlaylist", id=id)

    def listar_musicas_da_playlist(self, playlist_id):
        return [self._m(m) for m in self._exec(f"query($p: ID!) {{ musicasDaPlaylist(playlistId: $p) {{ {M} }} }}",
                                               "musicasDaPlaylist", p=playlist_id)]
    def listar_playlists_com_musica(self, musica_id):
        return [self._p(p) for p in self._exec(f"query($m: ID!) {{ playlistsComMusica(musicaId: $m) {{ {P} }} }}",
                                               "playlistsComMusica", m=musica_id)]


# ====================================================================== SOAP
class ClienteSoap:
    """SOAP: o cliente (zeep) lê o WSDL e gera os métodos dinamicamente."""

    def __init__(self, url: str):
        from zeep import Client
        from zeep.transports import Transport
        self.cliente = Client(url + "?wsdl", transport=Transport(timeout=10))
        # usa sempre a URL informada (o WSDL pode anunciar 0.0.0.0 como endereço do serviço)
        binding = next(iter(self.cliente.wsdl.bindings))
        self.s = self.cliente.create_service(binding, url)

    def _chamar(self, operacao, **args):
        from zeep.exceptions import Fault
        try:
            return getattr(self.s, operacao)(**args)
        except Fault as f:
            if "NaoEncontrado" in str(f.code):
                raise NaoEncontradoRemoto(f.message)
            raise ErroRemoto(f"{f.code}: {f.message}")

    @staticmethod
    def _u(o): return {"id": int(o.id), "nome": o.nome, "idade": int(o.idade)}
    @staticmethod
    def _m(o): return {"id": int(o.id), "nome": o.nome, "artista": o.artista}
    @staticmethod
    def _p(o): return {"id": int(o.id), "nome": o.nome, "usuarioId": int(o.usuarioId),
                       "musicaIds": [int(x) for x in (o.musicaIds or [])]}

    def listar_usuarios(self): return [self._u(u) for u in self._chamar("listarUsuarios") or []]
    def criar_usuario(self, nome, idade): return self._u(self._chamar("criarUsuario", nome=nome, idade=idade))
    def obter_usuario(self, id): return self._u(self._chamar("obterUsuario", id=id))
    def atualizar_usuario(self, id, nome, idade): return self._u(self._chamar("atualizarUsuario", id=id, nome=nome, idade=idade))
    def remover_usuario(self, id): self._chamar("removerUsuario", id=id)

    def listar_musicas(self): return [self._m(m) for m in self._chamar("listarMusicas") or []]
    def criar_musica(self, nome, artista): return self._m(self._chamar("criarMusica", nome=nome, artista=artista))
    def obter_musica(self, id): return self._m(self._chamar("obterMusica", id=id))
    def atualizar_musica(self, id, nome, artista): return self._m(self._chamar("atualizarMusica", id=id, nome=nome, artista=artista))
    def remover_musica(self, id): self._chamar("removerMusica", id=id)

    def criar_playlist(self, usuario_id, nome, musica_ids):
        return self._p(self._chamar("criarPlaylist", usuarioId=usuario_id, nome=nome, musicaIds=musica_ids))
    def listar_playlists_do_usuario(self, usuario_id):
        return [self._p(p) for p in self._chamar("listarPlaylistsDoUsuario", usuarioId=usuario_id) or []]
    def obter_playlist(self, id): return self._p(self._chamar("obterPlaylist", id=id))
    def atualizar_playlist(self, id, nome, musica_ids):
        return self._p(self._chamar("atualizarPlaylist", id=id, nome=nome, musicaIds=musica_ids))
    def remover_playlist(self, id): self._chamar("removerPlaylist", id=id)

    def listar_musicas_da_playlist(self, playlist_id):
        return [self._m(m) for m in self._chamar("listarMusicasDaPlaylist", playlistId=playlist_id) or []]
    def listar_playlists_com_musica(self, musica_id):
        return [self._p(p) for p in self._chamar("listarPlaylistsComMusica", musicaId=musica_id) or []]


# ====================================================================== gRPC
def modulos_grpc():
    """(streaming_pb2, streaming_pb2_grpc) gerados a partir de contratos/streaming.proto."""
    sys.path.insert(0, str(RAIZ / "python" / "servico_grpc"))
    from codigo_gerado import carregar
    return carregar()


class ClienteGrpc:
    """gRPC: stub gerado a partir do .proto; chamadas parecem métodos locais."""

    def __init__(self, endereco: str):
        import grpc
        from google.protobuf import empty_pb2
        self.grpc = grpc
        self.pb, pb_grpc = modulos_grpc()
        self.vazio = empty_pb2.Empty()
        self.canal = grpc.insecure_channel(endereco)
        self.stub = pb_grpc.StreamingServiceStub(self.canal)

    def _chamar(self, metodo, req):
        try:
            return getattr(self.stub, metodo)(req, timeout=10)
        except self.grpc.RpcError as e:
            if e.code() == self.grpc.StatusCode.NOT_FOUND:
                raise NaoEncontradoRemoto(e.details())
            raise ErroRemoto(f"{e.code().name}: {e.details()}")

    @staticmethod
    def _u(o): return {"id": o.id, "nome": o.nome, "idade": o.idade}
    @staticmethod
    def _m(o): return {"id": o.id, "nome": o.nome, "artista": o.artista}
    @staticmethod
    def _p(o): return {"id": o.id, "nome": o.nome, "usuarioId": o.usuario_id, "musicaIds": list(o.musica_ids)}

    def _id(self, id): return self.pb.IdRequest(id=id)

    def listar_usuarios(self): return [self._u(u) for u in self._chamar("ListarUsuarios", self.vazio).usuarios]
    def criar_usuario(self, nome, idade): return self._u(self._chamar("CriarUsuario", self.pb.CriarUsuarioRequest(nome=nome, idade=idade)))
    def obter_usuario(self, id): return self._u(self._chamar("ObterUsuario", self._id(id)))
    def atualizar_usuario(self, id, nome, idade):
        return self._u(self._chamar("AtualizarUsuario", self.pb.AtualizarUsuarioRequest(id=id, nome=nome, idade=idade)))
    def remover_usuario(self, id): self._chamar("RemoverUsuario", self._id(id))

    def listar_musicas(self): return [self._m(m) for m in self._chamar("ListarMusicas", self.vazio).musicas]
    def criar_musica(self, nome, artista): return self._m(self._chamar("CriarMusica", self.pb.CriarMusicaRequest(nome=nome, artista=artista)))
    def obter_musica(self, id): return self._m(self._chamar("ObterMusica", self._id(id)))
    def atualizar_musica(self, id, nome, artista):
        return self._m(self._chamar("AtualizarMusica", self.pb.AtualizarMusicaRequest(id=id, nome=nome, artista=artista)))
    def remover_musica(self, id): self._chamar("RemoverMusica", self._id(id))

    def criar_playlist(self, usuario_id, nome, musica_ids):
        return self._p(self._chamar("CriarPlaylist", self.pb.CriarPlaylistRequest(usuario_id=usuario_id, nome=nome, musica_ids=musica_ids)))
    def listar_playlists_do_usuario(self, usuario_id):
        return [self._p(p) for p in self._chamar("ListarPlaylistsDoUsuario", self._id(usuario_id)).playlists]
    def obter_playlist(self, id): return self._p(self._chamar("ObterPlaylist", self._id(id)))
    def atualizar_playlist(self, id, nome, musica_ids):
        return self._p(self._chamar("AtualizarPlaylist", self.pb.AtualizarPlaylistRequest(id=id, nome=nome, musica_ids=musica_ids)))
    def remover_playlist(self, id): self._chamar("RemoverPlaylist", self._id(id))

    def listar_musicas_da_playlist(self, playlist_id):
        return [self._m(m) for m in self._chamar("ListarMusicasDaPlaylist", self._id(playlist_id)).musicas]
    def listar_playlists_com_musica(self, musica_id):
        return [self._p(p) for p in self._chamar("ListarPlaylistsComMusica", self._id(musica_id)).playlists]


def criar_cliente(tecnologia: str, endereco: str):
    return {"rest": ClienteRest, "graphql": ClienteGraphQL, "soap": ClienteSoap, "grpc": ClienteGrpc}[tecnologia](endereco)
