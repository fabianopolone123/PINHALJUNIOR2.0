"""
Cliente de envio de e-mail (SMTP).

Segundo canal de notificação, ao lado do WhatsApp (`core/wapi.py`). Diferente das
outras integrações — que falam HTTP via `urllib` — aqui o próprio Django já traz o
que precisamos (`django.core.mail`), então **não há dependência nova**: montamos a
conexão SMTP na mão a partir do `EmailConfig` da tela, sem depender das variáveis
`EMAIL_*` do settings.

Ponto de entrada: `enviar(config, destino, assunto, corpo)` → `(ok, detalhe)`.
Nunca levanta exceção; qualquer falha vira uma mensagem amigável e é contabilizada
no contador do `EmailConfig`. Mesmo contrato de retorno do `_enviar_whatsapp`, para
o despachante de notificações tratar os dois canais igual.
"""

import logging

from django.core.mail import EmailMessage, get_connection

logger = logging.getLogger(__name__)

TIMEOUT = 20  # segundos — SMTP trava fácil; o envio roda em thread, mas com limite

BACKEND_SMTP = "django.core.mail.backends.smtp.EmailBackend"


def _conexao(config):
    """Monta a conexão SMTP a partir do `EmailConfig` (nunca do settings).

    `use_tls` e `use_ssl` são mutuamente exclusivos no Django — por isso a
    `seguranca` da tela é traduzida aqui num par coerente."""
    from .models import EmailConfig

    return get_connection(
        backend=BACKEND_SMTP,
        host=config.host,
        port=config.porta,
        username=config.usuario,
        # O Gmail exibe a senha de app em grupos de 4 separados por espaço, e o
        # usuário costuma colar assim; o servidor não aceita os espaços.
        password=(config.senha or "").replace(" ", ""),
        use_tls=config.seguranca == EmailConfig.SEGURANCA_TLS,
        use_ssl=config.seguranca == EmailConfig.SEGURANCA_SSL,
        timeout=TIMEOUT,
        fail_silently=False,
    )


def link_descadastro(config, contato):
    """URL pública de descadastro de um contato (vazia se não der para montar).

    Usa `EmailConfig.site_url` em vez de `request.build_absolute_uri` porque as
    notificações saem em thread de fundo, onde não existe request."""
    base = (getattr(config, "site_url", "") or "").rstrip("/")
    token = getattr(contato, "token", "") if contato else ""
    if not base or not token:
        return ""
    return f"{base}/descadastrar/{token}/"


def _montar_corpo(config, corpo, url_saida):
    """Junta o corpo ao rodapé de identificação e, quando houver, à linha de
    descadastro. Identificar o remetente e oferecer saída são os dois sinais que
    mais pesam contra a marcação de spam em mensagem não solicitada."""
    partes = [(corpo or "").rstrip()]
    rodape = (getattr(config, "rodape", "") or "").strip()
    extras = []
    if rodape:
        extras.append(rodape)
    if url_saida:
        extras.append(f"Para não receber mais estes avisos: {url_saida}")
    if extras:
        partes.append("-- \n" + "\n".join(extras))
    return "\n\n".join(partes)


def _registrar_log(destino, assunto, ok, detalhe, origem):
    """Grava a linha do extrato da tela. Isolado para nunca atrapalhar o envio."""
    from .models import LogEmail

    LogEmail.registrar(destino, assunto, ok, detalhe, origem)


