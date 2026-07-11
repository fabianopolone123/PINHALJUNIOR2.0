"""
Importa a DIRETORIA (voluntários) do sistema antigo para o novo.

Cria/atualiza um `MembroDiretoria` (+ `FichaMedicaDiretoria` + foto) por
integrante e vincula ao perfil "Diretoria". Lê direto do ZIP de exportação.

Regras (definidas com o Fabiano em 2026-07-11):
- PULA o registro de teste e o `fabianop` (Fabiano já é o Diretor no novo).
- MESCLAGEM: quem tem diretoria num login e o aventureiro em outro é anexado ao
  login que TEM o aventureiro (o mais usado). Mapa em `MESCLAGEM`.
- Só-diretoria cujo login ainda não existe no novo: o User é criado preservando
  o username e o hash da senha do sistema antigo.

Idempotente (update_or_create por usuário). Use --dry-run para simular.
Rodar LOCALMENTE (o ZIP é git-ignored); depois sincronizar db/media para o VPS.

Uso:
    python manage.py importar_diretoria --dry-run
    python manage.py importar_diretoria
"""

import json
import os
import zipfile

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_date

from core.models import FichaMedicaDiretoria, MembroDiretoria

ZIP_PADRAO = "exportacao_migracao_pinhal_20260705_155620_com_arquivos.zip"

# Config de migração (skip + mesclagem) fica FORA do código, pois contém logins/
# nomes reais (dado pessoal — não versionar). Arquivo JSON local, git-ignored:
#   {"skip": ["teste123", "fabianop"],
#    "mesclagem": {"<login antigo diretoria>": "<login novo a manter>"}}
# Sem o arquivo, só o registro de teste é pulado e não há mesclagens.
CONFIG_PADRAO = "migracao_mesclagem.json"
SKIP_FALLBACK = {"teste123"}

PASTA_FOTOS = "diretoria/fotos"


def _carregar_config(path):
    """Lê skip + mesclagem do JSON local (se existir)."""
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fp:
            data = json.load(fp)
        return set(data.get("skip", []) or []), dict(data.get("mesclagem", {}) or {})
    return set(SKIP_FALLBACK), {}


def _s(v):
    return (v or "").strip() if isinstance(v, str) else (v or "")


def _estado_civil(v):
    s = _s(v).lower()
    if "casad" in s:
        return "casado"
    if "divor" in s:
        return "divorciado"
    if "viuv" in s or "viúv" in s:
        return "viuvo"
    if "solte" in s:
        return "solteiro"
    if "uniao" in s or "união" in s or "estáv" in s or "estav" in s:
        return "uniao_estavel"
    return ""  # texto solto/lixo (ex.: "51531") -> vazio


def _escolaridade(v):
    s = _s(v).lower()
    if "fund" in s:
        return "fundamental"
    if "med" in s or "méd" in s:
        return "medio"
    if "super" in s or "facul" in s:
        return "superior"
    return ""


