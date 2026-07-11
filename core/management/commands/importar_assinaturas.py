"""
Importa as ASSINATURAS desenhadas do sistema antigo para o novo.

- Aventureiro: `aventureiroficha` tem 3 assinaturas em base64 (inscrição,
  declaração médica, termo de imagem) -> `AssinaturaDocumento` (casa por CPF).
- Diretoria: `diretoriaficha` tem 2 (compromisso, termo de imagem) ->
  `AssinaturaDocumentoDiretoria`. A declaração médica não existia no antigo:
  recebe uma CÓPIA da assinatura do compromisso, para ficar com as 3 (decisão do
  Fabiano em 2026-07-11). Casa por CPF via a tabela `diretoria`.

Depende do `importar_diretoria` já ter rodado (para as assinaturas de diretoria).
Idempotente: pula a assinatura que já existir. Use --dry-run para simular.
Rodar LOCALMENTE (o ZIP é git-ignored); depois sincronizar db/media para o VPS.

Uso:
    python manage.py importar_assinaturas --dry-run
    python manage.py importar_assinaturas
"""

import base64
import binascii
import json
import os
import re
import uuid
import zipfile

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core import termos
from core.models import (
    AssinaturaDocumento,
    AssinaturaDocumentoDiretoria,
    Aventureiro,
    MembroDiretoria,
)

ZIP_PADRAO = "exportacao_migracao_pinhal_20260705_155620_com_arquivos.zip"


def _dig(s):
    return re.sub(r"\D", "", s or "")


def _decode(data_url):
    """data:image/png;base64,... -> ContentFile PNG (ou None)."""
    if not data_url or not isinstance(data_url, str):
        return None
    payload = data_url.split(",", 1)[1] if "," in data_url else data_url
    try:
        binario = base64.b64decode(payload)
    except (binascii.Error, ValueError, TypeError):
        return None
    if not binario:
        return None
    return ContentFile(binario, name=f"mig_{uuid.uuid4().hex}.png")


def _img(z, ref):
    """A assinatura vem como referência de arquivo ({exported_path,...}) OU, na
    falta, como base64. Devolve um ContentFile pronto para o ImageField (ou None)."""
    if isinstance(ref, dict):
        ep = ref.get("exported_path")
        if not ep or ep not in z.namelist():
            return None
        ext = os.path.splitext(ep)[1] or ".png"
        return ContentFile(z.read(ep), name=f"mig_{uuid.uuid4().hex}{ext}")
    return _decode(ref)


