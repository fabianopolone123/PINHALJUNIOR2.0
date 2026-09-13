"""Preparo da foto do lote.

Foto tirada no celular tem 3-5 MB e vem **girada** (a orientação fica só no
EXIF). Num leilão com 50 pessoas, servir o arquivo cru é o caminho mais curto
para a tela travar — e uma foto deitada estraga o item mais bonito do leilão.

Usa **Pillow**, que já é dependência do projeto. Nada novo entra por aqui.
"""

import logging
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

LARGURA_MAX = 1280
LARGURA_MINI = 420
QUALIDADE = 82


def _abrir_corrigida(arquivo):
    """Abre a imagem já **desgirada** pelo EXIF e em RGB."""
    img = Image.open(arquivo)
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
        original = _abrir_corrigida(lote.foto)

        grande = _reduzir(original, LARGURA_MAX)
        buffer_grande = BytesIO()
        grande.convert("RGB").save(buffer_grande, format="JPEG", quality=QUALIDADE, optimize=True)

        mini = _reduzir(original, LARGURA_MINI)
        buffer_mini = BytesIO()
        mini.convert("RGB").save(buffer_mini, format="JPEG", quality=QUALIDADE, optimize=True)

        base = f"lote-{lote.pk}.jpg"
        lote.foto.save(base, ContentFile(buffer_grande.getvalue()), save=False)
        lote.foto_mini.save(f"mini-{base}", ContentFile(buffer_mini.getvalue()), save=False)
        lote.save(update_fields=["foto", "foto_mini"])
        return True
    except Exception:  # noqa: BLE001 — foto ruim não derruba o cadastro
        logger.exception("Leilão: falha ao preparar a foto do lote %s", lote.pk)
        return False
