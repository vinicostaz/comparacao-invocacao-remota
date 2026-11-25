"""Teste funcional: executa o MESMO roteiro (CRUD + 5 consultas do enunciado) em cada serviço.

Uso (na raiz do projeto, com os serviços já rodando):
    python testes/testar_servicos.py                 # testa os serviços que estiverem no ar
    python testes/testar_servicos.py --servicos python
    python testes/testar_servicos.py --servicos java-rest,python-rest
"""
import argparse
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from clientes import NaoEncontradoRemoto, criar_cliente
from servicos import selecionar


class Falha(Exception):
    pass


def verificar(condicao, mensagem):
    if not condicao:
        raise Falha(mensagem)


def espera_nao_encontrado(funcao, *args):
    try:
        funcao(*args)
    except NaoEncontradoRemoto:
        return
    raise Falha(f"{funcao.__name__}{args} deveria dar 'não encontrado'")


def roteiro(c):
    """Lista de (descrição, passo). Cada passo usa o cliente 'c' e um dicionário de estado."""
    s = {}

    def passo_listar_usuarios():
        us = c.listar_usuarios()
        verificar(len(us) >= 99, f"esperava ~100 usuários, veio {len(us)}")
        verificar(us[0]["nome"] == "Usuario 1", f"primeiro usuário inesperado: {us[0]}")

    def passo_listar_musicas():
        ms = c.listar_musicas()
        verificar(len(ms) >= 199, f"esperava ~200 músicas, veio {len(ms)}")
        verificar(ms[0] == {"id": 1, "nome": "Musica 1", "artista": "Artista 1"}, f"primeira música: {ms[0]}")

    def passo_criar_usuario():
        u = c.criar_usuario("Ana Teste", 30)
        verificar(u["nome"] == "Ana Teste" and u["idade"] == 30 and u["id"] > 100, f"usuário criado: {u}")
        s["u"] = u["id"]

    def passo_obter_usuario():
        verificar(c.obter_usuario(s["u"]) == {"id": s["u"], "nome": "Ana Teste", "idade": 30}, "dados divergentes")

    def passo_atualizar_usuario():
        u = c.atualizar_usuario(s["u"], "Ana Atualizada", 31)
        verificar(u == {"id": s["u"], "nome": "Ana Atualizada", "idade": 31}, f"retorno: {u}")
        verificar(c.obter_usuario(s["u"])["nome"] == "Ana Atualizada", "alteração não persistiu")

    def passo_criar_musica():
        m = c.criar_musica("Canção Nova", "Banda X")
        verificar(m["nome"] == "Canção Nova" and m["artista"] == "Banda X", f"música criada: {m}")
        s["m"] = m["id"]

    def passo_atualizar_musica():
        m = c.atualizar_musica(s["m"], "Canção Remix", "Banda Y")
        verificar(m == {"id": s["m"], "nome": "Canção Remix", "artista": "Banda Y"}, f"retorno: {m}")
        verificar(c.obter_musica(s["m"])["artista"] == "Banda Y", "alteração não persistiu")

    def passo_criar_playlist():
        p = c.criar_playlist(s["u"], "Minha Playlist", [s["m"], 1])
        verificar(p["usuarioId"] == s["u"] and p["musicaIds"] == [s["m"], 1], f"playlist criada: {p}")
        s["p"] = p["id"]

    def passo_obter_playlist():
        p = c.obter_playlist(s["p"])
        verificar(p == {"id": s["p"], "nome": "Minha Playlist", "usuarioId": s["u"], "musicaIds": [s["m"], 1]}, f"{p}")

    def passo_playlists_do_usuario():
        ps = c.listar_playlists_do_usuario(s["u"])
        verificar([p["id"] for p in ps] == [s["p"]], f"playlists do usuário: {ps}")
        ps1 = c.listar_playlists_do_usuario(1)
        verificar([p["id"] for p in ps1] == [1, 101], f"playlists do usuário 1: {[p['id'] for p in ps1]}")

    def passo_musicas_da_playlist():
        ms = c.listar_musicas_da_playlist(s["p"])
        verificar([m["id"] for m in ms] == [s["m"], 1], f"músicas: {ms}")
        verificar(ms[0]["nome"] == "Canção Remix", "dados da música não vieram completos")
        ms7 = c.listar_musicas_da_playlist(7)
        verificar([m["id"] for m in ms7] == [7, 24, 41, 58, 75, 92, 109, 126, 143, 160], f"playlist 7: {ms7}")

    def passo_playlists_com_musica():
        ps = c.listar_playlists_com_musica(s["m"])
        verificar([p["id"] for p in ps] == [s["p"]], f"playlists com a música: {ps}")
        ps18 = [p["id"] for p in c.listar_playlists_com_musica(18)]
        verificar(ps18 == [1, 18, 65, 82, 99, 116, 133, 150, 167, 184], f"playlists com música 18: {ps18}")

    def passo_atualizar_playlist():
        p = c.atualizar_playlist(s["p"], "Renomeada", [2, 3])
        verificar(p["nome"] == "Renomeada" and p["musicaIds"] == [2, 3], f"retorno: {p}")

    def passo_remover_musica():
        c.atualizar_playlist(s["p"], "Renomeada", [s["m"], 2])
        c.remover_musica(s["m"])
        espera_nao_encontrado(c.obter_musica, s["m"])
        verificar(c.obter_playlist(s["p"])["musicaIds"] == [2], "música removida continuou na playlist")

    def passo_remover_playlist():
        c.remover_playlist(s["p"])
        espera_nao_encontrado(c.obter_playlist, s["p"])

    def passo_remover_usuario():
        p2 = c.criar_playlist(s["u"], "Outra", [5])
        c.remover_usuario(s["u"])
        espera_nao_encontrado(c.obter_usuario, s["u"])
        espera_nao_encontrado(c.obter_playlist, p2["id"])  # composição: playlists somem com o usuário

    def passo_erros():
        espera_nao_encontrado(c.obter_usuario, 999999)
        espera_nao_encontrado(c.remover_musica, 999999)
        espera_nao_encontrado(c.listar_musicas_da_playlist, 999999)

    return [
        ("GET    listar usuários", passo_listar_usuarios),
        ("GET    listar músicas", passo_listar_musicas),
        ("POST   criar usuário", passo_criar_usuario),
        ("GET    obter usuário", passo_obter_usuario),
        ("PUT    atualizar usuário", passo_atualizar_usuario),
        ("POST   criar música", passo_criar_musica),
        ("PUT    atualizar música", passo_atualizar_musica),
        ("POST   criar playlist", passo_criar_playlist),
        ("GET    obter playlist", passo_obter_playlist),
        ("GET    playlists de um usuário", passo_playlists_do_usuario),
        ("GET    músicas de uma playlist", passo_musicas_da_playlist),
        ("GET    playlists que contêm uma música", passo_playlists_com_musica),
        ("PUT    atualizar playlist", passo_atualizar_playlist),
        ("DELETE remover música", passo_remover_musica),
        ("DELETE remover playlist", passo_remover_playlist),
        ("DELETE remover usuário (+ playlists)", passo_remover_usuario),
        ("ERRO   recurso inexistente", passo_erros),
    ]


