"""Value Object Documento — identificação civil do Devedor (DOMAIN-022).

O Documento representa o CPF do Devedor (pessoa física, v1). É imutável,
armazenado apenas com dígitos e validado pelo algoritmo dos dígitos
verificadores (VO-022-VAL-001/002).
"""

from __future__ import annotations

from dataclasses import dataclass

from emprestimo.domain.common.errors import DocumentoInvalidoError


@dataclass(frozen=True, slots=True)
class Documento:
    """CPF normalizado e validado do Devedor.

    Atributos:
        valor: CPF canônico com 11 dígitos (ex.: ``52998224725``).

    Invariantes:
        - VO-022-VAL-001: somente dígitos, comprimento exato 11;
        - VO-022-VAL-002: dígitos verificadores corretos;
        - VO-022-VAL-004: imutável (``frozen=True``).
    """

    valor: str

    def __post_init__(self) -> None:
        _validar(self.valor)

    @classmethod
    def from_str(cls, raw: str) -> Documento:
        """Cria um Documento a partir de uma string com ou sem máscara.

        Exemplos:
            >>> Documento.from_str("529.982.247-25")
            Documento(valor='52998224725')
        """
        normalizado = _normalizar(raw)
        return cls(valor=normalizado)

    def __str__(self) -> str:
        return self.valor

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Documento):
            return NotImplemented
        return self.valor == other.valor

    def __hash__(self) -> int:
        return hash(self.valor)


def _normalizar(raw: str) -> str:
    """Remove máscara e caracteres inválidos, mantendo apenas dígitos."""
    return "".join(caractere for caractere in raw if caractere.isdigit())


def _validar(valor: str) -> None:
    """Valida o CPF pelos dígitos verificadores.

    Levanta ``DocumentoInvalidoError`` quando o valor não satisfaz
    VO-022-VAL-001 ou VO-022-VAL-002.
    """
    if len(valor) != 11:
        raise DocumentoInvalidoError(
            valor,
            "CPF deve conter exatamente 11 dígitos",
        )

    if not valor.isdigit():
        raise DocumentoInvalidoError(
            valor,
            "CPF deve conter apenas dígitos",
        )

    if len(set(valor)) == 1:
        raise DocumentoInvalidoError(
            valor,
            "CPF com todos os dígitos iguais é inválido",
        )

    digitos = [int(d) for d in valor]

    primeiro_digito = _calcular_digito_verificador(digitos[:9], pesos_iniciais=10)
    if primeiro_digito != digitos[9]:
        raise DocumentoInvalidoError(
            valor,
            "dígito verificador do CPF está incorreto",
        )

    segundo_digito = _calcular_digito_verificador(digitos[:10], pesos_iniciais=11)
    if segundo_digito != digitos[10]:
        raise DocumentoInvalidoError(
            valor,
            "dígito verificador do CPF está incorreto",
        )


def _calcular_digito_verificador(digitos: list[int], *, pesos_iniciais: int) -> int:
    """Calcula um dígito verificador do CPF pelo algoritmo da Receita Federal.

    Args:
        digitos: dígitos base (9 ou 10 posições).
        pesos_iniciais: peso inicial da multiplicação (10 para 1º dígito,
            11 para o 2º).
    """
    total = sum(
        digito * peso for digito, peso in zip(digitos, range(pesos_iniciais, 1, -1), strict=False)
    )
    resto = total % 11
    return 0 if resto < 2 else 11 - resto
