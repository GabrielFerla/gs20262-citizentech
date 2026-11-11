"""Gera as bases de bairros, abrigos e sensores a partir do OpenStreetMap.

Roda uma vez (precisa de internet) e o resultado (CSV) fica versionado no git,
para que o projeto rode sem internet. Usa só a biblioteca padrão do Python.

    python area2-bigdata/db/seeds/gerar_seeds_osm.py
    python area2-bigdata/db/seeds/gerar_seeds_osm.py --cache /tmp/osm   # reaproveita downloads

Dados © colaboradores do OpenStreetMap, licença ODbL (https://www.openstreetmap.org/copyright).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

PASTA = Path(__file__).resolve().parent
OVERPASS = "https://overpass-api.de/api/interpreter"
AREA = 'area["name"="Porto Alegre"]["admin_level"="8"]->.a;'

CONSULTAS = {
    "locais.json": AREA
    + '(nwr(area.a)["amenity"="school"]["name"]; nwr(area.a)["leisure"="sports_centre"]["name"];);'
    + "out center tags;",
    "bairros_geom.json": AREA
    + 'rel(area.a)["boundary"="administrative"]["admin_level"="10"]; out geom;',
    "bairros_pontos.json": AREA
    + 'node(area.a)["place"~"^(suburb|neighbourhood|quarter)$"]["name"]; out tags center;',
}

# Bairros atingidos pela enchente de maio/2024 (simplificação usada na simulação;
# conferir com o mapa oficial de inundação antes de citar no pitch).
BAIRROS_RISCO = {
    "Arquipélago", "Centro Histórico", "Navegantes", "Humaitá", "Sarandi", "Farrapos",
    "São Geraldo", "Anchieta", "Cidade Baixa", "Menino Deus", "Praia de Belas",
}

# Um abrigo por bairro, nesta ordem. Os de área de risco existem para mostrar que
# a recomendação os evita quando o rio da região está em alerta.
BAIRROS_ABRIGO_RISCO = ["Sarandi", "Humaitá", "Navegantes", "Menino Deus", "Cidade Baixa", "Centro Histórico"]
BAIRROS_ABRIGO_SEGURO = [
    "Petrópolis", "Partenon", "Santana", "Bela Vista", "Rio Branco", "Jardim Botânico",
    "Bom Jesus", "Teresópolis", "Glória", "Santa Tereza", "Medianeira", "Passo da Areia",
    "Jardim Lindóia", "Cristo Redentor",
]
TOTAL_ABRIGOS = 20
CAPACIDADE = {"ginasio": 300, "escola": 150}  # estimativa: o OSM não informa capacidade

PUBLICA = re.compile(
    r"\b(escola (estadual|municipal)|emef|emei|eeef|eeem|e\.\s?e\.|col[eé]gio estadual|instituto estadual)",
    re.IGNORECASE,
)
GINASIO = re.compile(r"\b(gin[aá]sio|centro esportivo|centro de esportes)", re.IGNORECASE)
INFANTIL = re.compile(r"\b(educa[cç][aã]o infantil|emei)\b", re.IGNORECASE)


def slug(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")


def baixar(nome: str, cache: Path) -> dict:
    arquivo = cache / nome
    if arquivo.exists():
        return json.loads(arquivo.read_text(encoding="utf-8"))
    consulta = "[out:json][timeout:180];" + CONSULTAS[nome]
    dados = urllib.parse.urlencode({"data": consulta}).encode()
    req = urllib.request.Request(OVERPASS, data=dados, headers={"User-Agent": "gs-citizentech/0.1 (projeto academico)"})
    for tentativa in range(3):
        try:
            with urllib.request.urlopen(req, timeout=200) as resp:
                conteudo = resp.read()
            break
        except OSError:
            if tentativa == 2:
                raise
            time.sleep(10 * (tentativa + 1))
    cache.mkdir(parents=True, exist_ok=True)
    arquivo.write_bytes(conteudo)
    return json.loads(conteudo)


def segmentos_do_bairro(relacao: dict) -> list[tuple[float, float, float, float]]:
    """Todos os segmentos (lon, lat) das vias externas e internas do contorno."""
    segs = []
    for membro in relacao.get("members", []):
        geo = membro.get("geometry") or []
        for p, q in zip(geo, geo[1:], strict=False):
            segs.append((p["lon"], p["lat"], q["lon"], q["lat"]))
    return segs


def dentro(lon: float, lat: float, segs) -> bool:
    """Regra par-ímpar (ray casting). Funciona sem montar os anéis do polígono."""
    dentro_ = False
    for x1, y1, x2, y2 in segs:
        if (y1 > lat) != (y2 > lat):
            x = x1 + (lat - y1) * (x2 - x1) / (y2 - y1)
            if x > lon:
                dentro_ = not dentro_
    return dentro_


def distancia_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def coordenadas(elemento: dict) -> tuple[float, float]:
    if "lat" in elemento:
        return elemento["lat"], elemento["lon"]
    return elemento["center"]["lat"], elemento["center"]["lon"]


def pontuacao(tipo: str, nome: str) -> int:
    """Quanto maior, melhor candidato a abrigo. 0 = descartar.

    Prefere escolas públicas e ginásios de verdade (é o que costuma virar abrigo);
    descarta academias e clubes privados marcados como centro esportivo.
    """
    if tipo == "ginasio":
        return 3 if GINASIO.search(nome) else 0
    if PUBLICA.search(nome):
        return 2 if INFANTIL.search(nome) else 3
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, default=PASTA / ".cache_osm")
    args = parser.parse_args()

    geom = baixar("bairros_geom.json", args.cache)
    pontos = baixar("bairros_pontos.json", args.cache)
    locais = baixar("locais.json", args.cache)

    rotulos = {
        n["tags"]["name"]: (n["lat"], n["lon"])
        for n in pontos["elements"]
        if n["type"] == "node"
    }
    bairros = []
    for rel in geom["elements"]:
        if rel["type"] != "relation":
            continue
        nome = rel["tags"]["name"]
        segs = segmentos_do_bairro(rel)
        if nome in rotulos:
            lat, lon = rotulos[nome]
        else:
            lat = sum(s[1] for s in segs) / len(segs)
            lon = sum(s[0] for s in segs) / len(segs)
        bairros.append({"id": slug(nome), "nome": nome, "segs": segs, "lat": lat, "lon": lon})
    bairros.sort(key=lambda b: b["nome"])

    def bairro_de(lat: float, lon: float) -> dict | None:
        return next((b for b in bairros if dentro(lon, lat, b["segs"])), None)

    with (PASTA / "estacoes.csv").open(encoding="utf-8") as f:
        estacoes = list(csv.DictReader(f))
    for e in estacoes:
        b = bairro_de(float(e["lat"]), float(e["lon"]))
        achado = b["id"] if b else "(fora de Porto Alegre)"
        if achado != e["bairro_id"]:
            print(f"AVISO estação {e['id']}: bairro informado {e['bairro_id']}, ponto cai em {achado}")
    reais = [e for e in estacoes if e["demo"] != "true"]

    candidatos: dict[str, list[dict]] = {}
    for el in locais["elements"]:
        tags = el.get("tags", {})
        lat, lon = coordenadas(el)
        b = bairro_de(lat, lon)
        if not b:
            continue
        tipo = "escola" if tags.get("amenity") == "school" else "ginasio"
        candidatos.setdefault(b["nome"], []).append(
            {"osm": f"{el['type']}/{el['id']}", "nome": tags["name"].strip(), "tipo": tipo, "lat": lat, "lon": lon, "bairro": b}
        )

    escolhidos = []
    for nome_bairro in BAIRROS_ABRIGO_RISCO + BAIRROS_ABRIGO_SEGURO:
        opcoes = [c for c in candidatos.get(nome_bairro, []) if pontuacao(c["tipo"], c["nome"]) > 0]
        if not opcoes:
            print(f"AVISO sem escola/ginásio no OSM para {nome_bairro}")
            continue
        opcoes.sort(key=lambda c: (-pontuacao(c["tipo"], c["nome"]), c["nome"]))
        escolhidos.append(opcoes[0])
        if len(escolhidos) == TOTAL_ABRIGOS:
            break

    with (PASTA / "bairros.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "nome", "zona_risco", "lat", "lon"])
        for b in bairros:
            zona = "alta" if b["nome"] in BAIRROS_RISCO else "baixa"
            w.writerow([b["id"], b["nome"], zona, f"{b['lat']:.5f}", f"{b['lon']:.5f}"])

    abrigos = []
    for i, c in enumerate(escolhidos, start=1):
        proxima = min(reais, key=lambda e: distancia_km(c["lat"], c["lon"], float(e["lat"]), float(e["lon"])))
        abrigos.append({
            "id": f"abr-{i:02d}",
            "osm_ref": c["osm"],
            "nome": c["nome"],
            "tipo": c["tipo"],
            "bairro_id": c["bairro"]["id"],
            "lat": f"{c['lat']:.5f}",
            "lon": f"{c['lon']:.5f}",
            "capacidade": CAPACIDADE[c["tipo"]],
            "capacidade_estimada": "true",
            "em_area_de_risco": str(c["bairro"]["nome"] in BAIRROS_RISCO).lower(),
            "estacao_proxima_id": proxima["id"],
            "demo": "false",
        })
    # Duas estações fictícias (demo = true), cada uma com o seu abrigo: a do circuito ESP32 no Wokwi e a
    # dos testes de integração, que publicam nela para não mexer na simulação nem no ESP32.
    for estacao_id, abrigo_id, nome in (("demo-wokwi", "abr-demo", "Abrigo de demonstração (Wokwi)"),
                                        ("tst-integracao", "abr-teste", "Abrigo de teste (integração)")):
        demo = next(e for e in estacoes if e["id"] == estacao_id)
        abrigos.append({
            "id": abrigo_id, "osm_ref": "", "nome": nome, "tipo": "ginasio",
            "bairro_id": demo["bairro_id"], "lat": demo["lat"], "lon": demo["lon"], "capacidade": 50,
            "capacidade_estimada": "true", "em_area_de_risco": "false", "estacao_proxima_id": demo["id"], "demo": "true",
        })
    with (PASTA / "abrigos.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(abrigos[0]))
        w.writeheader()
        w.writerows(abrigos)

    # Os sensores das estações fictícias publicam como a ponte do Wokwi (origem "wokwi"); os demais são do simulador.
    prefixo_demo = {"demo-wokwi": "wok", "tst-integracao": "tst", "abr-demo": "wok", "abr-teste": "tst"}
    sensores = []
    for e in estacoes:
        origem = "wokwi" if e["demo"] == "true" else "sim"
        prefixo = prefixo_demo.get(e["id"], e["id"])
        sensores.append([f"{prefixo}-nivel", "nivel_rio", "m", e["id"], "", origem, 0, 15])
        sensores.append([f"{prefixo}-chuva", "chuva", "mm", e["id"], "", origem, 0, 60])
    for a in abrigos:
        sid = f"{prefixo_demo[a['id']]}-ocup" if a["demo"] == "true" else f"{a['id']}-ocup"
        origem = "wokwi" if a["demo"] == "true" else "sim"
        sensores.append([sid, "ocupacao_abrigo", "pessoas", "", a["id"], origem, 0, int(a["capacidade"]) * 2])
    with (PASTA / "sensores.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "tipo", "unidade", "estacao_id", "abrigo_id", "origem", "valor_min", "valor_max"])
        w.writerows(sensores)

    print(f"{len(bairros)} bairros, {len(abrigos)} abrigos, {len(sensores)} sensores gerados em {PASTA}")
    for a in abrigos:
        print(f"  {a['id']}  {a['tipo']:7}  risco={a['em_area_de_risco']:5}  {a['bairro_id']:20}  {a['nome']}")


if __name__ == "__main__":
    main()