class _NoOp:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Command(BaseCommand):
    help = "Importa as assinaturas desenhadas (aventureiro e diretoria) do sistema antigo."

    def add_arguments(self, parser):
        parser.add_argument("--zip", default=ZIP_PADRAO)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        zpath = opts["zip"]
        dry = opts["dry_run"]
        if not os.path.exists(zpath):
            raise CommandError(f"ZIP não encontrado: {zpath}")
        z = zipfile.ZipFile(zpath)

        def load(p):
            return json.loads(z.read(p).decode("utf-8"))

        def f(r):
            return r.get("fields", r)

        avfichas = load("dados_json/accounts/aventureiroficha.json")
        dirfichas = load("dados_json/accounts/diretoriaficha.json")
        diretoria = {f(d)["id"]: f(d) for d in load("dados_json/accounts/diretoria.json")}

        contexto = _NoOp() if dry else transaction.atomic()
        with contexto:
            av_ok, av_sig, av_skip, av_nomatch = self._aventureiro(avfichas, z, dry)
            dir_ok, dir_sig, dir_skip, dir_nomatch = self._diretoria(dirfichas, diretoria, z, dry)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== Resumo importar_assinaturas ==="))
        self.stdout.write(f"  {'(dry-run) ' if dry else ''}AVENTUREIRO: fichas casadas {av_ok} | "
                          f"assinaturas criadas {av_sig} | já existiam {av_skip} | sem match {av_nomatch}")
        self.stdout.write(f"  DIRETORIA: fichas casadas {dir_ok} | assinaturas criadas {dir_sig} | "
                          f"já existiam {dir_skip} | sem match {dir_nomatch}")
        if dry:
            self.stdout.write(self.style.WARNING("  (nada foi gravado — rode sem --dry-run para aplicar)"))

    # ---------------------------------------------------------------- aventureiro
    def _aventureiro(self, fichas, z, dry):
        por_cpf = {}
        for av in Aventureiro.objects.all():
            por_cpf.setdefault(_dig(av.cpf), av)

        campos = [
            ("assinatura_inscricao", AssinaturaDocumento.DOC_INSCRICAO),
            ("assinatura_declaracao_medica", AssinaturaDocumento.DOC_DECLARACAO_MEDICA),
            ("assinatura_termo_imagem", AssinaturaDocumento.DOC_AUTORIZACAO_IMAGEM),
        ]
        casadas = criadas = skip = nomatch = 0
        for fic in fichas:
            ff = fic.get("fields", fic)
            cpf = _dig((ff.get("inscricao_data") or {}).get("cpf_aventureiro"))
            av = por_cpf.get(cpf) if cpf else None
            if av is None:
                nomatch += 1
                continue
            casadas += 1
            autorizacao = getattr(av, "autorizacao_imagem", None)
            for campo, doc in campos:
                if not ff.get(campo):
                    continue
                if AssinaturaDocumento.objects.filter(aventureiro=av, documento=doc).exists():
                    skip += 1
                    continue
                if dry:
                    criadas += 1
                    continue
                img = _img(z, ff.get(campo))
                if img is None:
                    continue
                titulo, texto = termos.montar_texto(doc, av, autorizacao)
                AssinaturaDocumento.objects.create(
                    aventureiro=av, documento=doc, imagem=img,
                    titulo_documento=titulo, texto_documento=texto,
                    assinante_nome=av.resp_nome, assinante_cpf=av.resp_cpf,
                )
                criadas += 1
        return casadas, criadas, skip, nomatch

    # ------------------------------------------------------------------ diretoria
    def _diretoria(self, fichas, diretoria, z, dry):
        por_cpf = {}
        for m in MembroDiretoria.objects.all():
            por_cpf.setdefault(_dig(m.cpf), m)

        casadas = criadas = skip = nomatch = 0
        for fic in fichas:
            ff = fic.get("fields", fic)
            dir_antiga = diretoria.get(ff.get("diretoria")) or {}
            cpf = _dig(dir_antiga.get("cpf"))
            membro = por_cpf.get(cpf) if cpf else None
            if membro is None:
                nomatch += 1
                continue
            casadas += 1
            # compromisso e imagem vêm do antigo; declaração médica = cópia do compromisso.
            mapa = [
                (ff.get("assinatura_compromisso"), AssinaturaDocumentoDiretoria.DOC_COMPROMISSO),
                (ff.get("assinatura_termo_imagem"), AssinaturaDocumentoDiretoria.DOC_AUTORIZACAO_IMAGEM),
                (ff.get("assinatura_compromisso"), AssinaturaDocumentoDiretoria.DOC_DECLARACAO_MEDICA),
            ]
            for data_url, doc in mapa:
                if not data_url:
                    continue
                if AssinaturaDocumentoDiretoria.objects.filter(membro=membro, documento=doc).exists():
                    skip += 1
                    continue
                if dry:
                    criadas += 1
                    continue
                img = _img(z, data_url)
                if img is None:
                    continue
                titulo, texto = termos.montar_texto_diretoria(doc, membro)
                AssinaturaDocumentoDiretoria.objects.create(
                    membro=membro, documento=doc, imagem=img,
                    titulo_documento=titulo, texto_documento=texto,
                    assinante_nome=membro.nome_completo, assinante_cpf=membro.cpf,
                )
                criadas += 1
        return casadas, criadas, skip, nomatch
