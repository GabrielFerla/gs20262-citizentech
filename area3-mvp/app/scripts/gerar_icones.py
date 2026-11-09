"""Gera os ícones do Abriga em assets/ a partir do mesmo desenho do logotipo do app (src/componentes/Icones.tsx).

O desenho é "um telhado acima da água": um telhado branco sobre uma onda verde-clara, em fundo verde,
num quadro de 64 × 64. Só as cores da marca (nada de brasão, faixa ou cores de órgão público).
O script redesenha em alta resolução com o Pillow (que já vem com o requirements-dev.txt) e reduz,
para as bordas saírem suaves.

    .venv/bin/python area3-mvp/app/scripts/gerar_icones.py      # na raiz do repositório
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parents[1] / "assets"
PRIMARIA = (0x1F, 0x7A, 0x5C)  # cores.primaria em src/tema.ts
ONDA = (0x7D, 0xD3, 0xAE)  # cores.primariaSobreEscuro
BRANCO = (255, 255, 255)
AMPLIAR = 4  # desenha 4 vezes maior e reduz (antisserrilhado)

# Desenho no quadro de 64: telhado "M14 34 L32 17 L50 34" e onda "M12 46 q5-5 10 0 t10 0 10 0 10 0".
TELHADO = [(14, 34), (32, 17), (50, 34)]
# Cada trecho da onda é uma curva quadrática: (início, controle, fim). O "t" reflete o controle anterior.
ONDA_TRECHOS = [
    ((12, 46), (17, 41), (22, 46)),
    ((22, 46), (27, 51), (32, 46)),
    ((32, 46), (37, 41), (42, 46)),
    ((42, 46), (47, 51), (52, 46)),
]
RAIO_DO_CANTO = 14.3  # 22% do quadro: o mesmo arredondado da máscara de ícone do sistema


def _quadratica(p0, p1, p2, passos=32):
    for i in range(1, passos + 1):
        t = i / passos
        u = 1 - t
        yield (u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0], u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1])


def _pontos_da_onda():
    pontos = [ONDA_TRECHOS[0][0]]
    for p0, p1, p2 in ONDA_TRECHOS:
        pontos += list(_quadratica(p0, p1, p2))
    return pontos


def desenhar(
    lado: int,
    *,
    fundo=None,
    canto: bool = False,
    escala: float = 1.0,
    cor_do_telhado=BRANCO,
    cor_da_onda=ONDA,
    traco_do_telhado: float = 6,
    traco_da_onda: float = 5,
) -> Image.Image:
    """O desenho de 64 unidades num quadro de `lado` px. `escala` < 1 encolhe o desenho em volta do centro."""
    grande = lado * AMPLIAR
    imagem = Image.new("RGBA", (grande, grande), (0, 0, 0, 0))
    traco = ImageDraw.Draw(imagem)
    if fundo is not None:
        if canto:
            traco.rounded_rectangle((0, 0, grande - 1, grande - 1), radius=grande * RAIO_DO_CANTO / 64, fill=fundo)
        else:
            traco.rectangle((0, 0, grande, grande), fill=fundo)

    unidade = grande / 64 * escala

    def p(x, y):
        return (grande / 2 + (x - 32) * unidade, grande / 2 + (y - 32) * unidade)

    def linha(pontos, largura, cor):
        convertidos = [p(*q) for q in pontos]
        traco.line(convertidos, fill=cor, width=round(largura * unidade), joint="curve")
        raio = largura * unidade / 2
        for x, y in (convertidos[0], convertidos[-1], *convertidos[1:-1]):  # pontas e juntas arredondadas
            traco.ellipse((x - raio, y - raio, x + raio, y + raio), fill=cor)

    linha(TELHADO, traco_do_telhado, cor_do_telhado)
    linha(_pontos_da_onda(), traco_da_onda, cor_da_onda)
    return imagem.resize((lado, lado), Image.Resampling.LANCZOS)


def main() -> None:
    # iOS não aceita transparência no ícone: fundo verde cheio (os cantos vêm da máscara do sistema).
    desenhar(1024, fundo=PRIMARIA).convert("RGB").save(ASSETS / "icon.png", optimize=True)
    # Navegador: quadrado arredondado. Abaixo de 60 px o traço engrossa um pouco para não sumir.
    desenhar(48, fundo=PRIMARIA, canto=True, traco_do_telhado=7, traco_da_onda=6).save(ASSETS / "favicon.png")
    # Android (ícone adaptativo, 108 de lado): o sistema recorta um círculo de uns 72 no centro. O desenho
    # ocupa 78% desse círculo e fica dentro da zona segura (66 de 108).
    no_circulo = 72 / 108 * 0.78
    Image.new("RGB", (512, 512), PRIMARIA).save(ASSETS / "android-icon-background.png", optimize=True)
    desenhar(512, escala=no_circulo).save(ASSETS / "android-icon-foreground.png", optimize=True)
    # Monocromático (temas do Android 13 ou superior): só o traço, numa cor; o sistema pinta.
    desenhar(432, escala=no_circulo, cor_da_onda=BRANCO).save(ASSETS / "android-icon-monochrome.png", optimize=True)
    # Tela de abertura: o ícone (quadrado arredondado) pela metade, sobre o fundo claro.
    abertura = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    abertura.paste(desenhar(512, fundo=PRIMARIA, canto=True), (256, 256))
    abertura.save(ASSETS / "splash-icon.png", optimize=True)
    print(f"ícones gravados em {ASSETS}")


if __name__ == "__main__":
    main()
