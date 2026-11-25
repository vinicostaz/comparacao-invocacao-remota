"""Cenários de carga do Locust para as 4 tecnologias.

Normalmente é executado pelo executar_testes.py, mas pode ser usado direto:
    CENARIO=consulta locust -f testes/carga/locustfile.py RestUser --host http://localhost:9001
    CENARIO=crud     locust -f testes/carga/locustfile.py GrpcUser --host localhost:9004
(sem --headless, abre a interface web do Locust em http://localhost:8089)

Cenários (variável de ambiente CENARIO):
  consulta       -> sorteia uma das cinco consultas do enunciado
  relacionamento -> lista as músicas de uma playlist sorteada
  catalogo       -> lista todas as músicas, exercitando respostas maiores
  crud           -> ciclo POST -> GET -> PUT -> DELETE de um usuário

Todas as tecnologias pedem os MESMOS dados (no GraphQL, os mesmos campos que o REST devolve),
e as requisições têm os mesmos nomes, para que as estatísticas sejam comparáveis.
"""
import os
import random
import re
import sys
import time
from pathlib import Path

import grpc.experimental.gevent as grpc_gevent

grpc_gevent.init_gevent()  # faz o gRPC cooperar com o gevent usado pelo Locust

import grpc  # noqa: E402
from google.protobuf import empty_pb2  # noqa: E402
from locust import User, constant  # noqa: E402
from locust.contrib.fasthttp import FastHttpUser  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "python" / "servico_grpc"))
from codigo_gerado import carregar  # noqa: E402

pb, pb_grpc = carregar()

CENARIO = os.environ.get("CENARIO", "consulta")
N_USUARIOS, N_MUSICAS, N_PLAYLISTS = 100, 200, 200  # dados iniciais dos servidores

CONSULTAS = ["listarMusicas", "musicasDaPlaylist", "playlistsComMusica", "playlistsDoUsuario", "obterUsuario"]


def sortear_consulta():
    nome = random.choice(CONSULTAS)
    if nome == "musicasDaPlaylist":
        return nome, random.randint(1, N_PLAYLISTS)
    if nome == "playlistsComMusica":
        return nome, random.randint(1, N_MUSICAS)
    if nome in ("playlistsDoUsuario", "obterUsuario"):
        return nome, random.randint(1, N_USUARIOS)
    return nome, None


def executar(usuario):
    """Tarefa única: despacha para o cenário escolhido."""
    if CENARIO == "crud":
        usuario.crud(f"Carga {random.randint(1, 10**6)}", random.randint(18, 80))
    elif CENARIO == "relacionamento":
        usuario.consulta("musicasDaPlaylist", random.randint(1, N_PLAYLISTS))
    elif CENARIO == "catalogo":
        usuario.consulta("listarMusicas", None)
    else:
        usuario.consulta(*sortear_consulta())


class BaseUser:
    """wait_time=0: cada usuário virtual envia a próxima requisição assim que
    recebe a resposta (carga máxima para aquele número de usuários simultâneos)."""
    wait_time = constant(0)
    tasks = [executar]


# ====================================================================== REST
class RestUser(BaseUser, FastHttpUser):
    ROTAS = {
        "listarMusicas": lambda _: "/musicas",
        "musicasDaPlaylist": lambda i: f"/playlists/{i}/musicas",
        "playlistsComMusica": lambda i: f"/musicas/{i}/playlists",
        "playlistsDoUsuario": lambda i: f"/usuarios/{i}/playlists",
        "obterUsuario": lambda i: f"/usuarios/{i}",
    }

    def consulta(self, nome, arg):
        self.client.get(self.ROTAS[nome](arg), name=nome)

    def crud(self, nome, idade):
        r = self.client.post("/usuarios", json={"nome": nome, "idade": idade}, name="POST criar")
        if not r.ok:
            return
        uid = r.json()["id"]
        self.client.get(f"/usuarios/{uid}", name="GET obter")
        self.client.put(f"/usuarios/{uid}", json={"nome": nome + " v2", "idade": idade + 1}, name="PUT atualizar")
        self.client.delete(f"/usuarios/{uid}", name="DELETE remover")


# =================================================================== GraphQL
P = "id nome usuario { id } musicas { id }"  # mesmos dados que o JSON de playlist do REST
GQL = {
    "listarMusicas": ("{ musicas { id nome artista } }", None),
    "musicasDaPlaylist": ("query($id: ID!) { musicasDaPlaylist(playlistId: $id) { id nome artista } }", "id"),
    "playlistsComMusica": (f"query($id: ID!) {{ playlistsComMusica(musicaId: $id) {{ {P} }} }}", "id"),
    "playlistsDoUsuario": (f"query($id: ID!) {{ playlistsDoUsuario(usuarioId: $id) {{ {P} }} }}", "id"),
    "obterUsuario": ("query($id: ID!) { usuario(id: $id) { id nome idade } }", "id"),
}
GQL_CRIAR = "mutation($i: UsuarioInput!) { criarUsuario(input: $i) { id nome idade } }"
GQL_OBTER = "query($id: ID!) { usuario(id: $id) { id nome idade } }"
GQL_ATUALIZAR = "mutation($id: ID!, $i: UsuarioInput!) { atualizarUsuario(id: $id, input: $i) { id nome idade } }"
GQL_REMOVER = "mutation($id: ID!) { removerUsuario(id: $id) }"


