"""
Importa os dados de cadastro do sistema ANTIGO (exportação de migração).

Traz APENAS os dados de cadastro ("cadastre-se"): a conta de acesso (login e
senha preservados), os dados de pai, mãe e responsável legal, os dados de cada
aventureiro, a ficha médica e o termo de autorização de imagem, além da foto de
cada aventureiro.

NÃO importa: diretoria, financeiro, eventos, loja, whatsapp, assinaturas, nem
responsáveis que não tenham nenhum aventureiro vinculado.

Estrutura esperada na pasta de origem (pacote descompactado da exportação):
    <origem>/dados_json/auth/user.json
    <origem>/dados_json/accounts/responsavel.json
    <origem>/dados_json/accounts/aventureiro.json
    <origem>/arquivos/...            (fotos referenciadas por exported_path)

Uso:
    python manage.py importar_migracao --origem "C:/caminho/para/exportacao"
    python manage.py importar_migracao --origem "..." --dry-run   # só simula

É seguro rodar mais de uma vez: reaproveita o login pelo username e pula o
aventureiro que já existir (mesmo usuário + mesmo nome). Nunca apaga dados.

IMPORTANTE (segurança de menores): as fotos são dados reais dos membros do
clube e vão apenas para a pasta MEDIA_ROOT (git-ignored). NUNCA versionar.
"""

import json
import os
import shutil

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_date, parse_datetime

from core.models import Aventureiro, AutorizacaoImagem, FichaMedica

# ID do registro-lixo de teste no sistema antigo (nome "teste", CPF inválido).
AVENTUREIRO_LIXO_ID = 41

# Pasta (relativa ao MEDIA_ROOT) das fotos importadas.
PASTA_FOTOS = "aventureiros/fotos"

SEXO_MAP = {"feminino": "F", "masculino": "M"}

SANGUE_MAP = {
    "A+": "A+", "A-": "A-", "AB+": "AB+", "AB-": "AB-",
    "B+": "B+", "B-": "B-", "O+": "O+", "O-": "O-",
    "Não sabe": "NAO_SABE", "": "",
}

# Nomes de doenças (lista antiga) -> campo booleano da FichaMedica.
DOENCA_MAP = {
    "Catapora": "catapora", "Meningite": "meningite", "Hepatite": "hepatite",
    "Dengue": "dengue", "Pneumonia": "pneumonia", "Malária": "malaria",
    "Febre amarela": "febre_amarela", "H1N1": "h1n1", "Cólera": "colera",
    "Rubéola": "rubeola", "Sarampo": "sarampo", "Tétano": "tetano",
}


def _s(valor):
    """Normaliza para string sem espaços nas pontas (None -> '')."""
    return (valor or "").strip() if isinstance(valor, str) else (valor or "")


