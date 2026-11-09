"""Gera os ícones do Abriga em assets/ a partir do mesmo desenho do logotipo do app (src/componentes/Icones.tsx).

O desenho é o telhado com a gota, num quadro de 48 × 48. O script redesenha em alta resolução com o Pillow
(que já vem com o requirements-dev.txt) e reduz, para as bordas saírem suaves.

    .venv/bin/python area3-mvp/app/scripts/gerar_icones.py      # na raiz do repositório
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parents[1] / "assets"
PRIMARIA = (0x0B, 0x5D, 0x73)  # cores.primaria em src/tema.ts
BRANCO = (255, 255, 255)
FUNDO = (0xF4, 0xF7, 0xF9)  # web.backgroundColor em app.json
AMPLIAR = 4  # desenha 4 vezes maior e reduz (antisserrilhado)


def _cubica(p0, p1, p2, p3, passos=48):
    for i in range(1, passos + 1):
        t = i / passos
        u = 1 - t
        yield (
            u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0],
            u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1],
        )


def _gota():
    """M24 19 C24 19 17 27.5 17 31.5 A7 7 0 0 0 31 31.5 C31 27.5 24 19 24 19 Z (o arco passa por baixo)."""
    pontos = [(24, 19), *_cubica((24, 19), (24, 19), (17, 27.5), (17, 31.5))]
    pontos += [(24 + 7 * math.cos(a), 31.5 + 7 * math.sin(a)) for a in (math.pi * (1 - i / 48) for i in range(1, 49))]
    pontos += list(_cubica((31, 31.5), (31, 27.5), (24, 19), (24, 19)))
    return pontos


def desenhar_logo(lado: int, cor, fundo=None, escala: float = 0.62, quadrado_arredondado: bool = False) -> Image.Image:
    """O logotipo centrado num quadro de `lado` px; `escala` é a fração do quadro ocupada pelo desenho de 48 unidades."""
    grande = lado * AMPLIAR
    imagem = Image.new("RGBA", (grande, grande), (0, 0, 0, 0))
    traco = ImageDraw.Draw(imagem)
    if fundo is not None:
        if quadrado_arredondado:
            traco.rounded_rectangle((0, 0, grande - 1, grande - 1), radius=grande * 0.22, fill=fundo)
        else:
            traco.rectangle((0, 0, grande, grande), fill=fundo)

    unidade = grande * escala / 48
    deslocamento = (grande - 48 * unidade) / 2

    def p(x, y):
        return (deslocamento + x * unidade, deslocamento + y * unidade)

    def linha(pontos, largura, pontas_redondas):
        convertidos = [p(*q) for q in pontos]
        traco.line(convertidos, fill=cor, width=round(largura * unidade), joint="curve")
        raio = largura * unidade / 2
        juntas = convertidos if pontas_redondas else convertidos[1:-1]
        for x, y in juntas:
            traco.ellipse((x - raio, y - raio, x + raio, y + raio), fill=cor)

    linha([(5, 23), (24, 7), (43, 23)], 4.5, pontas_redondas=True)  # telhado
    linha([(11, 21), (11, 41), (37, 41), (37, 21)], 4, pontas_redondas=False)  # paredes
    traco.polygon([p(*q) for q in _gota()], fill=cor)
    return imagem.resize((lado, lado), Image.Resampling.LANCZOS)


def main() -> None:
    # iOS não aceita transparência no ícone: fundo azul-petróleo cheio, logotipo branco.
    desenhar_logo(1024, BRANCO, PRIMARIA).convert("RGB").save(ASSETS / "icon.png", optimize=True)
    # Navegador: quadrado arredondado, legível em 16 px.
    desenhar_logo(48, BRANCO, PRIMARIA, escala=0.78, quadrado_arredondado=True).save(ASSETS / "favicon.png")
    # Android (ícone adaptativo): o sistema recorta o centro; o desenho fica na zona segura (66 de 108).
    Image.new("RGB", (512, 512), PRIMARIA).save(ASSETS / "android-icon-background.png", optimize=True)
    desenhar_logo(512, BRANCO, escala=0.5).save(ASSETS / "android-icon-foreground.png", optimize=True)
    desenhar_logo(432, BRANCO, escala=0.5).save(ASSETS / "android-icon-monochrome.png", optimize=True)
    # Tela de abertura: logotipo na cor do app sobre o fundo claro.
    desenhar_logo(1024, PRIMARIA, escala=0.5).save(ASSETS / "splash-icon.png", optimize=True)
    print(f"ícones gravados em {ASSETS}")


if __name__ == "__main__":
    main()
