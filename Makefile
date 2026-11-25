.PHONY: setup build-java start test benchmark charts

setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -r python/requirements.txt

build-java:
	cd java && mvn -q package

start:
	.venv/bin/python testes/iniciar_servicos.py

test:
	.venv/bin/python testes/testar_servicos.py --servicos todos

benchmark:
	.venv/bin/python testes/carga/executar_testes.py \
		--servicos todos --usuarios 1,10,20,30,40 \
		--cenarios consulta,relacionamento,catalogo,crud

charts:
	.venv/bin/python testes/carga/graficos.py resultados