class Command(BaseCommand):
    help = (
        "Importa os cadastros (login, pai/mãe/responsável, aventureiros, ficha "
        "médica, termo de imagem e fotos) da exportação do sistema antigo."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--origem",
            required=True,
            help="Pasta com o pacote descompactado da exportação (contém dados_json/ e arquivos/).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas simula e mostra o que seria feito, sem gravar nada.",
        )

    # ------------------------------------------------------------------ helpers
    def _carregar(self, origem, caminho_rel):
        caminho = os.path.join(origem, caminho_rel.replace("/", os.sep))
        if not os.path.exists(caminho):
            raise CommandError(f"Arquivo não encontrado: {caminho}")
        with open(caminho, encoding="utf-8") as fp:
            return json.load(fp)

    def _dados_usuario(self, old_user):
        """Campos do login preservando o hash de senha e as datas originais."""
        return {
            "password": old_user.get("password") or "",
            "email": _s(old_user.get("email")),
            "first_name": _s(old_user.get("first_name"))[:150],
            "last_name": _s(old_user.get("last_name"))[:150],
            "is_active": bool(old_user.get("is_active", True)),
            "is_staff": False,
            "is_superuser": False,
            "last_login": parse_datetime(old_user["last_login"]) if old_user.get("last_login") else None,
            "date_joined": parse_datetime(old_user["date_joined"]) if old_user.get("date_joined") else None,
        }

    def _dados_aventureiro(self, av, resp):
        """Monta o dict de campos do Aventureiro (criança + pai/mãe/resp + endereço)."""
        resp_whats = (
            _s(resp.get("responsavel_celular"))
            or _s(resp.get("responsavel_telefone"))
            or _s(resp.get("pai_celular"))
            or _s(resp.get("mae_celular"))
        )
        return {
            "nome_completo": _s(av.get("nome"))[:150],
            "sexo": SEXO_MAP.get(av.get("sexo"), ""),
            "data_nascimento": parse_date(av["nascimento"]) if av.get("nascimento") else None,
            "colegio": _s(av.get("colegio"))[:150],
            "serie": _s(av.get("serie"))[:50],
            "ano": "",
            "bolsa_familia": av.get("bolsa") == "sim",
            "endereco": _s(resp.get("endereco"))[:200],
            "bairro": _s(resp.get("bairro"))[:100],
            "cidade": _s(resp.get("cidade"))[:100],
            "cep": _s(resp.get("cep"))[:15],
            "estado": _s(resp.get("estado"))[:50],
            "certidao_nascimento": _s(av.get("certidao"))[:100],
            "religiao": _s(av.get("religiao"))[:100],
            "rg": _s(av.get("rg"))[:30],
            "orgao_expedidor": _s(av.get("orgao"))[:50],
            "cpf": _s(av.get("cpf"))[:20],
            "tamanho_camiseta": _s(av.get("camiseta"))[:10],
            # Pai
            "pai_nome": _s(resp.get("pai_nome"))[:150],
            "pai_email": _s(resp.get("pai_email")),
            "pai_cpf": _s(resp.get("pai_cpf"))[:20],
            "pai_celular": _s(resp.get("pai_celular"))[:20],
            "pai_whatsapp": _s(resp.get("pai_celular"))[:20],
            # Mãe
            "mae_nome": _s(resp.get("mae_nome"))[:150],
            "mae_email": _s(resp.get("mae_email")),
            "mae_cpf": _s(resp.get("mae_cpf"))[:20],
            "mae_celular": _s(resp.get("mae_celular"))[:20],
            "mae_whatsapp": _s(resp.get("mae_celular"))[:20],
            # Responsável legal
            "resp_nome": (_s(resp.get("responsavel_nome")) or _s(resp.get("mae_nome")) or _s(resp.get("pai_nome")))[:150],
            "resp_parentesco": _s(resp.get("responsavel_parentesco"))[:50],
            "resp_cpf": _s(resp.get("responsavel_cpf"))[:20],
            "resp_email": _s(resp.get("responsavel_email")),
            "resp_whatsapp": resp_whats[:20],
            "cidade_inscricao": _s(resp.get("cidade"))[:100],
            "declaracao_medica_aceita": bool(av.get("declaracao_medica")),
            "autorizacao_imagem_aceita": bool(av.get("autorizacao_imagem")),
        }

    def _dados_ficha_medica(self, av):
        cond = av.get("condicoes") or {}
        aler = av.get("alergias") or {}
        doencas = set(av.get("doencas") or [])

        def _cond(chave):
            c = cond.get(chave, {})
            sim = c.get("resposta") == "sim"
            rem = _s(c.get("remedio")) if c.get("medicamento") == "sim" else ""
            return sim, rem[:200]

        def _aler(chave):
            a = aler.get(chave, {})
            return a.get("resposta") == "sim", _s(a.get("descricao"))[:200]

        cardiaco, cardiaco_med = _cond("cardiaco")
        diabetico, diabetico_med = _cond("diabetico")
        renais, renais_med = _cond("renal")
        psico, psico_med = _cond("psicologico")
        a_pele, a_pele_q = _aler("alergia_pele")
        a_alim, a_alim_q = _aler("alergia_alimento")
        a_med, a_med_q = _aler("alergia_medicamento")

        # Detalhes soltos (detalhe de condição + deficiências) -> outros_problemas.
        extras = []
        for chave, rotulo in [("cardiaco", "Cardíaco"), ("diabetico", "Diabetes"),
                              ("renal", "Renal"), ("psicologico", "Psicológico")]:
            det = _s(cond.get(chave, {}).get("detalhe"))
            if det:
                extras.append(f"{rotulo}: {det}")
        for d in (av.get("deficiencias") or []):
            if _s(d):
                extras.append(f"Deficiência: {_s(d)}")

        dados = {
            "possui_plano_saude": av.get("plano") == "sim",
            "qual_plano_saude": _s(av.get("plano_nome"))[:150],
            "cartao_sus": _s(av.get("cns"))[:50],
            "alergia_pele": a_pele, "alergia_pele_qual": a_pele_q,
            "alergia_alimentar": a_alim, "alergia_alimentar_qual": a_alim_q,
            "alergia_medicamentos": a_med, "alergia_medicamentos_qual": a_med_q,
            "cardiaco": cardiaco, "cardiaco_medicamentos": cardiaco_med,
            "diabetico": diabetico, "diabetico_medicamentos": diabetico_med,
            "renais": renais, "renais_medicamentos": renais_med,
            "psicologicos": psico, "psicologicos_medicamentos": psico_med,
            "outros_problemas": "\n".join(extras),
            "tipo_sanguineo": SANGUE_MAP.get(av.get("tipo_sangue"), ""),
        }
        for rotulo, campo in DOENCA_MAP.items():
            dados[campo] = rotulo in doencas
        return dados

    def _dados_autorizacao(self, av, resp):
        return {
            "nome_menor": _s(av.get("nome"))[:150],
            "nacionalidade_menor": "",
            "resp_nome": (_s(resp.get("responsavel_nome")) or _s(resp.get("mae_nome")) or _s(resp.get("pai_nome")))[:150],
            "resp_nacionalidade": "",
            "resp_estado_civil": "",
            "resp_rg": "",
            "resp_cpf": _s(resp.get("responsavel_cpf"))[:20],
            "resp_endereco": _s(resp.get("endereco"))[:200],
            "resp_numero": "",
            "resp_bairro": _s(resp.get("bairro"))[:100],
            "resp_cidade": _s(resp.get("cidade"))[:100],
            "resp_estado": _s(resp.get("estado"))[:50],
        }

    def _copiar_foto(self, origem, av, aventureiro):
        """Copia a foto para MEDIA_ROOT/aventureiros/fotos e ajusta o campo."""
        foto = av.get("foto") or {}
        exported = foto.get("exported_path")
        if not exported:
            return "sem foto"
        origem_arq = os.path.join(origem, exported.replace("/", os.sep))
        if not os.path.exists(origem_arq):
            return "arquivo ausente"
        ext = os.path.splitext(exported)[1] or ".png"
        nome_arq = f"av_{aventureiro.pk}{ext}"
        rel = f"{PASTA_FOTOS}/{nome_arq}"
        destino = os.path.join(settings.MEDIA_ROOT, PASTA_FOTOS, nome_arq)
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        shutil.copyfile(origem_arq, destino)
        aventureiro.foto.name = rel
        aventureiro.save(update_fields=["foto"])
        return "copiada"

    # -------------------------------------------------------------------- handle
    def handle(self, *args, **options):
        origem = options["origem"]
        dry = options["dry_run"]
        if not os.path.isdir(origem):
            raise CommandError(f"Pasta de origem não existe: {origem}")

        users = {u["id"]: u for u in self._carregar(origem, "dados_json/auth/user.json")}
        resps = {r["id"]: r for r in self._carregar(origem, "dados_json/accounts/responsavel.json")}
        aventureiros = self._carregar(origem, "dados_json/accounts/aventureiro.json")

        criados = pulados = fotos_ok = 0
        logins = set()
        avisos = []

        # Fora da transação quando dry-run (só leitura). Com transação no real.
        contexto = transaction.atomic() if not dry else _NoOp()
        with contexto:
            for av in aventureiros:
                if av["id"] == AVENTUREIRO_LIXO_ID:
                    continue
                resp = resps.get(av["responsavel"])
                if resp is None:
                    avisos.append(f"aventureiro {av['id']} sem responsável válido — pulado")
                    continue
                old_user = users.get(resp["user"])
                if old_user is None:
                    avisos.append(f"aventureiro {av['id']} sem login válido — pulado")
                    continue

                username = _s(old_user.get("username"))
                nome = _s(av.get("nome"))

                if dry:
                    logins.add(username)
                    existe = User.objects.filter(username=username).filter(
                        aventureiros__nome_completo=nome
                    ).exists()
                    if existe:
                        pulados += 1
                    else:
                        criados += 1
                        if (av.get("foto") or {}).get("exported_path"):
                            fotos_ok += 1
                    continue

                # 1) Login (reaproveita pelo username; preserva hash e datas).
                usuario, _u = User.objects.get_or_create(username=username)
                for campo, valor in self._dados_usuario(old_user).items():
                    setattr(usuario, campo, valor)
                usuario.save()
                logins.add(username)

                # 2) Aventureiro (pula se já existir mesmo user + mesmo nome).
                if usuario.aventureiros.filter(nome_completo=nome).exists():
                    pulados += 1
                    continue

                aventureiro = Aventureiro(usuario=usuario, **self._dados_aventureiro(av, resp))
                aventureiro.save()

                # Preserva a data de criação/inscrição original (auto_now_add).
                criado = parse_datetime(av["created_at"]) if av.get("created_at") else None
                if criado:
                    Aventureiro.objects.filter(pk=aventureiro.pk).update(
                        criado_em=criado, data_inscricao=criado.date()
                    )

                # 3) Ficha médica + 4) Termo de imagem.
                FichaMedica.objects.create(aventureiro=aventureiro, **self._dados_ficha_medica(av))
                AutorizacaoImagem.objects.create(aventureiro=aventureiro, **self._dados_autorizacao(av, resp))

                # 5) Foto.
                if self._copiar_foto(origem, av, aventureiro) == "copiada":
                    fotos_ok += 1

                criados += 1

        # ---- resumo ----
        prefixo = "[SIMULAÇÃO] " if dry else ""
        self.stdout.write(self.style.SUCCESS(f"{prefixo}Importação concluída."))
        self.stdout.write(f"Logins (contas): {len(logins)}")
        self.stdout.write(f"Aventureiros importados: {criados}")
        self.stdout.write(f"Aventureiros já existentes (pulados): {pulados}")
        self.stdout.write(f"Fotos copiadas: {fotos_ok}")
        if avisos:
            self.stdout.write(self.style.WARNING("Avisos:"))
            for a in avisos:
                self.stdout.write(f"- {a}")


class _NoOp:
    """Context manager vazio (para o modo dry-run, sem transação)."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False
