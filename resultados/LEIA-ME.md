# Resultados dos testes de carga

## Metodologia

Os oito serviços foram medidos separadamente, com o gerador Locust e o servidor na mesma máquina. Antes das medições, cada processo recebeu um período de aquecimento. Todos usaram os mesmos dados iniciais e as mesmas operações.

Foram combinados:

- duas linguagens: Java e Python;
- quatro tecnologias: REST, GraphQL, SOAP e gRPC;
- quatro cenários: consulta, relacionamento, catálogo e CRUD;
- cinco cargas: 1, 10, 20, 30 e 40 usuários simultâneos.

Isso gerou 160 pontos agregados e 2.227.534 requisições, sem falhas. Os gráficos usam escala linear.

## Consultas variadas

| Serviço | Vazão máxima medida | Carga do máximo | p95 com 40 usuários |
|---|---:|---:|---:|
| gRPC Java | 10.837,3 req/s | 30 | 4 ms |
| REST Java | 9.833,8 req/s | 30 | 4 ms |
| REST Python | 7.820,2 req/s | 10 | 9 ms |
| GraphQL Java | 6.925,8 req/s | 10 | 7 ms |
| gRPC Python | 5.376,5 req/s | 40 | 12 ms |
| SOAP Java | 946,4 req/s | 40 | 44 ms |
| GraphQL Python | 571,7 req/s | 10 | 94 ms |
| SOAP Python | 495,5 req/s | 1 | 210 ms |

## Catálogo completo

O cenário de catálogo separa o custo de serializar 200 músicas. Com 40 usuários, o p95 chegou a 760 ms no SOAP Python e 110 ms no GraphQL Python. REST Python ficou em 11 ms e gRPC Python em 30 ms. Em Java, REST e gRPC permaneceram em 5 ms e 4 ms, respectivamente.

## Tamanho de resposta

| Tecnologia | Java | Python |
|---|---:|---:|
| REST | 10,3 KB | 10,3 KB |
| GraphQL | 10,7 KB | 10,7 KB |
| SOAP | 17,3 KB | 22,1 KB |
| gRPC | 5,4 KB | 5,4 KB |

## Interpretação

- Java apresentou maior vazão em GraphQL e gRPC nesta máquina.
- REST Python foi competitivo nos cenários de relacionamento e CRUD.
- O custo de XML apareceu com mais força no catálogo e nas cargas maiores do SOAP Python.
- Após a vazão estabilizar, novas cargas aumentaram principalmente a latência. Os pontos 20 e 30 tornaram essa transição mais visível.
- O ponto registrado em `saturacao.csv` representa a menor carga que atingiu 90% da maior vazão observada no intervalo. Quando ele ocorre em 40, a saturação real pode estar acima da faixa testada.

Esses resultados dependem da máquina, versões das bibliotecas, duração do teste e implementação. Eles devem apoiar a análise crítica do trabalho, não uma conclusão universal sobre os protocolos.