class GraphQLUser(BaseUser, FastHttpUser):

    def _gql(self, nome, consulta, variaveis=None):
        with self.client.post("/graphql", json={"query": consulta, "variables": variaveis or {}},
                              name=nome, catch_response=True) as r:
            try:
                corpo = r.json()
            except Exception:
                r.failure(f"HTTP {r.status_code}")
                return None
            if corpo.get("errors"):
                r.failure(corpo["errors"][0].get("message"))
                return None
            return corpo.get("data")

    def consulta(self, nome, arg):
        consulta, var = GQL[nome]
        self._gql(nome, consulta, {var: arg} if var else None)

    def crud(self, nome, idade):
        dados = self._gql("POST criar", GQL_CRIAR, {"i": {"nome": nome, "idade": idade}})
        if not dados:
            return
        uid = dados["criarUsuario"]["id"]
        self._gql("GET obter", GQL_OBTER, {"id": uid})
        self._gql("PUT atualizar", GQL_ATUALIZAR, {"id": uid, "i": {"nome": nome + " v2", "idade": idade + 1}})
        self._gql("DELETE remover", GQL_REMOVER, {"id": uid})


# ====================================================================== SOAP
NS = "http://streaming.exemplo.com/soap"
ENVELOPE = ('<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
            f'xmlns:tns="{NS}"><soapenv:Body>{{corpo}}</soapenv:Body></soapenv:Envelope>')
CABECALHOS_SOAP = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": '""'}
RE_ID = re.compile(r"<(?:\w+:)?id>(\d+)</")


def operacao_soap(operacao, **params):
    """Monta o envelope document/literal wrapped: <tns:operacao><tns:param>v</tns:param></tns:operacao>"""
    campos = "".join(f"<tns:{k}>{v}</tns:{k}>" for k, v in params.items())
    return ENVELOPE.format(corpo=f"<tns:{operacao}>{campos}</tns:{operacao}>")


SOAP = {
    "listarMusicas": lambda _: operacao_soap("listarMusicas"),
    "musicasDaPlaylist": lambda i: operacao_soap("listarMusicasDaPlaylist", playlistId=i),
    "playlistsComMusica": lambda i: operacao_soap("listarPlaylistsComMusica", musicaId=i),
    "playlistsDoUsuario": lambda i: operacao_soap("listarPlaylistsDoUsuario", usuarioId=i),
    "obterUsuario": lambda i: operacao_soap("obterUsuario", id=i),
}


class SoapUser(BaseUser, FastHttpUser):
    caminho = "/soap/streaming"

    def _soap(self, nome, envelope):
        with self.client.post(self.caminho, data=envelope.encode("utf-8"), headers=CABECALHOS_SOAP,
                              name=nome, catch_response=True) as r:
            texto = r.text or ""
            if r.status_code != 200 or "Fault>" in texto:
                r.failure(f"HTTP {r.status_code} / SOAP Fault")
                return None
            return texto

    def consulta(self, nome, arg):
        self._soap(nome, SOAP[nome](arg))

    def crud(self, nome, idade):
        resposta = self._soap("POST criar", operacao_soap("criarUsuario", nome=nome, idade=idade))
        achado = RE_ID.search(resposta or "")
        if not achado:
            return
        uid = achado.group(1)
        self._soap("GET obter", operacao_soap("obterUsuario", id=uid))
        self._soap("PUT atualizar", operacao_soap("atualizarUsuario", id=uid, nome=nome + " v2", idade=idade + 1))
        self._soap("DELETE remover", operacao_soap("removerUsuario", id=uid))


# ====================================================================== gRPC
class GrpcUser(BaseUser, User):
    """O Locust não tem cliente gRPC embutido: medimos o tempo de cada chamada e
    registramos o resultado no Locust com events.request.fire()."""

    VAZIO = empty_pb2.Empty()

    def on_start(self):
        self.canal = grpc.insecure_channel(self.host)
        self.stub = pb_grpc.StreamingServiceStub(self.canal)

    def on_stop(self):
        self.canal.close()

    def _rpc(self, nome, metodo, requisicao):
        inicio = time.perf_counter()
        resposta, erro, tamanho = None, None, 0
        try:
            resposta = metodo(requisicao, timeout=30)
            tamanho = resposta.ByteSize()
        except grpc.RpcError as e:
            erro = e
        self.environment.events.request.fire(
            request_type="grpc", name=nome, response_time=(time.perf_counter() - inicio) * 1000,
            response_length=tamanho, exception=erro, context={},
        )
        return resposta

    def consulta(self, nome, arg):
        s, pb_id = self.stub, (pb.IdRequest(id=arg) if arg else None)
        if nome == "listarMusicas":
            self._rpc(nome, s.ListarMusicas, self.VAZIO)
        elif nome == "musicasDaPlaylist":
            self._rpc(nome, s.ListarMusicasDaPlaylist, pb_id)
        elif nome == "playlistsComMusica":
            self._rpc(nome, s.ListarPlaylistsComMusica, pb_id)
        elif nome == "playlistsDoUsuario":
            self._rpc(nome, s.ListarPlaylistsDoUsuario, pb_id)
        else:
            self._rpc(nome, s.ObterUsuario, pb_id)

    def crud(self, nome, idade):
        s = self.stub
        u = self._rpc("POST criar", s.CriarUsuario, pb.CriarUsuarioRequest(nome=nome, idade=idade))
        if u is None:
            return
        self._rpc("GET obter", s.ObterUsuario, pb.IdRequest(id=u.id))
        self._rpc("PUT atualizar", s.AtualizarUsuario,
                  pb.AtualizarUsuarioRequest(id=u.id, nome=nome + " v2", idade=idade + 1))
        self._rpc("DELETE remover", s.RemoverUsuario, pb.IdRequest(id=u.id))


CLASSES = {"rest": "RestUser", "graphql": "GraphQLUser", "soap": "SoapUser", "grpc": "GrpcUser"}
