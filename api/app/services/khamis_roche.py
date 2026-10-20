"""Estatura adulta prevista — método de Khamis-Roche (rapazes).

Khamis HJ, Roche AF. Predicting adult stature without using skeletal age:
the Khamis-Roche method. Pediatrics 1994;94(4):504–507; errata em
Pediatrics 1995;95(3):457.

    EA (polegadas) = β0 + β1 × altura (pol.) + β2 × peso (lb) + β3 × média dos pais (pol.)

com os coeficientes da idade arredondada à meia-idade mais próxima (4,0–17,5).
A tabela abaixo é a corrigida pela errata (coluna do peso). Atenção: há
reproduções — por exemplo o pacote R matuR — com a coluna do peso 10× menor,
i.e. anterior à errata; com esses valores a previsão sobe vários centímetros.

Percentagem da estatura adulta prevista → estado maturacional, segundo
Cumming et al. (2017), Strength Cond J 39(2):34–47 (bio-banding):
  < 85 %  pré-púbere · 85–90 % início da puberdade · 90–95 % meio · ≥ 95 % fim.
"""
from __future__ import annotations

# idade: (β0 intercepto, β1 altura, β2 peso, β3 média dos pais) — rapazes, unidades imperiais.
COEF_RAPAZES: dict[float, tuple[float, float, float, float]] = {
    4.0: (-10.2567, 1.23812, -0.087235, 0.50286),
    4.5: (-10.7190, 1.15964, -0.074454, 0.52887),
    5.0: (-11.0213, 1.10674, -0.064778, 0.53919),
    5.5: (-11.1556, 1.07480, -0.057760, 0.53691),
    6.0: (-11.1138, 1.05923, -0.052947, 0.52513),
    6.5: (-11.0221, 1.05542, -0.049892, 0.50692),
    7.0: (-10.9984, 1.05877, -0.048144, 0.48538),
    7.5: (-11.0214, 1.06467, -0.047256, 0.46361),
    8.0: (-11.0696, 1.06853, -0.046778, 0.44469),
    8.5: (-11.1220, 1.06572, -0.046261, 0.43171),
    9.0: (-11.1571, 1.05166, -0.045254, 0.42776),
    9.5: (-11.1405, 1.02174, -0.043311, 0.43593),
    10.0: (-11.0380, 0.97135, -0.039981, 0.45932),
    10.5: (-10.8286, 0.89589, -0.034814, 0.50101),
    11.0: (-10.4917, 0.81239, -0.029050, 0.54781),
    11.5: (-10.0065, 0.74134, -0.024167, 0.58409),
    12.0: (-9.3522, 0.68325, -0.020076, 0.60927),
    12.5: (-8.6055, 0.63869, -0.016681, 0.62279),
    13.0: (-7.8632, 0.60818, -0.013895, 0.62407),
    13.5: (-7.1348, 0.59228, -0.011624, 0.61253),
    14.0: (-6.4299, 0.59151, -0.009776, 0.58762),
    14.5: (-5.7578, 0.60643, -0.008261, 0.54875),
    15.0: (-5.1282, 0.63757, -0.006988, 0.49536),
    15.5: (-4.5092, 0.68548, -0.005863, 0.42687),
    16.0: (-3.9292, 0.75069, -0.004795, 0.34271),
    16.5: (-3.4873, 0.83375, -0.003695, 0.24231),
    17.0: (-3.2830, 0.93520, -0.002470, 0.12510),
    17.5: (-3.4156, 1.05558, -0.001027, -0.00950),
}

CM_POR_POL = 2.54
LB_POR_KG = 2.20462


def idade_tabela(idade_anos: float) -> float | None:
    """Idade arredondada à meia-idade mais próxima, dentro de 4,0–17,5."""
    a = round(idade_anos * 2) / 2
    return a if a in COEF_RAPAZES else None


def categoria_cumming(pct: float) -> str:
    if pct < 85:
        return "Pré-púbere"
    if pct < 90:
        return "Início da puberdade"
    if pct < 95:
        return "Meio da puberdade"
    return "Fim da puberdade"


def estatura_adulta_prevista(idade_anos: float, altura_cm: float, peso_kg: float,
                             altura_pai_cm: float, altura_mae_cm: float) -> dict | None:
    """Devolve a estatura adulta prevista e o estado maturacional, ou None se
    faltar algum dado ou a idade estiver fora de 4,0–17,5 anos."""
    if None in (idade_anos, altura_cm, peso_kg, altura_pai_cm, altura_mae_cm):
        return None
    a = idade_tabela(idade_anos)
    if a is None:
        return None
    b0, b1, b2, b3 = COEF_RAPAZES[a]
    media_pais_pol = (altura_pai_cm + altura_mae_cm) / 2 / CM_POR_POL
    prevista_pol = b0 + b1 * (altura_cm / CM_POR_POL) + b2 * (peso_kg * LB_POR_KG) + b3 * media_pais_pol
    prevista_cm = prevista_pol * CM_POR_POL
    pct = altura_cm / prevista_cm * 100
    return {
        "estatura_prevista_cm": round(prevista_cm, 1),
        "pct_estatura_adulta": round(pct, 1),
        "crescimento_restante_cm": round(max(0.0, prevista_cm - altura_cm), 1),
        "categoria": categoria_cumming(pct),
        "idade_tabela": a,
    }