def testar(servico, detalhado=False):
    print(f"\n=== {servico.nome}  ({servico.endereco})")
    try:
        cliente = criar_cliente(servico.tecnologia, servico.endereco)
    except Exception as e:
        print(f"  [FALHOU] não foi possível criar o cliente: {e}")
        return False
    ok = True
    for descricao, passo in roteiro(cliente):
        try:
            passo()
            print(f"  [ok]     {descricao}")
        except Exception as e:
            ok = False
            print(f"  [FALHOU] {descricao}: {type(e).__name__}: {e}")
            if detalhado:
                traceback.print_exc()
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--servicos", help="ex.: todos | java | python | rest | java-rest,python-grpc")
    ap.add_argument("-v", "--detalhado", action="store_true")
    args = ap.parse_args()

    alvos = selecionar(args.servicos)
    if not args.servicos:
        alvos = [s for s in alvos if s.no_ar()]
        if not alvos:
            raise SystemExit("Nenhum serviço no ar. Inicie os servidores (ver README).")
    resultados = {s.nome: testar(s, args.detalhado) for s in alvos}

    print("\nResumo:")
    for nome, ok in resultados.items():
        print(f"  {'OK    ' if ok else 'FALHOU'}  {nome}")
    sys.exit(0 if all(resultados.values()) else 1)


if __name__ == "__main__":
    main()
