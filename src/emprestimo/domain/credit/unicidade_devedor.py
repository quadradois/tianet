"""Domain Service UnicidadeDevedorService — garante unicidade do documento na Carteira (DOMAIN-023).

O serviço verifica, antes da criação ou reativação, se já existe Devedor
com o mesmo documento na mesma Carteira — independentemente do estado
(Ativo ou Inativo) — conforme DOMAIN-024 (RN-001, RN-002).
"""

from __future__ import annotations

import uuid

from emprestimo.domain.common.errors import DevedorJaExisteError
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.ports import DevedorUniquenessChecker


class UnicidadeDevedorService:
    """Serviço de domínio para garantir unicidade do documento por Carteira (DOMAIN-023).

    Responsabilidades (DOMAIN-023 §2):
        - verificar se o documento informado já existe na Carteira;
        - impedir a criação de Devedor duplicado (RN-001);
        - garantir a consistência da regra DOMAIN-024;
        - apoiar a reativação, revalidando a unicidade do documento
          na Carteira (qualquer estado — RN-002).

    O serviço não persiste dados; a consulta é delegada ao port
    DevedorUniquenessChecker (IMP-046 / IMP-048).
    """

    def __init__(self, checker: DevedorUniquenessChecker) -> None:
        self._checker = checker

    def verificar_documento_disponivel(self, documento: Documento, carteira_id: uuid.UUID) -> None:
        """Verifica se o documento está disponível na Carteira.

        Levanta ``DevedorJaExisteError`` se já existir Devedor com o mesmo
        documento na mesma Carteira, independentemente do estado (Ativo ou
        Inativo) — DOMAIN-024 RN-001/RN-002.

        Args:
            documento: CPF normalizado do Devedor (DOMAIN-022).
            carteira_id: identificador da Carteira (DOMAIN-001).

        Raises:
            DevedorJaExisteError: documento já cadastrado na Carteira.
        """
        if self._checker.exists_by_documento_carteira(documento, carteira_id):
            raise DevedorJaExisteError(documento.valor, carteira_id)
