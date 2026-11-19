from __future__ import annotations

import argparse
import csv
import json
import math
import os
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable
from xml.etree import ElementTree

import grpc
import httpx

from music_service.config import project_root
from music_service.seed import seed
from music_service.services.grpc_api.generated import music_pb2, music_pb2_grpc


SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
TNS = "urn:music-service"
PROTOCOLS = ("REST", "GraphQL", "SOAP", "gRPC")
PROFILES = ("entity_read", "relationship_read", "write_cycle")


@dataclass
class Sample:
    elapsed_ms: float
    response_bytes: int
    success: bool


@dataclass
class Result:
    protocol: str
    profile: str
    concurrency: int
    requests: int
    successes: int
    errors: int
    duration_s: float
    throughput_rps: float
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_response_bytes: float


def percentile(values: list[float], value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(value * len(ordered)) - 1))
    return ordered[index]


class HttpAdapter:
    def __init__(self, protocol: str, url: str):
        self.protocol = protocol
        self.url = url
        self.client = httpx.Client(timeout=15.0)
        self.counter = 0
        self.lock = threading.Lock()

    def next_id(self) -> int:
        with self.lock:
            self.counter += 1
            return self.counter

    def rest(self, profile: str) -> int:
        if profile == "entity_read":
            response = self.client.get(f"{self.url}/users/1")
            response.raise_for_status()
            return len(response.content)
        if profile == "relationship_read":
            response = self.client.get(f"{self.url}/playlists/1/songs")
            response.raise_for_status()
            return len(response.content)
        unique = self.next_id()
        response = self.client.post(
            f"{self.url}/users", json={"name": f"Carga {unique}", "age": 30}
        )
        response.raise_for_status()
        created = response.json()
        deleted = self.client.delete(f"{self.url}/users/{created['id']}")
        deleted.raise_for_status()
        return len(response.content) + len(deleted.content)

    def graphql(self, profile: str) -> int:
        if profile == "entity_read":
            query = "query { user(id: 1) { id name age } }"
            variables = None
        elif profile == "relationship_read":
            query = "query { playlist(id: 1) { id name songs { id name artist } } }"
            variables = None
        else:
            unique = self.next_id()
            query = """
            mutation CreateDelete($input: UserInput!) {
              createUser(input: $input) { id name age }
            }
            """
            variables = {"input": {"name": f"Carga {unique}", "age": 30}}
        response = self.client.post(self.url, json={"query": query, "variables": variables})
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            raise RuntimeError(payload["errors"])
        size = len(response.content)
        if profile == "write_cycle":
            user_id = payload["data"]["createUser"]["id"]
            delete = self.client.post(
                self.url,
                json={"query": f"mutation {{ deleteUser(id: {user_id}) {{ success }} }}"},
            )
            delete.raise_for_status()
            if delete.json().get("errors"):
                raise RuntimeError(delete.json()["errors"])
            size += len(delete.content)
        return size

    @staticmethod
    def soap_envelope(operation: str, params: dict[str, str | int] | None = None) -> bytes:
        envelope = ElementTree.Element(f"{{{SOAP_NS}}}Envelope")
        body = ElementTree.SubElement(envelope, f"{{{SOAP_NS}}}Body")
        method = ElementTree.SubElement(body, f"{{{TNS}}}{operation}")
        for key, value in (params or {}).items():
            element = ElementTree.SubElement(method, f"{{{TNS}}}{key}")
            element.text = str(value)
        return ElementTree.tostring(envelope, encoding="utf-8", xml_declaration=True)

    def soap_call(self, operation: str, params: dict[str, str | int] | None = None) -> bytes:
        response = self.client.post(
            self.url,
            content=self.soap_envelope(operation, params),
            headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": operation},
        )
        response.raise_for_status()
        if b"Fault" in response.content:
            raise RuntimeError(response.text)
        return response.content

    def soap(self, profile: str) -> int:
        if profile == "entity_read":
            return len(self.soap_call("get_user", {"user_id": 1}))
        if profile == "relationship_read":
            return len(self.soap_call("list_songs_by_playlist", {"playlist_id": 1}))
        unique = self.next_id()
        created = self.soap_call("create_user", {"name": f"Carga {unique}", "age": 30})
        root = ElementTree.fromstring(created)
        id_element = next(element for element in root.iter() if element.tag.endswith("id"))
        deleted = self.soap_call("delete_user", {"user_id": int(id_element.text or "0")})
        return len(created) + len(deleted)

    def call(self, profile: str) -> int:
        if self.protocol == "REST":
            return self.rest(profile)
        if self.protocol == "GraphQL":
            return self.graphql(profile)
        return self.soap(profile)

    def close(self) -> None:
        self.client.close()


class GrpcAdapter:
    def __init__(self, target: str):
        self.channel = grpc.insecure_channel(target)
        self.stub = music_pb2_grpc.MusicServiceStub(self.channel)
        self.counter = 0
        self.lock = threading.Lock()

    def next_id(self) -> int:
        with self.lock:
            self.counter += 1
            return self.counter

    def call(self, profile: str) -> int:
        if profile == "entity_read":
            response = self.stub.GetUser(music_pb2.IdRequest(id=1), timeout=15)
        elif profile == "relationship_read":
            response = self.stub.ListSongsByPlaylist(music_pb2.IdRequest(id=1), timeout=15)
        else:
            unique = self.next_id()
            response = self.stub.CreateUser(
                music_pb2.UserInput(name=f"Carga {unique}", age=30), timeout=15
            )
            deleted = self.stub.DeleteUser(music_pb2.IdRequest(id=response.id), timeout=15)
            return response.ByteSize() + deleted.ByteSize()
        return response.ByteSize()

    def close(self) -> None:
        self.channel.close()