class Command(BaseCommand):
    help = "Importa a diretoria (voluntários) do sistema antigo (MembroDiretoria)."

    def add_arguments(self, parser):
        parser.add_argument("--zip", default=ZIP_PADRAO, help="Caminho do ZIP de exportação.")
        parser.add_argument("--config", default=CONFIG_PADRAO, help="JSON local com skip/mesclagem.")
        parser.add_argument("--dry-run", action="store_true", help="Só simula (não grava).")

    def handle(self, *args, **opts):
        zpath = opts["zip"]
        dry = opts["dry_run"]
        if not os.path.exists(zpath):
            raise CommandError(f"ZIP não encontrado: {zpath}")

        SKIP_LOGINS, MESCLAGEM = _carregar_config(opts["config"])
        if not MESCLAGEM:
            self.stdout.write(self.style.WARNING(
                f"  (sem config de mesclagem em '{opts['config']}' — cada um no próprio login)"))

        z = zipfile.ZipFile(zpath)

        def load(p):
            return json.loads(z.read(p).decode("utf-8"))

        def f(r):
            return r.get("fields", r)

        users_old = {f(u)["id"]: f(u) for u in load("dados_json/auth/user.json")}
        diretoria = load("dados_json/accounts/diretoria.json")

        criados_membro = atualizados = users_criados = pulados = fotos = fichas = 0
        avisos = []

        contexto = _NoOp() if dry else transaction.atomic()
        with contexto:
            grupo = None
            if not dry:
                grupo, _ = Group.objects.get_or_create(name="Diretoria")

            for d in diretoria:
                fd = f(d)
                uold = users_old.get(fd["user"]) or {}
                login_antigo = _s(uold.get("username"))
                nome = _s(fd.get("nome"))

                if login_antigo in SKIP_LOGINS:
                    pulados += 1
                    self.stdout.write(f"  PULADO: {nome} ({login_antigo})")
                    continue

                alvo = MESCLAGEM.get(login_antigo, login_antigo)
                user = User.objects.filter(username=alvo).first()

                acao_user = "usa existente"
                if user is None:
                    if not login_antigo:
                        avisos.append(f"{nome}: sem login antigo — pulado")
                        pulados += 1
                        continue
                    acao_user = "CRIA login"
                    if not dry:
                        user = User(
                            username=alvo,
                            password=uold.get("password", ""),  # hash Django (preserva senha)
                            email=_s(uold.get("email")),
                            first_name=_s(uold.get("first_name"))[:150],
                            last_name=_s(uold.get("last_name"))[:150],
                            is_active=bool(uold.get("is_active", True)),
                        )
                        user.save()
                        users_criados += 1

                self.stdout.write(
                    f"  {nome:<34} -> login '{alvo}' ({acao_user})"
                    + (f"  [mesclagem de '{login_antigo}']" if alvo != login_antigo else "")
                )

                if dry:
                    continue

                defaults = {
                    "nome_completo": nome[:150],
                    "igreja": _s(fd.get("igreja"))[:150],
                    "distrito": _s(fd.get("distrito"))[:150],
                    "cpf": _s(fd.get("cpf"))[:20],
                    "rg": _s(fd.get("rg"))[:30],
                    "data_nascimento": parse_date(_s(fd.get("nascimento"))) or None,
                    "estado_civil": _estado_civil(fd.get("estado_civil")),
                    "conjuge_nome": _s(fd.get("conjuge"))[:150],
                    "email": _s(fd.get("email")),
                    "whatsapp": _s(fd.get("whatsapp"))[:20],
                    "tel_residencial": _s(fd.get("telefone_residencial"))[:20],
                    "tel_comercial": _s(fd.get("telefone_comercial"))[:20],
                    "endereco": _s(fd.get("endereco"))[:200],
                    "numero": _s(fd.get("numero"))[:20],
                    "bairro": _s(fd.get("bairro"))[:100],
                    "cidade": _s(fd.get("cidade"))[:100],
                    "cep": _s(fd.get("cep"))[:15],
                    "estado": _s(fd.get("estado"))[:50],
                    "escolaridade": _escolaridade(fd.get("escolaridade")),
                    "compromisso_aceito": True,
                    "declaracao_medica_aceita": bool(fd.get("declaracao_medica", True)),
                    "autorizacao_imagem_aceita": bool(fd.get("autorizacao_imagem", True)),
                }
                filhos = [fd.get("filho_1"), fd.get("filho_2"), fd.get("filho_3")]
                qtd = sum(1 for x in filhos if _s(x))
                defaults["tem_filhos"] = qtd > 0
                defaults["qtd_filhos"] = qtd

                membro, novo = MembroDiretoria.objects.update_or_create(
                    usuario=user, defaults=defaults
                )
                if novo:
                    criados_membro += 1
                else:
                    atualizados += 1

                user.groups.add(grupo)

                # Foto
                foto = fd.get("foto") or {}
                exported = foto.get("exported_path")
                if exported and exported in z.namelist():
                    ext = os.path.splitext(exported)[1] or ".png"
                    membro.foto.save(
                        f"dir_{membro.pk}{ext}", ContentFile(z.read(exported)), save=True
                    )
                    fotos += 1

                # Ficha médica (o antigo só tem limitação de saúde -> outros_problemas)
                lim = _s(fd.get("limitacao_saude_descricao"))
                FichaMedicaDiretoria.objects.update_or_create(
                    membro=membro,
                    defaults={"outros_problemas": lim if fd.get("possui_limitacao_saude") else ""},
                )
                fichas += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== Resumo importar_diretoria ==="))
        self.stdout.write(f"  {'(dry-run) ' if dry else ''}membros criados: {criados_membro} | "
                          f"atualizados: {atualizados} | users criados: {users_criados}")
        self.stdout.write(f"  fotos: {fotos} | fichas médicas: {fichas} | pulados: {pulados}")
        for a in avisos:
            self.stdout.write(self.style.WARNING("  aviso: " + a))
        if dry:
            self.stdout.write(self.style.WARNING("  (nada foi gravado — rode sem --dry-run para aplicar)"))


class _NoOp:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False
