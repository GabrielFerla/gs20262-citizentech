"""Métricas da previsão: erro (MAE/RMSE) e, o que importa para a Defesa Civil, a antecedência do alerta.

Antecedência: no momento em que o rio passa da cota, há quantas horas seguidas a
previsão já dizia que ele ia passar? Conta no máximo o horizonte da previsão (6 h): um
aviso dado 10 h antes previa a cota para 4 h antes do cruzamento, ou seja, errou cedo, e
não vale como 10 h de antecedência. A regra simples (persistência: "daqui a 6 h o nível
é igual ao de agora") só "avisa" quando o rio já passou, então a antecedência dela é
sempre 0 h. Alarme falso: a previsão disse que ia passar da cota e o rio não passou
nem nas 6 h seguintes.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

FOLGA_M = 0.10  # mesma folga da regra de alerta da fase 1: só conta um evento novo depois de o rio baixar


def mae(erros: Sequence[float]) -> float | None:
    return sum(abs(e) for e in erros) / len(erros) if erros else None


def rmse(erros: Sequence[float]) -> float | None:
    return math.sqrt(sum(e * e for e in erros) / len(erros)) if erros else None


def erro(previstos: Sequence[float], reais: Sequence[float]) -> dict:
    """MAE e RMSE em metros (só pares com o valor real conhecido)."""
    erros = [p - r for p, r in zip(previstos, reais, strict=True) if r is not None]
    return {"mae_m": _r(mae(erros), 3), "rmse_m": _r(rmse(erros), 3), "exemplos": len(erros)}


def ganho_percentual(modelo: float | None, base: float | None) -> float | None:
    """Quanto o erro caiu em relação à regra simples (positivo = melhor)."""
    if modelo is None or not base:
        return None
    return round(100 * (1 - modelo / base), 1)


def alarmes(atuais: Sequence[float], previstos: Sequence[float], cota: float, horizonte_h: int = 6) -> dict:
    """Antecedência e alarmes falsos numa série horária contínua.

    atuais[k]    = nível observado na hora k
    previstos[k] = nível previsto, na hora k, para a hora k + horizonte
    """
    if len(atuais) != len(previstos):
        raise ValueError("séries de tamanhos diferentes")
    ligado = [p >= cota for p in previstos]
    cruzamentos = cruzamentos_da_cota(atuais, cota)

    antecedencias = []
    for k in cruzamentos:
        j = k - 1
        while j >= 0 and ligado[j] and k - j <= horizonte_h and atuais[j] < cota:
            j -= 1
        antecedencias.append(k - 1 - j)

    falsos = 0
    k = 0
    while k < len(ligado):
        if not ligado[k] or atuais[k] >= cota:
            k += 1
            continue
        inicio = k
        while k < len(ligado) and ligado[k] and atuais[k] < cota:
            k += 1
        fim = k - 1
        if not any(a >= cota for a in atuais[inicio : fim + 2 + horizonte_h]):
            falsos += 1  # o rio não chegou à cota nem nas horas seguintes ao aviso

    antecipados = [a for a in antecedencias if a > 0]
    return {
        "cota_m": cota,
        "eventos": len(cruzamentos),
        "antecipados": len(antecipados),
        "antecedencia_media_h": _r(sum(antecedencias) / len(antecedencias), 1) if antecedencias else None,
        "antecedencias_h": antecedencias,
        "alarmes_falsos": falsos,
    }


def cruzamentos_da_cota(atuais: Sequence[float], cota: float) -> list[int]:
    """Horas em que o rio passou da cota (de baixo para cima), com a folga contra o "pisca-pisca"."""
    cruzamentos, armado = [], True
    for k in range(1, len(atuais)):
        if armado and atuais[k] >= cota > atuais[k - 1]:
            cruzamentos.append(k)
            armado = False
        elif atuais[k] < cota - FOLGA_M:
            armado = True
    return cruzamentos


def _r(valor: float | None, casas: int) -> float | None:
    return None if valor is None else round(valor, casas)