def enviar(config, destino, assunto, corpo, *, contato=None, transacional=False, origem=""):
    """Envia UM e-mail de texto simples e devolve `(ok: bool, detalhe: str)`.

    `detalhe` é "enviado" no sucesso ou uma mensagem de erro amigável na falha.
    Contabiliza o resultado no `EmailConfig` e, quando `contato` é passado, também
    nele — inclusive marcando **bounce** se o servidor recusar o endereço, para não
    insistir num endereço morto (o que derruba a reputação do remetente).

    `transacional=True` (confirmação do que a própria pessoa acabou de fazer) omite
    o convite de descadastro e o cabeçalho `List-Unsubscribe`: não faz sentido
    oferecer saída de um comprovante. Para todo o resto eles vão — Gmail e Outlook
    esperam esse cabeçalho de quem manda aviso não solicitado.

    Não levanta exceção."""
    if not getattr(config, "configurado", False):
        return False, "E-mail não configurado."
    destino = (destino or "").strip()
    if not destino or "@" not in destino:
        return False, "Endereço de destino inválido."
    if not (corpo or "").strip():
        return False, "Mensagem vazia."
    assunto_final = (assunto or "").strip() or "(sem assunto)"

    url_saida = "" if transacional else link_descadastro(config, contato)
    cabecalhos = {}
    if url_saida:
        # RFC 8058: com o par abaixo, o próprio Gmail/Outlook mostra o botão
        # "Cancelar inscrição" e o clique chega no nosso endpoint.
        cabecalhos["List-Unsubscribe"] = f"<{url_saida}>"
        cabecalhos["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

    reply_to = (getattr(config, "reply_to", "") or "").strip()

    try:
        msg = EmailMessage(
            subject=assunto_final,
            body=_montar_corpo(config, corpo, url_saida),
            from_email=config.remetente,
            to=[destino],
            reply_to=[reply_to] if reply_to else None,
            headers=cabecalhos or None,
            connection=_conexao(config),
        )
        msg.send(fail_silently=False)
    except Exception as exc:  # noqa: BLE001 — envio nunca derruba o fluxo do chamador
        erro = f"{type(exc).__name__}: {exc}"
        logger.warning("Falha ao enviar e-mail para %s: %s", destino, erro)
        amigavel = _amigavel(exc)
        try:
            config.registrar_falha(erro)
            if contato is not None and _eh_recusa_definitiva(exc):
                contato.registrar_bounce(erro)
        except Exception:  # noqa: BLE001 — contador nunca atrapalha o retorno
            logger.exception("Falha ao registrar erro de e-mail")
        _registrar_log(destino, assunto_final, False, amigavel, origem)
        return False, amigavel

    try:
        config.registrar_envio()
        if contato is not None:
            contato.registrar_envio()
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao registrar envio de e-mail")
    _registrar_log(destino, assunto_final, True, "enviado", origem)
    return True, "enviado"


def _eh_recusa_definitiva(exc):
    """True se o servidor recusou o ENDEREÇO (bounce permanente) — caso em que o
    contato deve ser suprimido. Falha de conexão/autenticação é problema nosso, não
    do endereço, e não pode marcar bounce."""
    import smtplib

    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return True
    codigo = getattr(exc, "smtp_code", None)
    # 5xx = erro permanente. 4xx é temporário (greylisting, caixa cheia) e merece
    # nova tentativa depois, então não suprime.
    return isinstance(codigo, int) and 500 <= codigo < 600


def _amigavel(exc):
    """Traduz as falhas mais comuns de SMTP para algo acionável na tela."""
    import smtplib

    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return (
            "O servidor recusou a conta ou a senha. No Gmail é preciso usar uma "
            "senha de app (com a verificação em duas etapas ligada), não a senha "
            "normal da conta."
        )
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "O servidor recusou o endereço de destino."
    if isinstance(exc, smtplib.SMTPSenderRefused):
        return "O servidor recusou o remetente. Confira a conta configurada."
    if isinstance(exc, smtplib.SMTPConnectError):
        return "Não foi possível conectar ao servidor SMTP. Confira o host e a porta."
    if isinstance(exc, (TimeoutError, OSError)):
        return (
            "Falha de conexão com o servidor SMTP (tempo esgotado). Confira o host, "
            "a porta e se a saída SMTP está liberada."
        )
    return f"Não foi possível enviar: {exc}"
