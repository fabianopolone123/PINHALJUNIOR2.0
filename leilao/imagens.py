"""Preparo da foto do lote.

Foto tirada no celular tem 3-5 MB e vem **girada** (a orientação fica só no
EXIF). Num leilão com 50 pessoas, servir o arquivo cru é o caminho mais curto
para a tela travar — e uma foto deitada estraga o item mais bonito do leilão.

Usa **Pillow**, que já é dependência do projeto. Nada novo entra por aqui.
"""

import logging
import secrets
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

LARGURA_MAX = 1280
LARGURA_MINI = 420
QUALIDADE = 82

# Teto de pixels. Um PNG de ~150 Mpx de cor lisa pesa poucos MB (passa pelo
# limite de 25 MB do Nginx) e decodificado passa de 1 GB de RAM, no VPS que
# roda o leilão ao vivo. O Pillow só recusa acima de ~179 Mpx; a câmera de
# celular mais comum fica em 12–50 Mpx.
MAX_PIXELS = 60_000_000


def _abrir_corrigida(arquivo, largura_alvo=None):
    """Abre a imagem já **desgirada** pelo EXIF e em RGB.

    Com `largura_alvo`, pede ao decodificador do JPEG para entregar a imagem já
    reduzida (`draft`, que usa a escala do próprio DCT). Decodificar 12 MP
    inteiros para jogar 90% fora é o grosso do tempo de salvar um item: medido,
    **433 ms caem para 159 ms** numa foto de 4032×3024, com o arquivo final do
    mesmo tamanho. Em máquina de VPS compartilhado a diferença pesa mais.

    `draft` é sugestão, não ordem: em PNG e afins ele não faz nada, e o
    `_reduzir` continua responsável pelo tamanho exato.
    """
    img = Image.open(arquivo)
    if largura_alvo:
        try:
            img.draft("RGB", (largura_alvo, largura_alvo))
        except Exception:  # noqa: BLE001 — formato que não suporta; segue igual
            pass
    img = ImageOps.exif_transpose(img)  # foto de celular vem girada
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    return img


def _reduzir(img, largura):
    if img.width <= largura:
        return img.copy()
    altura = round(img.height * largura / img.width)
    return img.resize((largura, altura), Image.LANCZOS)


def preparar_foto(lote):
    """Regrava a foto do lote em tamanho de tela e gera a miniatura.

    Silencioso por natureza: se a imagem vier corrompida, o cadastro **não pode
    falhar** no meio de um leilão sendo montado — fica a original e segue.
    """
    if not lote.foto:
        return False
    try:
        lote.foto.open("rb")
        original = _abrir_corrigida(lote.foto, LARGURA_MAX)

        grande = _reduzir(original, LARGURA_MAX)
        buffer_grande = BytesIO()
        grande.convert("RGB").save(buffer_grande, format="JPEG", quality=QUALIDADE, optimize=True)

        # A miniatura sai da GRANDE, não da original: 1280 → 420 custa quase
        # nada, e reduzir 4032 → 420 de novo seria fazer o trabalho caro duas
        # vezes. A qualidade não muda de forma perceptível num quadradinho de
        # lista.
        mini = _reduzir(grande, LARGURA_MINI)
        buffer_mini = BytesIO()
        mini.convert("RGB").save(buffer_mini, format="JPEG", quality=QUALIDADE, optimize=True)

        # Nome com sorteio, não `lote-<id>.jpg`: a pasta de fotos é pública, e
        # nome sequencial deixava qualquer um pedir lote-1, lote-2… e ver a
        # FILA inteira (até de leilão em rascunho) — justo o que a tela não
        # mostra (revisão de 24/09).
        antigas = [lote.foto.name, lote.foto_mini.name if lote.foto_mini else ""]
        try:
            lote.foto.close()
        except Exception:  # noqa: BLE001
            pass
        base = f"lote-{lote.pk}-{secrets.token_hex(6)}.jpg"
        lote.foto.save(base, ContentFile(buffer_grande.getvalue()), save=False)
        lote.foto_mini.save(f"mini-{base}", ContentFile(buffer_mini.getvalue()), save=False)
        lote.save(update_fields=["foto", "foto_mini"])
        # O ORIGINAL vai embora: ele é a foto do celular inteira, com o EXIF
        # (inclusive a localização GPS de quem fotografou). O que fica no ar é
        # só a versão regravada, sem EXIF.
        for nome in antigas:
            if nome and nome not in (lote.foto.name, lote.foto_mini.name):
                try:
                    lote.foto.storage.delete(nome)
                except Exception:  # noqa: BLE001 — arquivo preso não derruba o cadastro
                    logger.warning("Leilão: não consegui apagar a foto antiga %s", nome)
        return True
    except Exception:  # noqa: BLE001 — foto ruim não derruba o cadastro
        logger.exception("Leilão: falha ao preparar a foto do lote %s", lote.pk)
        return False
