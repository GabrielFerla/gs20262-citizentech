"""Mensagens de alerta em linguagem simples ("IA simulada" com modelos de texto).

Segue o mesmo contrato que um LLM teria (veja area1-ia/prompts/sistema.md):

    fatos (JSON) ──► 1. intenção ──► 2. texto por canal ──► 3. verificação ──► mensagens

1. Intenção, pela situação mais grave entre agora e a prevista para 6 h:
   1 atenção = "Fique atento", 2 alerta = "Prepare-se para sair", 3 inundação = "Saia agora".
   Se a previsão é pior que o agora, a mensagem é ANTECIPADA ("deve ... nas próximas 6 horas").
2. Um texto por canal: SMS (160 caracteres sem acento), push (título + corpo), WhatsApp e
   um resumo técnico para a Defesa Civil.
3. A verificação confere as regras de linguagem simples (tamanho, frases curtas, sem
   jargão, ação logo no começo, telefone e abrigo quando é para sair). Os testes rodam a
   verificação em todas as combinações; trocar este gerador por um LLM manteria a etapa 3.

    python -m ia.mensagens      # imprime exemplos (usados em prompts/exemplos.md)
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass

HORIZONTE_H = 6
TAMANHO_MINIMO_NOME = 8  # o nome do abrigo encurtado no SMS nunca fica menor que isso (+ "...")
LIMITES = {"sms": 160, "push_titulo": 50, "push_corpo": 178, "whatsapp": 700, "defesa_civil": 700}
MAX_PALAVRAS_POR_FRASE = 20
# Comparados sem acento, no começo de palavra, e fora dos nomes próprios (rio, estação, bairro, abrigo).
JARGAO = ("cota", "persistencia", "modelo", "algoritmo", "severidade", "probabilidade", "hidrologic",
          "random forest", "regressao")
ACOES = ("Saia agora", "Prepare-se", "Fique atento", "Não volte", "Nao volte")
CANAIS_CIDADAO = ("sms", "push_titulo", "push_corpo", "whatsapp")
NOMES_SITUACAO = {0: "normal", 1: "atenção", 2: "alerta", 3: "inundação"}


@dataclass(frozen=True)
class AbrigoMensagem:
    nome: str
    minutos_a_pe: int | None = None
    vagas: int | None = None


@dataclass(frozen=True)
class Fatos:
    """O que a mensagem precisa saber. Tudo vem da previsão e da recomendação."""

    estacao: str  # "Guaíba - Cais Mauá"
    corpo_hidrico: str  # "Lago Guaíba"
    nivel_atual_m: float
    nivel_previsto_m: float
    severidade_atual: int  # 0 normal, 1 atenção, 2 alerta, 3 inundação
    severidade_prevista: int
    cota_m: float | None = None  # cota da situação mais grave (só no texto da Defesa Civil)
    bairro: str | None = None
    abrigo: AbrigoMensagem | None = None
    erro_modelo_m: float | None = None  # erro médio no teste (Defesa Civil)
    erro_regra_simples_m: float | None = None

    @property
    def nivel(self) -> int:
        return max(self.severidade_atual, self.severidade_prevista)

    @property
    def antecipado(self) -> bool:
        return self.severidade_prevista > self.severidade_atual

    @property
    def baixando(self) -> bool:
        return self.severidade_prevista < self.severidade_atual


@dataclass(frozen=True)
class Mensagens:
    intencao: str
    sms: str | None
    push_titulo: str | None
    push_corpo: str | None
    whatsapp: str | None
    defesa_civil: str
    verificacao: dict[str, list[str]]  # canal → problemas encontrados (vazio = passou)

    def para_dict(self) -> dict:
        return asdict(self)


# ----------------------------------------------------------------------------- partes do texto
def _rio(f: Fatos) -> str:
    return f"O {f.corpo_hidrico}"


def _onde(f: Fatos) -> str:
    return f" no bairro {f.bairro}" if f.bairro else ""


def _intencao(f: Fatos) -> str:
    if f.nivel == 0:
        return "sem_alerta"
    if f.baixando:  # só quem saiu de casa (inundação) recebe "não volte"
        return "nao_volte" if f.severidade_atual == 3 else "fique_atento"
    return {1: "fique_atento", 2: "prepare_se", 3: "saia_agora"}[f.nivel]


def _acao(intencao: str) -> str:
    return {
        "saia_agora": "Saia agora para um lugar alto.",
        "prepare_se": "Prepare-se para sair de casa.",
        "fique_atento": "Fique atento.",
        "nao_volte": "Não volte para casa ainda.",
    }[intencao]


def _situacao(f: Fatos, curta: bool = False) -> str:
    rio, onde = _rio(f), "" if curta else _onde(f)
    prazo = f"em até {HORIZONTE_H} h" if curta else f"nas próximas {HORIZONTE_H} horas"
    if f.baixando:
        return {
            3: f"{rio} começou a baixar, mas as ruas{onde} ainda são perigosas.",
            2: f"{rio} começou a baixar, mas ainda está alto{onde}.",
            1: f"{rio} está baixando e voltando ao normal{onde}.",
        }[f.severidade_atual]
    if f.nivel == 3:
        return f"{rio} deve alagar ruas{onde} {prazo}." if f.antecipado else f"{rio} está alagando ruas{onde}."
    if f.nivel == 2:
        return f"{rio} deve subir muito{onde} {prazo}." if f.antecipado else f"{rio} está muito alto{onde}."
    return f"{rio} deve subir{onde} {prazo}." if f.antecipado else f"{rio} está acima do normal{onde}."


def _abrigo(f: Fatos, curto: bool = False) -> str | None:
    if f.nivel < 2 or f.baixando:
        return None
    if f.abrigo is None:
        return "Procure o abrigo mais perto no app."
    a = f.abrigo
    if curto:  # SMS e push: uma frase só
        return f"Vá para {a.nome}" + (f" ({a.minutos_a_pe} min a pé)." if a.minutos_a_pe is not None else ".")
    detalhes = [x for x in (f"fica a {a.minutos_a_pe} min a pé" if a.minutos_a_pe is not None else None,
                            f"tem {a.vagas} vagas" if a.vagas is not None else None) if x]
    return f"Vá para {a.nome}." + (f" {' e '.join(detalhes).capitalize()}." if detalhes else "")


def _cuidados(f: Fatos) -> str:
    if f.baixando:
        return {
            3: "Espere a Defesa Civil liberar a volta.",
            2: "Mantenha documentos e remédios à mão.",
            1: "Evite as margens até o rio voltar ao normal.",
        }[f.severidade_atual]
    return {
        3: "Não atravesse ruas alagadas.",
        2: "Separe documentos, remédios e água.",
        1: "Evite as margens e acompanhe os avisos.",
    }[f.nivel]


def _emergencia(f: Fatos, curta: bool = False) -> str | None:
    if f.nivel < 2:
        return None
    return "Emergência: 199 ou 193." if curta else "Emergência: 199 (Defesa Civil) ou 193 (Bombeiros)."


def _titulo(f: Fatos, intencao: str) -> str:
    return {
        "saia_agora": "Saia agora: risco de alagamento",
        "prepare_se": "Prepare-se: o rio vai subir" if f.antecipado else "Alerta de cheia: prepare-se",
        "fique_atento": (
            "Rio baixando: fique atento" if f.baixando
            else "Atenção: o rio vai subir" if f.antecipado
            else "Atenção: rio acima do normal"
        ),
        "nao_volte": "Rio baixando: ainda não volte",
    }[intencao]


def sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


def _montar(f: Fatos, obrigatorias: list[str], opcionais: list[str], limite: int, ascii_: bool = False) -> str:
    """Junta as partes obrigatórias e acrescenta as opcionais, na ordem, enquanto couber.

    Se nem as obrigatórias couberem, encurta o nome do abrigo (o resto não pode sair:
    ação, situação, abrigo e telefone de emergência).
    """
    ajustar = sem_acento if ascii_ else (lambda s: s)
    partes = [ajustar(p) for p in obrigatorias]
    texto = " ".join(partes)
    if len(texto) > limite and f.abrigo is not None:
        nome = ajustar(f.abrigo.nome)
        curto = nome[: max(len(nome) - (len(texto) - limite) - 3, TAMANHO_MINIMO_NOME)].rstrip() + "..."
        partes = [p.replace(nome, curto) for p in partes]
        texto = " ".join(partes)
    for parte in opcionais:
        parte = ajustar(parte)
        if len(texto) + 1 + len(parte) <= limite:
            texto = f"{texto} {parte}"
    return texto


def _partes_curtas(f: Fatos, intencao: str) -> list[str]:
    partes = [_acao(intencao), _situacao(f, curta=True), _abrigo(f, curto=True), _emergencia(f, curta=True)]
    return [p for p in partes if p]


def _sms(f: Fatos, intencao: str) -> str:
    return _montar(f, ["DEFESA CIVIL:", *_partes_curtas(f, intencao)], [_cuidados(f)], LIMITES["sms"], ascii_=True)


def _push_corpo(f: Fatos, intencao: str) -> str:
    return _montar(f, _partes_curtas(f, intencao), [_cuidados(f)], LIMITES["push_corpo"])


def _whatsapp(f: Fatos, intencao: str) -> str:
    linhas = ["*Defesa Civil de Porto Alegre*", "", f"*{_acao(intencao)}*", _situacao(f), ""]
    abrigo = _abrigo(f)
    if abrigo:
        linhas.append(abrigo)
    linhas.append(_cuidados(f))
    emergencia = _emergencia(f)
    if emergencia:
        linhas.append(emergencia)
    return "\n".join(linhas)


def _numero(valor: float | None, casas: int = 2) -> str:
    return "?" if valor is None else f"{valor:.{casas}f}".replace(".", ",")


def _defesa_civil(f: Fatos) -> str:
    if f.nivel == 0:
        rotulo = "NORMAL"
    elif f.baixando:
        rotulo = "RIO BAIXANDO"
    else:
        rotulo = "ALERTA ANTECIPADO" if f.antecipado else "ALERTA EM CURSO"
    variacao = f.nivel_previsto_m - f.nivel_atual_m
    partes = [
        f"[{rotulo}] {f.estacao}: {_numero(f.nivel_atual_m)} m agora ({NOMES_SITUACAO[f.severidade_atual]}).",
        f"Previsão para {HORIZONTE_H} h: {_numero(f.nivel_previsto_m)} m ({NOMES_SITUACAO[f.severidade_prevista]}"
        + (f"; cota {_numero(f.cota_m)} m" if f.cota_m is not None else "")
        + f"), variação {'+' if variacao >= 0 else '−'}{_numero(abs(variacao))} m.",
    ]
    if f.erro_modelo_m is not None and f.erro_regra_simples_m is not None:
        partes.append(
            f"Erro médio da IA no teste: {_numero(f.erro_modelo_m, 3)} m (regra simples: {_numero(f.erro_regra_simples_m, 3)} m)."
        )
    if f.nivel >= 2 and not f.baixando:
        partes.append("Evitar abrigos em área de risco ligados a esta estação.")
    if f.abrigo is not None and f.bairro:
        partes.append(f"Abrigo sugerido para {f.bairro}: {f.abrigo.nome}.")
    return " ".join(partes)


# ----------------------------------------------------------------------------- verificação
def _frases(texto: str) -> list[str]:
    limpo = texto.replace("*", "")
    return [s.strip() for s in re.split(r"[.!?\n]+", limpo) if s.strip()]


def _sem_nomes_proprios(texto: str, fatos: Fatos) -> str:
    """Texto sem acento, minúsculo e sem os nomes vindos dos fatos ("Escola Modelo" não é jargão)."""
    limpo = sem_acento(texto).lower()
    nomes = [fatos.estacao, fatos.corpo_hidrico, fatos.bairro, fatos.abrigo.nome if fatos.abrigo else None]
    for nome in filter(None, nomes):
        nome = sem_acento(nome).lower()
        limpo = limpo.replace(nome, " ")
        # nome do abrigo encurtado no SMS ("escola modelo de po...")
        limpo = re.sub(re.escape(nome[:TAMANHO_MINIMO_NOME]) + r"[^.(]*\.\.\.", " ", limpo)
    return limpo


def verificar(canal: str, texto: str, fatos: Fatos) -> list[str]:
    """Regras de linguagem simples. Devolve a lista de problemas (vazia = passou)."""
    problemas = []
    limite = LIMITES[canal]
    if len(texto) > limite:
        problemas.append(f"tem {len(texto)} caracteres (máximo {limite})")
    if canal == "defesa_civil":
        return problemas
    if canal == "sms" and not texto.isascii():
        problemas.append("SMS com acento ou símbolo fora do padrão GSM")
    sem_nomes = _sem_nomes_proprios(texto, fatos)
    for termo in JARGAO:
        if re.search(rf"\b{re.escape(termo)}", sem_nomes):
            problemas.append(f"usa jargão: '{termo}'")
    for frase in _frases(texto):
        if len(frase.split()) > MAX_PALAVRAS_POR_FRASE:
            problemas.append(f"frase longa ({len(frase.split())} palavras): '{frase[:40]}…'")
    if canal != "push_titulo":
        inicio = texto.replace("DEFESA CIVIL:", "").replace("*Defesa Civil de Porto Alegre*", "").replace("*", "").strip()
        if not inicio.startswith(ACOES):
            problemas.append("não começa pela ação (o que a pessoa deve fazer)")
        if fatos.nivel >= 2 and not fatos.baixando:
            if "199" not in texto:
                problemas.append("falta o telefone de emergência (199)")
            if fatos.abrigo is not None and sem_acento(fatos.abrigo.nome)[:8].lower() not in sem_acento(texto).lower():
                problemas.append("falta o abrigo recomendado")
    return problemas


# ----------------------------------------------------------------------------- geração
def gerar(fatos: Fatos) -> Mensagens:
    intencao = _intencao(fatos)
    if intencao == "sem_alerta":
        textos = dict.fromkeys(CANAIS_CIDADAO)
    else:
        textos = {
            "sms": _sms(fatos, intencao),
            "push_titulo": _titulo(fatos, intencao),
            "push_corpo": _push_corpo(fatos, intencao),
            "whatsapp": _whatsapp(fatos, intencao),
        }
    textos["defesa_civil"] = _defesa_civil(fatos)
    verificacao = {canal: verificar(canal, texto, fatos) for canal, texto in textos.items() if texto is not None}
    return Mensagens(intencao=intencao, verificacao=verificacao, **textos)


EXEMPLOS = {
    "Guaíba vai passar da cota de inundação (aviso antecipado, com abrigo)": Fatos(
        estacao="Guaíba - Cais Mauá", corpo_hidrico="Lago Guaíba", nivel_atual_m=2.62, nivel_previsto_m=3.08,
        severidade_atual=2, severidade_prevista=3, cota_m=3.0, bairro="Navegantes",
        abrigo=AbrigoMensagem("Colégio Dom João Becker", minutos_a_pe=34, vagas=96),
        erro_modelo_m=0.022, erro_regra_simples_m=0.075,
    ),
    "Gravataí deve entrar em alerta (aviso antecipado, sem bairro)": Fatos(
        estacao="Rio Gravataí - Sarandi", corpo_hidrico="Rio Gravataí", nivel_atual_m=3.21, nivel_previsto_m=3.55,
        severidade_atual=1, severidade_prevista=2, cota_m=3.5,
    ),
    "Dilúvio acima do normal (atenção)": Fatos(
        estacao="Arroio Dilúvio - Av. Ipiranga", corpo_hidrico="Arroio Dilúvio", nivel_atual_m=1.92,
        nivel_previsto_m=1.95, severidade_atual=1, severidade_prevista=1, cota_m=1.8,
    ),
    "Guaíba baixando depois da cheia": Fatos(
        estacao="Guaíba - Cais Mauá", corpo_hidrico="Lago Guaíba", nivel_atual_m=3.05, nivel_previsto_m=2.88,
        severidade_atual=3, severidade_prevista=2, cota_m=3.0, bairro="Centro Histórico",
    ),
}


def main() -> None:
    for titulo, fatos in EXEMPLOS.items():
        print(f"## {titulo}\n\nEntrada:\n```json\n{json.dumps(asdict(fatos), ensure_ascii=False, indent=2)}\n```\n")
        print(f"Saída:\n```json\n{json.dumps(gerar(fatos).para_dict(), ensure_ascii=False, indent=2)}\n```\n")


if __name__ == "__main__":
    main()
