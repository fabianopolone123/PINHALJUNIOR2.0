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


def enviar(config, destino, assunto, corpo):
    """Envia UM e-mail de texto simples e devolve `(ok: bool, detalhe: str)`.

    `detalhe` é "enviado" no sucesso ou uma mensagem de erro amigável na falha.
    Contabiliza o resultado no contador do `EmailConfig`. Não levanta exceção."""
    if not getattr(config, "configurado", False):
        return False, "E-mail não configurado."
    destino = (destino or "").strip()
    if not destino or "@" not in destino:
        return False, "Endereço de destino inválido."
    if not (corpo or "").strip():
        return False, "Mensagem vazia."

    try:
        msg = EmailMessage(
            subject=(assunto or "").strip() or "(sem assunto)",
            body=corpo,
            from_email=config.remetente,
            to=[destino],
            connection=_conexao(config),
        )
        msg.send(fail_silently=False)
    except Exception as exc:  # noqa: BLE001 — envio nunca derruba o fluxo do chamador
        erro = f"{type(exc).__name__}: {exc}"
        logger.warning("Falha ao enviar e-mail para %s: %s", destino, erro)
        try:
            config.registrar_falha(erro)
        except Exception:  # noqa: BLE001 — contador nunca atrapalha o retorno
            logger.exception("Falha ao registrar erro de e-mail")
        return False, _amigavel(exc)

    try:
        config.registrar_envio()
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao registrar envio de e-mail")
    return True, "enviado"


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
