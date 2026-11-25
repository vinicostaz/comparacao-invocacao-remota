package br.streaming.soap;

import jakarta.xml.ws.Endpoint;

import java.util.concurrent.Executors;

/**
 * Publica o serviço SOAP usando o servidor HTTP embutido no JDK (JAX-WS RI).
 * Porta padrão 8003; para mudar: java -Dporta=XXXX -jar target/servico-soap.jar
 */
public class ServidorSoap {

    public static void main(String[] args) {
        int porta = Integer.getInteger("porta", 8003);
        String endereco = "http://0.0.0.0:" + porta + "/soap/streaming";

        Endpoint endpoint = Endpoint.create(new StreamingSoapService());
        // por padrão o servidor do JDK atende uma requisição por vez; usamos um pool de threads
        endpoint.setExecutor(Executors.newFixedThreadPool(64));
        endpoint.publish(endereco);

        System.out.println("Servidor SOAP (Java / JAX-WS) ouvindo em http://localhost:" + porta
                + "/soap/streaming  (WSDL: ?wsdl)");
    }
}
