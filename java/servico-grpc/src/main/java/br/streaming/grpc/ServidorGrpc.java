package br.streaming.grpc;

import io.grpc.Server;
import io.grpc.ServerBuilder;

/**
 * Sobe o servidor gRPC (HTTP/2 + Protocol Buffers, transporte Netty).
 * Porta padrão 8004; para mudar: java -Dporta=XXXX -jar target/servico-grpc.jar
 */
public class ServidorGrpc {

    public static void main(String[] args) throws Exception {
        int porta = Integer.getInteger("porta", 8004);

        Server servidor = ServerBuilder.forPort(porta)
                .addService(new StreamingGrpcService())
                .build()
                .start();

        System.out.println("Servidor gRPC (Java / grpc-java) ouvindo em localhost:" + porta);
        Runtime.getRuntime().addShutdownHook(new Thread(servidor::shutdown));
        servidor.awaitTermination();
    }
}
