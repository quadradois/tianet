"""Ports do Platform Context — contratos de persistência (Repository Pattern).

A camada Domain define os contratos; a Infrastructure implementa. O Domain
não conhece SQLAlchemy nem FastAPI (DECISION-001 / ADR-001).
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from emprestimo.domain.platform.conexao_whatsapp import ConexaoWhatsApp, EstadoPareamento
from emprestimo.domain.platform.configuracao import Configuracao
from emprestimo.domain.platform.credencial import Credencial
from emprestimo.domain.platform.perfil import PerfilAcesso
from emprestimo.domain.platform.permissao import Permissao
from emprestimo.domain.platform.sessao import Sessao
from emprestimo.domain.platform.tenant import Tenant, TenantState
from emprestimo.domain.platform.usuario import Usuario


@dataclass(frozen=True)
class TenantFiltro:
    """Filtros para listagem de Tenants (IMP-025)."""

    estado: TenantState | None = None


@dataclass(frozen=True)
class TenantOrdenacao:
    """Ordenação para listagem de Tenants (IMP-025)."""

    campo: Literal["criado_em", "identificador_institucional", "nome", "estado"] = "criado_em"
    direcao: Literal["asc", "desc"] = "asc"


@dataclass(frozen=True)
class TenantPaginado:
    """Resultado paginado de Tenants (IMP-025)."""

    items: list[Tenant]
    total: int
    page: int
    size: int
    pages: int


class TenantRepository(ABC):
    """Persistência do Aggregate Tenant (IMP-004)."""

    @abstractmethod
    def save(self, tenant: Tenant) -> None: ...

    @abstractmethod
    def find_by_id(self, tenant_id: uuid.UUID) -> Tenant | None: ...

    @abstractmethod
    def find_by_identificador_institucional(self, identificador: str) -> Tenant | None: ...

    @abstractmethod
    def find_all(self) -> list[Tenant]: ...

    @abstractmethod
    def find_all_paginated(
        self,
        page: int = 1,
        size: int = 20,
        ordenacao: TenantOrdenacao | None = None,
        filtro: TenantFiltro | None = None,
    ) -> TenantPaginado: ...


class UsuarioRepository(ABC):
    """Persistência da Entity Usuário (IMP-005)."""

    @abstractmethod
    def save(self, usuario: Usuario) -> None: ...

    @abstractmethod
    def find_by_id(self, usuario_id: uuid.UUID) -> Usuario | None: ...

    @abstractmethod
    def find_by_email(self, email: str) -> Usuario | None: ...

    @abstractmethod
    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[Usuario]: ...


class ConfiguracaoRepository(ABC):
    """Persistência da Entity Configuração (IMP-006)."""

    @abstractmethod
    def save(self, configuracao: Configuracao) -> None: ...

    @abstractmethod
    def find_by_id(self, configuracao_id: uuid.UUID) -> Configuracao | None: ...

    @abstractmethod
    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[Configuracao]: ...


class ConexaoWhatsAppRepository(ABC):
    """Persistencia da Entity ConexaoWhatsApp (IMP-365, PLAN-034).

    O token viaja SEPARADO da entidade, e de proposito: ele e segredo, e a
    entidade nao deve carrega-lo por engano para um log, uma resposta de API ou
    uma trilha de auditoria. Quem quiser o token pede por ele explicitamente, e
    quem quiser o estado da conexao nunca o recebe de brinde.

    A cifragem e responsabilidade da implementacao — o dominio nao conhece
    `cryptography`, nem deveria.
    """

    @abstractmethod
    def save(self, conexao: ConexaoWhatsApp, *, token: str | None = None) -> None:
        """Grava a conexao. `token=None` preserva o token ja guardado.

        Sem esse cuidado, um `save` de pareamento apagaria o token — e a conexao
        continuaria existindo, sem poder enviar nada.
        """

    @abstractmethod
    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> ConexaoWhatsApp | None: ...

    @abstractmethod
    def find_token(self, tenant_id: uuid.UUID) -> str | None:
        """Devolve o token decifrado. Unico caminho para obte-lo."""

    @abstractmethod
    def exigir_disponibilidade(self) -> None:
        """Falha AGORA se este repositorio nao puder guardar segredo.

        Existe para ser chamado antes de criar a instancia no provedor. Sem
        isso, uma chave de cifra ausente so apareceria no `save` — depois de o
        Evolution ja ter criado a instancia com o token que so nos tinhamos.
        Instancia inalcancavel por causa de uma variavel de ambiente esquecida.
        """

    @abstractmethod
    def delete(self, tenant_id: uuid.UUID) -> None:
        """Apaga a conexao do Tenant, token cifrado junto (IMP-368).

        Par local do `excluir_instancia`: manter a linha depois de a instancia
        ter sido apagada no provedor deixaria uma conexao que aponta para nada
        e um token que nao autentica mais em lugar nenhum.
        """

    @abstractmethod
    def bloquear_tenant(self, tenant_id: uuid.UUID) -> None:
        """Serializa a criacao de conexao para este Tenant na transacao atual.

        `UNIQUE (tenant_id)` so rejeita a segunda no commit — tarde demais, se as
        duas ja tiverem criado instancia no provedor. O lock e sobre o Tenant, e
        nao sobre a linha, porque no caso que importa a linha ainda nao existe.
        """


class QrCodeIndisponivelError(RuntimeError):
    """O QR ainda nao existe. Estado NORMAL logo apos conectar, nao falha.

    Nomeado no dominio para que a Application possa distinguir "espere e tente
    de novo" de "o provedor caiu" sem importar o cliente HTTP.
    """


class EfeitoNaoAplicadoError(RuntimeError):
    """A operacao **comprovadamente** nao aconteceu no provedor.

    Espelha a allowlist da ADR-009 para envio, no outro sentido: so e levantada
    quando ha prova de nao execucao — a requisicao nao saiu da maquina, ou o
    provedor a recusou antes de agir. Toda falha ambigua fica de fora, porque a
    Application usa esta excecao para decidir entre registrar rollback (o estado
    voltou) e divergencia (o efeito externo ficou), e a segunda e a afirmacao
    segura quando nao se sabe.
    """


class ProvedorWhatsApp(ABC):
    """Operacoes de instancia no provedor, sem o protocolo HTTP a tiracolo.

    A Application orquestra criar, conectar, ler estado e desconectar; nao
    conhece rotas, chaves de tenant nem formato de QR. O token entra como
    parametro em vez de virar estado do adapter porque quem sabe qual token usar
    e o repositorio, e ele so entrega o valor a quem pedir explicitamente.
    """

    @abstractmethod
    def instancia_existente(self, nome: str) -> tuple[str, str] | None:
        """Procura instancia ja criada no provedor e devolve `(id, token)`.

        Existe porque "nao ha registro local" nao significa "nao ha instancia":
        fecha a janela do `create` cuja resposta se perdeu, em que o provedor
        criou e nos nao guardamos o `instancia_id`. Nessa janela o **nome e a
        unica pista**, e por isso ele e gerado pela plataforma a partir do
        Tenant (IMP-368) — um nome digitado tornaria a recuperacao dependente
        de alguem redigitar exatamente igual.

        Ate o IMP-367 este metodo justificava-se por outra premissa — "a
        instancia do TiaNet foi criada a mao antes desta tela existir". O
        fundador esclareceu em 2026-09-02 que ela nasceu dos nossos proprios
        testes; a premissa caiu, a janela do `create` perdido permaneceu.
        """

    @abstractmethod
    def excluir_instancia(self, instancia_id: str) -> None:
        """Apaga a instancia no provedor (IMP-368).

        Diferente de `desconectar`, que so desvincula o numero: aqui a
        instancia deixa de existir, e com ela o token. Existe porque o logout
        sozinho acumula instancias mortas no provedor — cada uma um nome, um
        token e uma sessao que ninguem usa.

        **Idempotente:** instancia ja ausente e sucesso, nao erro. Quem chama
        quer o fim, e o fim ja aconteceu.
        """

    @abstractmethod
    def criar_instancia(self, nome: str) -> tuple[str, str]:
        """Cria a instancia e devolve `(instancia_id, token)`.

        **O token e gerado por nos**; o provedor apenas o ecoa. Quem procurar um
        identificador emitido pelo servidor nao vai encontrar.
        """

    @abstractmethod
    def conectar(self, token: str) -> None:
        """Inicia o pareamento. Idempotente numa instancia ja conectada."""

    @abstractmethod
    def qrcode(self, token: str) -> str:
        """QR em base64. Levanta `QrCodeIndisponivelError` enquanto gera."""

    @abstractmethod
    def estado(self, token: str, instancia_id: str) -> EstadoPareamento:
        """Estado do pareamento e, quando pareada, o numero da conta.

        Recebe os dois identificadores porque as duas informacoes vivem atras de
        autenticacoes diferentes no provedor: `LoggedIn` responde ao token da
        instancia, e o `jid` com o telefone responde a chave de Tenant.
        """

    @abstractmethod
    def desconectar(self, token: str) -> None:
        """Desvincula o numero. A instancia permanece."""


class CredencialRepository(ABC):
    """Persistencia da Entity Credencial (IMP-086)."""

    @abstractmethod
    def save(self, credencial: Credencial) -> None: ...

    @abstractmethod
    def find_by_id(self, credencial_id: uuid.UUID) -> Credencial | None: ...

    @abstractmethod
    def find_by_usuario_id(self, usuario_id: uuid.UUID) -> Credencial | None: ...


class SessaoRepository(ABC):
    """Persistencia da Entity Sessao (IMP-086)."""

    @abstractmethod
    def save(self, sessao: Sessao) -> None: ...

    @abstractmethod
    def find_by_id(self, sessao_id: uuid.UUID) -> Sessao | None: ...

    @abstractmethod
    def find_by_usuario_id(self, usuario_id: uuid.UUID) -> list[Sessao]: ...

    @abstractmethod
    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[Sessao]: ...


class PermissaoRepository(ABC):
    """Persistencia do catalogo de Permissoes (IMP-086)."""

    @abstractmethod
    def save(self, permissao: Permissao) -> None: ...

    @abstractmethod
    def find_by_codigo(self, codigo: str) -> Permissao | None: ...

    @abstractmethod
    def find_all(self) -> list[Permissao]: ...


class PerfilAcessoRepository(ABC):
    """Persistencia do Perfil de Acesso e suas permissoes (IMP-086)."""

    @abstractmethod
    def save(self, perfil: PerfilAcesso) -> None: ...

    @abstractmethod
    def find_by_id(self, perfil_id: uuid.UUID) -> PerfilAcesso | None: ...

    @abstractmethod
    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[PerfilAcesso]: ...

    @abstractmethod
    def find_by_tenant_nome(self, tenant_id: uuid.UUID, nome: str) -> PerfilAcesso | None: ...

    @abstractmethod
    def atribuir_usuario(self, usuario_id: uuid.UUID, perfil_id: uuid.UUID) -> None: ...

    @abstractmethod
    def remover_usuario(self, usuario_id: uuid.UUID) -> None: ...

    @abstractmethod
    def find_by_usuario_id(self, usuario_id: uuid.UUID) -> PerfilAcesso | None: ...

    @abstractmethod
    def exists_with_permission(self, codigo: str) -> bool: ...

    @abstractmethod
    def tenant_has_permission(self, tenant_id: uuid.UUID, codigo: str) -> bool: ...

    @abstractmethod
    def count_usuarios(self, perfil_id: uuid.UUID) -> int: ...