def execute(protocol: str, profile: str, concurrency: int, requests: int) -> Result:
    if protocol == "REST":
        adapter = HttpAdapter(protocol, "http://127.0.0.1:8001")
    elif protocol == "GraphQL":
        adapter = HttpAdapter(protocol, "http://127.0.0.1:8002/graphql")
    elif protocol == "SOAP":
        adapter = HttpAdapter(protocol, "http://127.0.0.1:8003/")
    else:
        adapter = GrpcAdapter("127.0.0.1:50051")

    for _ in range(min(10, requests)):
        adapter.call(profile)

    barrier = threading.Barrier(concurrency)

    def one() -> Sample:
        try:
            barrier.wait(timeout=20)
        except threading.BrokenBarrierError:
            pass
        started = time.perf_counter()
        try:
            size = adapter.call(profile)
            return Sample((time.perf_counter() - started) * 1000, size, True)
        except Exception:
            return Sample((time.perf_counter() - started) * 1000, 0, False)

    started = time.perf_counter()
    samples: list[Sample] = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(one) for _ in range(requests)]
        for future in as_completed(futures):
            samples.append(future.result())
    duration = time.perf_counter() - started
    adapter.close()
    successful = [sample for sample in samples if sample.success]
    latencies = [sample.elapsed_ms for sample in successful]
    sizes = [sample.response_bytes for sample in successful]
    return Result(
        protocol=protocol,
        profile=profile,
        concurrency=concurrency,
        requests=requests,
        successes=len(successful),
        errors=requests - len(successful),
        duration_s=round(duration, 4),
        throughput_rps=round(len(successful) / duration, 2) if duration else 0,
        mean_ms=round(sum(latencies) / len(latencies), 2) if latencies else 0,
        p50_ms=round(percentile(latencies, 0.50), 2),
        p95_ms=round(percentile(latencies, 0.95), 2),
        p99_ms=round(percentile(latencies, 0.99), 2),
        mean_response_bytes=round(sum(sizes) / len(sizes), 2) if sizes else 0,
    )


def wait_http(url: str, timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if httpx.get(url, timeout=1).status_code < 500:
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"servidor nao iniciou: {url}")


def wait_port(port: int, timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket() as sock:
            sock.settimeout(0.5)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.2)
    raise RuntimeError(f"porta {port} nao abriu")


def start_servers(root: Path, db: Path) -> list[subprocess.Popen]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(root / "src")
    environment["MUSIC_DB"] = str(db)
    commands = [
        [sys.executable, "-m", "uvicorn", "music_service.services.rest:app", "--host", "127.0.0.1", "--port", "8001", "--log-level", "warning"],
        [sys.executable, "-m", "uvicorn", "music_service.services.graphql:app", "--host", "127.0.0.1", "--port", "8002", "--log-level", "warning"],
        [sys.executable, "-m", "music_service.services.soap"],
        [sys.executable, "-m", "music_service.services.grpc_api.server"],
    ]
    processes = [
        subprocess.Popen(command, cwd=root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for command in commands
    ]
    try:
        wait_http("http://127.0.0.1:8001/health")
        wait_http("http://127.0.0.1:8002/health")
        wait_http("http://127.0.0.1:8003/?wsdl")
        wait_port(50051)
    except Exception:
        stop_servers(processes)
        raise
    return processes


def stop_servers(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def write_results(results: list[Result], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(results[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(result) for result in results)
    output.with_suffix(".json").write_text(
        json.dumps([asdict(result) for result in results], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark comparavel dos quatro protocolos")
    parser.add_argument("--protocols", default=",".join(PROTOCOLS))
    parser.add_argument("--profiles", default=",".join(PROFILES))
    parser.add_argument("--concurrency", default="1,10,30")
    parser.add_argument("--requests", type=int, default=180)
    parser.add_argument("--output", type=Path, default=project_root() / "results" / "benchmark.csv")
    parser.add_argument("--no-start", action="store_true", help="usa servidores ja iniciados")
    args = parser.parse_args()

    protocols = [item.strip() for item in args.protocols.split(",")]
    profiles = [item.strip() for item in args.profiles.split(",")]
    concurrencies = [int(item) for item in args.concurrency.split(",")]
    root = project_root()
    db = root / "data" / "benchmark.db"
    seed(db)
    processes: list[subprocess.Popen] = []
    try:
        if not args.no_start:
            processes = start_servers(root, db)
        results: list[Result] = []
        for profile in profiles:
            for concurrency in concurrencies:
                for protocol in protocols:
                    result = execute(protocol, profile, concurrency, args.requests)
                    results.append(result)
                    print(
                        f"{protocol:7s} {profile:18s} c={concurrency:2d} "
                        f"{result.throughput_rps:8.2f} req/s p95={result.p95_ms:8.2f} ms "
                        f"erros={result.errors}"
                    )
        write_results(results, args.output)
        print(f"Resultados: {args.output}")
    finally:
        stop_servers(processes)


if __name__ == "__main__":
    main()

