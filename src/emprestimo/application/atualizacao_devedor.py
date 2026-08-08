"""DevedorAtualizacaoService — orquestrador da atualização parcial de Devedor (IMP-054).

Fluxo:
1. Buscar Devedor existente por ID;
2. Validar unicidade do documento (se alterado — documento é imutável, então não altera);
3. Aplicar alterações no Aggregate: nome (atualizar_nome) e contatos
   (adicionar_contato, atualizar_contato, remover_contato);
4. Registrar trilha de auditoria (ADR-002) com evento DevedorAtualizado;
5. Persistir via Unit of Work em transação única (AD-001);
6. Idempotência (AD-002): Idempotency-Key registrada na mesma transação;
   replay com a mesma chave retorna exatamente o mesmo resultado.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from emprestimo.application.errors import IdempotenciaConflitoError
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.devedor import Devedor, DevedorState
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.unicidade_devedor import UnicidadeDevedorService
from emprestimo.domain.credit.eventos_devedor import DevedorAtualizado

ESCOPO_IDEMPOTENCIA = "devedor-atualizacao"
"""Escopo da Idempotency-Key: isola chaves por caso de uso (AD-002)."""


@dataclass(frozen=True)
class DevedorAtualizadoResultado:
    """Resultado da atualização de Devedor — estado final (IMP-054).

    Dados suficientes para a confirmação na API: identidade, documento,
    nome, contatos, estado final e timestamp de atualização.
    """

    devedor_id: uuid.UUID
    carteira_id: uuid.UUID
    documento: str
    nome: str
    contatos: tuple[dict[str, object], ...]
    estado: DevedorState
    atualizado_em: datetime


def _solicitacao_hash(
    devedor_id: uuid.UUID,
    nome: str | None = None,
    contatos: list[dict[str, object]] | None = None,
) -> str:
    """Fingerprint do payload — detecta chave reenviada com resultado divergente."""
    partes = [str(devedor_id)]
    if nome is not None:
        partes.append(nome.strip())
    if contatos is not None:
        # Ordena para consistência
        contatos_ordenados = sorted(
            [(c["tipo"], c["valor"], str(c.get("preferencial", "false")).lower()) for c in contatos]
        )
        partes.append("|".join(f"{t}:{v}:{p}" for t, v, p in contatos_ordenados))
    bruto = "|".join(partes)
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def _contatos_para_dict(contatos: tuple[Contato, ...]) -> tuple[dict[str, object], ...]:
    return tuple(
        {"tipo": c.tipo.value, "valor": c.valor, "preferencial": c.preferencial} for c in contatos
    )


class DevedorAtualizacaoService:
    """Orquestra a atualização parcial de um Devedor (US-021..US-026)."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        unicidade: UnicidadeDevedorService,
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._unicidade = unicidade
        self._auditoria = auditoria

    def atualizar(
        self,
        devedor_id: uuid.UUID,
        idempotency_key: str,
        *,
        nome: str | None = None,
        contatos: list[dict[str, object]] | None = None,
    ) -> DevedorAtualizadoResultado:
        """Executa a atualização parcial do Devedor em transação única.

        Args:
            devedor_id: UUID do Devedor a ser atualizado.
            idempotency_key: Chave de idempotência obrigatória (AD-002).
            nome: Novo nome do Devedor (opcional).
            contatos: Lista completa de contatos para substituir os atuais (opcional).
                      Cada item: {"tipo": "telefone|email|whatsapp", "valor": "...", "preferencial": bool}.
                      Se fornecido, substitui TODOS os contatos existentes.

        Returns:
            DevedorAtualizado com o estado final do Devedor.

        Raises:
            DevedorNaoEncontradoError: Se Devedor não existir.
            ViolacaoInvarianteError: Se violar regras de domínio (ex: RN-003, RN-005, DOMAIN-021).
            IdempotenciaConflitoError: Se chave reutilizada com payload divergente.
        """
        hash_solicitacao = _solicitacao_hash(devedor_id, nome, contatos)

        self._auditoria.registrar(
            "devedor",
            devedor_id,
            "atualizar.inicio",
            "iniciado",
            detalhes=json.dumps({"idempotency_key": idempotency_key}),
        )
        try:
            with self._uow_factory() as uow:
                resultado = self._replay_ou_registrar_chave(uow, idempotency_key, hash_solicitacao)
                if resultado is not None:
                    uow.commit()
                    return resultado

                # 1. Buscar Devedor existente
                devedor = uow.devedor.find_by_id(devedor_id)
                if devedor is None:
                    from emprestimo.application.errors import DevedorNaoEncontradoError

                    raise DevedorNaoEncontradoError(devedor_id)

                # 2. Capturar estado anterior para evento de auditoria
                nome_anterior = devedor.nome
                contatos_anteriores = devedor.contatos

                # 3. Aplicar alterações de nome (se fornecido)
                if nome is not None:
                    devedor.atualizar_nome(nome.strip())

                # 4. Aplicar alterações de contatos (se fornecido — substituição completa)
                if contatos is not None:
                    if not contatos:
                        from emprestimo.domain.common.errors import ViolacaoInvarianteError

                        raise ViolacaoInvarianteError(
                            "RN-003", "Devedor deve ter pelo menos um contato"
                        )

                    # Remove todos os contatos atuais e adiciona os novos
                    # Para isso, criamos novos contatos com o devedor_id correto
                    novos_contatos = []
                    for c in contatos:
                        tipo_str = c["tipo"].strip().lower()
                        tipo = TipoContato(tipo_str)
                        valor = c["valor"].strip()
                        preferencial = bool(c.get("preferencial", False))
                        novos_contatos.append(
                            Contato(
                                devedor_id=devedor.id,
                                tipo=tipo,
                                valor=valor,
                                preferencial=preferencial,
                            )
                        )
                    # Remove todos os atuais
                    for contato in list(devedor.contatos):
                        devedor.remover_contato(contato.id)
                    # Adiciona os novos
                    for contato in novos_contatos:
                        devedor.adicionar_contato(contato)

                # 4. Trilha de auditoria — aggregate atualizado
                self._auditoria.registrar(
                    "devedor",
                    devedor.id,
                    "atualizar.aggregate_atualizado",
                    "ok",
                    detalhes=json.dumps(
                        {
                            "devedor_id": str(devedor.id),
                            "carteira_id": str(devedor.carteira_id),
                            "idempotency_key": idempotency_key,
                        }
                    ),
                )

                # 5. Persistir via UoW (mesma transação)
                uow.devedor.save(devedor)

                # Não há relationship entre DevedorORM e ContatoORM: a coleção do
                # Aggregate precisa ser reconciliada explicitamente com o banco.
                # Sem apagar os que saíram, a linha antiga sobrevive e reaparece
                # na leitura — o estado persistido divergiria do Aggregate.
                ids_atuais = {c.id for c in devedor.contatos}
                for persistido in uow.contato.find_by_devedor(devedor.id):
                    if persistido.id not in ids_atuais:
                        uow.contato.remove(persistido.id)
                for contato in devedor.contatos:
                    uow.contato.save(contato)

                # 6. Evento de domínio para auditoria (ADR-002)
                carteira = uow.carteira.find_by_id(devedor.carteira_id)
                tenant_id = carteira.tenant_id if carteira else uuid.UUID(int=0)
                evento = DevedorAtualizado.from_devedor(
                    devedor,
                    tenant_id,
                    nome_anterior=nome_anterior,
                    contatos_anteriores=contatos_anteriores,
                )
                self._auditoria.registrar(
                    "devedor",
                    devedor.id,
                    "atualizar.evento_atualizado",
                    "ok",
                    detalhes=json.dumps(evento.to_audit_dict()),
                )

                resultado = DevedorAtualizadoResultado(
                    devedor_id=devedor.id,
                    carteira_id=devedor.carteira_id,
                    documento=devedor.documento.valor,
                    nome=devedor.nome,
                    contatos=_contatos_para_dict(devedor.contatos),
                    estado=devedor.estado,
                    atualizado_em=devedor.atualizado_em or datetime.now(),
                )
                uow.idempotencia.concluir(
                    idempotency_key, ESCOPO_IDEMPOTENCIA, _serializar_resultado(resultado)
                )
                uow.commit()

            self._auditoria.registrar(
                "devedor",
                resultado.devedor_id,
                "atualizar.sucesso",
                "ok",
                detalhes=json.dumps(
                    {"estado": resultado.estado.value, "idempotency_key": idempotency_key}
                ),
            )
            return resultado
        except Exception as exc:
            self._auditoria.registrar(
                "devedor",
                devedor_id,
                "atualizar.falha",
                "falhou",
                detalhes=f"{type(exc).__name__}: {exc}",
            )
            self._auditoria.registrar(
                "devedor", devedor_id, "atualizar.rollback", "rollback_aplicado"
            )
            raise

    def _replay_ou_registrar_chave(
        self, uow: UnitOfWork, idempotency_key: str, hash_solicitacao: str
    ) -> DevedorAtualizadoResultado | None:
        """Replay seguro (AD-002): mesma chave → mesmo resultado; divergente → conflito."""
        existente = uow.idempotencia.find_by_chave(idempotency_key, ESCOPO_IDEMPOTENCIA)
        if existente is None:
            uow.idempotencia.registrar(idempotency_key, ESCOPO_IDEMPOTENCIA, hash_solicitacao)
            return None
        # Verifica estado ANTES do hash: se em andamento, bloqueia independentemente do hash
        if existente["estado"] != "finished":
            raise IdempotenciaConflitoError(idempotency_key, "atualização em andamento")
        if existente["solicitacao_hash"] != hash_solicitacao:
            raise IdempotenciaConflitoError(idempotency_key, "resultado divergente")
        self._auditoria.registrar(
            "devedor",
            None,
            "atualizar.replay",
            "ok",
            detalhes=json.dumps({"idempotency_key": idempotency_key}),
        )
        return _desserializar_resultado(existente["resultado"])


def _serializar_resultado(resultado: DevedorAtualizadoResultado) -> str:
    return json.dumps(
        {
            "devedor_id": str(resultado.devedor_id),
            "carteira_id": str(resultado.carteira_id),
            "documento": resultado.documento,
            "nome": resultado.nome,
            "contatos": list(resultado.contatos),
            "estado": resultado.estado.value,
            "atualizado_em": resultado.atualizado_em.isoformat(),
        }
    )


def _desserializar_resultado(conteudo: str | None) -> DevedorAtualizadoResultado:
    if not conteudo:
        raise IdempotenciaConflitoError("?", "resultado ausente no registro")
    dados = json.loads(conteudo)
    return DevedorAtualizadoResultado(
        devedor_id=uuid.UUID(dados["devedor_id"]),
        carteira_id=uuid.UUID(dados["carteira_id"]),
        documento=dados["documento"],
        nome=dados["nome"],
        contatos=tuple(dados["contatos"]),
        estado=DevedorState(dados["estado"]),
        atualizado_em=datetime.fromisoformat(dados["atualizado_em"]),
    )
