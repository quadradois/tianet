from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]


def _compose_config() -> dict[str, Any]:
    environment = os.environ.copy()
    environment.update(
        {
            "POSTGRES_PASSWORD": "compose-test-password",
            "JWT_SECRET_KEY": "compose-test-jwt",
            "FRONTEND_SESSION_KEY_ID": "compose-test",
            "FRONTEND_SESSION_KEY": "x" * 43,
            "TIANET_AGENT_INTERNAL_SECRET": "s" * 32,
        }
    )
    completed = subprocess.run(
        ["docker", "compose", "config", "--format", "json"],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    value: object = json.loads(completed.stdout)
    assert isinstance(value, dict)
    return value


def test_agent_fica_em_rede_e_volume_exclusivos_sem_porta_publicada() -> None:
    config = _compose_config()
    agent = config["services"]["agent"]
    assert set(agent["networks"]) == {"agent-egress"}
    # Loopback publicado não é porta pública: só o Caddy do host alcança;
    # qualquer bind fora de 127.0.0.1 continua proibido (ingress WhatsApp).
    for publicada in agent.get("ports", []):
        assert publicada.get("host_ip", "") == "127.0.0.1", publicada
    assert agent["read_only"] is True
    assert agent["cap_drop"] == ["ALL"]
    assert agent["security_opt"] == ["no-new-privileges:true"]
    assert agent["environment"]["TIANET_AGENT_ENABLED"] == "false"
    assert agent["volumes"] == [
        {
            "type": "volume",
            "source": "agent-codex-data",
            "target": "/var/lib/tianet-agent/codex",
            "volume": {},
        },
        {
            "type": "volume",
            "source": "agent-runtime",
            "target": "/run/tianet-agent",
            "volume": {},
        },
    ]
    assert config["services"]["api"]["volumes"] == [
        {
            "type": "volume",
            "source": "agent-runtime",
            "target": "/run/tianet-agent",
            "read_only": True,
            "volume": {},
        }
    ]
    for service_name in ("api", "postgres", "worker", "migrate"):
        assert "agent-egress" not in config["services"][service_name]["networks"]


def test_compose_carrega_com_agent_desligado_e_sem_segredo() -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "POSTGRES_PASSWORD": "compose-test-password",
            "JWT_SECRET_KEY": "compose-test-jwt",
            "FRONTEND_SESSION_KEY_ID": "compose-test",
            "FRONTEND_SESSION_KEY": "x" * 43,
            "TIANET_AGENT_ENABLED": "false",
            "TIANET_AGENT_INTERNAL_SECRET": "",
        }
    )
    completed = subprocess.run(
        ["docker", "compose", "config", "--quiet"],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_imagem_fixa_cli_oficial_e_executa_com_usuario_sem_privilegio() -> None:
    dockerfile = (ROOT / "Dockerfile.agent").read_text(encoding="utf-8")
    assert "ARG CODEX_VERSION=0.146.1" in dockerfile
    assert "ARG CODEX_SHA256=" in dockerfile
    assert "github.com/openai/codex/releases/download/" in dockerfile
    assert "rust-v{version}/codex-x86_64-unknown-linux-musl.tar.gz" in dockerfile
    assert "hashlib.sha256(archive).hexdigest() != expected" in dockerfile
    assert "codex --version" in dockerfile
    assert "USER app" not in dockerfile
    assert "USER agent" in dockerfile
    assert "COPY docs" not in dockerfile
    assert "COPY migrations" not in dockerfile
    assert "COPY src ./src" not in dockerfile
    assert "COPY src/emprestimo/agent ./emprestimo/agent" in dockerfile
    # O ingress monta com UnitOfWork/SQLAlchemy reais: sem estes pacotes a
    # imagem quebra no boot (v1.1.28). Presentation/worker continuam fora.
    assert "COPY src/emprestimo/domain ./emprestimo/domain" in dockerfile
    assert "COPY src/emprestimo/application ./emprestimo/application" in dockerfile
    assert "COPY src/emprestimo/infrastructure ./emprestimo/infrastructure" in dockerfile
    assert "--require-hashes" in dockerfile
    assert "ghcr.io/astral-sh/uv@sha256:" in dockerfile
    assert "generate-json-schema" in dockerfile
    assert 'CMD ["python", "-m", "emprestimo.agent.server", "serve"]' in dockerfile


def test_ingress_tcp_liga_em_0000_com_perimetro_no_compose() -> None:
    """Guardrail do bind inalcançável (S1): 127.0.0.1 no container recusa o
    DNAT do publish — o bind precisa ser 0.0.0.0 e a restrição a 127.0.0.1
    vive no compose (coberta por
    test_agent_fica_em_rede_e_volume_exclusivos_sem_porta_publicada)."""
    server = (ROOT / "src" / "emprestimo" / "agent" / "server.py").read_text(encoding="utf-8")
    assert 'BIND_HOST = "0.0.0.0"' in server
    assert "LOOPBACK_HOST" not in server


def test_compose_prod_sem_tcp_do_agent_modo_socket() -> None:
    """Guardrail da topologia (S1/opção B): o agent vive SOMENTE na rede
    interna agent-egress, onde o daemon descarta publish sem NAT — publicar
    8010 ali é config morta que finge alcance. O prod sobe em modo socket
    Unix e o Caddy do host faz proxy para o socket do volume."""
    prod = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert "TIANET_AGENT_HTTP_PORT:" not in prod
    assert "8010:8010" not in prod
    assert "agent-runtime:/run/tianet-agent" in prod


def _terceiros_do_lock() -> set[str]:
    terceiros: set[str] = set()
    for linha in (ROOT / "requirements-agent.lock").read_text(encoding="utf-8").splitlines():
        if "==" in linha and not linha.startswith((" ", "#")):
            nome = linha.split("==")[0].strip().lower().replace("-", "_")
            terceiros.add(nome)
    return terceiros


_MODULO_PARA_PACOTE = {
    # Casos em que o módulo difere do nome da distribuição.
    "dotenv": "python_dotenv",
    "yaml": "pyyaml",
}


def _cadeia_de_boot() -> tuple[set[str], set[str]]:
    """Importações de terceiros alcançáveis do boot do agent (runtime).

    Segue apenas módulos `emprestimo.*` copiados para a imagem (agent,
    domain, application, infrastructure). Blocos `if TYPE_CHECKING:` são
    ignorados: anotação não exige o pacote em runtime — foi exatamente um
    import desses (httpx via metricas) que derrubou a v1.1.28.
    """
    import ast
    import sys

    raiz = ROOT / "src" / "emprestimo"
    pacotes_na_imagem = {"agent", "domain", "application", "infrastructure"}
    visitados: set[str] = set()
    terceiros: set[str] = set()
    proibidos: set[str] = set()

    def modulo_para_arquivo(modulo: str) -> Path | None:
        partes = modulo.split(".")
        assert partes[0] == "emprestimo"
        if partes[1] not in pacotes_na_imagem:
            if partes[1] in {"presentation", "worker"}:
                proibidos.add(modulo)
            return None
        base = raiz
        for parte in partes[1:]:
            base = base / parte
        if base.with_suffix(".py").is_file():
            return base.with_suffix(".py")
        candidato = base / "__init__.py"
        return candidato if candidato.is_file() else None

    def visitar(modulo: str, pacote_atual: str) -> None:
        if modulo in visitados:
            return
        visitados.add(modulo)
        arquivo = modulo_para_arquivo(modulo)
        if arquivo is None:
            return
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))

        def coletar(no: ast.AST, somente_tipos: bool = False) -> None:
            if (
                isinstance(no, ast.If)
                and isinstance(no.test, ast.Name)
                and no.test.id == "TYPE_CHECKING"
            ):
                for filho in no.body:
                    coletar(filho, somente_tipos=True)
                for filho in no.orelse:
                    coletar(filho, somente_tipos=somente_tipos)
                return
            if isinstance(no, (ast.Import, ast.ImportFrom)) and not somente_tipos:
                alvos = (
                    [a.name for a in no.names] if isinstance(no, ast.Import) else [no.module or ""]
                )
                for alvo in alvos:
                    topo = alvo.split(".")[0]
                    if not topo or topo == "__future__":
                        continue
                    if topo in sys.stdlib_module_names:
                        continue
                    if topo == "emprestimo":
                        visitar(alvo, pacote_atual)
                    else:
                        terceiros.add(topo)
                return
            for sub_no in ast.iter_child_nodes(no):
                coletar(sub_no, somente_tipos=somente_tipos)

        coletar(arvore)

    visitar("emprestimo.agent.server", "emprestimo.agent")
    visitar("emprestimo.agent.service", "emprestimo.agent")
    return terceiros, proibidos


def test_boot_do_agent_cabe_no_lock_sem_presentation() -> None:
    """Guardrail da v1.1.28: todo terceiro importado no boot existe no lock.

    O Quality passava com as dev-dependencies instaladas enquanto a imagem
    mínima quebrava (`No module named 'httpx'`). Este teste conta o efeito
    na fonte: a cadeia de import em runtime contra o lock com hashes.
    """
    terceiros, proibidos = _cadeia_de_boot()
    assert proibidos == set(), proibidos
    lock = _terceiros_do_lock()
    ausentes = {
        modulo for modulo in terceiros if _MODULO_PARA_PACOTE.get(modulo, modulo) not in lock
    }
    assert ausentes == set(), ausentes
    assert terceiros != set(), "a cadeia de boot deveria ter terceiros (fastapi)"
