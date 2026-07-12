"""
Parser do payload do webhook da W-API (mensagens recebidas).

Portado do projeto BEEZAP (parser testado em produção) — o formato exato do
payload da W-API varia (W-API Lite, Baileys, grupos), então a extração é bem
defensiva: tenta vários caminhos e, por fim, uma busca recursiva. Sem dependência
nova. `parse_webhook_payload` devolve um dict simples (remetente, texto, etc.),
acrescido de `is_group`/`chat_id` para o módulo de liberação de números.
"""

# Chaves provaveis para busca recursiva (fallback), em ordem de preferencia.
EVENT_KEYS = ('event', 'type', 'eventtype', 'event_type', 'webhooktype')
PHONE_KEYS = (
    'participant', 'remotejid', 'senderphone', 'sendernumber',
    'phone', 'from', 'sender', 'chatid', 'jid', 'number', 'id',
)
NAME_KEYS = ('sendername', 'pushname', 'contactname', 'notifyname', 'name')
TEXT_KEYS = ('conversation', 'text', 'body', 'caption', 'content', 'message')


def _safe_get(payload, *paths):
    for path in paths:
        current = payload
        found = True
        for key in path:
            if isinstance(key, int):
                if isinstance(current, (list, tuple)) and -len(current) <= key < len(current):
                    current = current[key]
                else:
                    found = False
                    break
            elif isinstance(current, dict):
                current = current.get(key)
            else:
                found = False
                break
        if found and current not in (None, '') and not isinstance(current, (dict, list, tuple)):
            return current
    return None


def _as_text(value, default=''):
    if value in (None, ''):
        return default
    if isinstance(value, (dict, list, tuple)):
        return default
    return str(value).strip()


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ('true', '1', 'yes', 'sim')
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _only_digits(value):
    return ''.join(ch for ch in str(value) if ch.isdigit())


_NON_PERSONAL_JID_SUFFIXES = ('@g.us', '@lid', '@newsletter', '@broadcast')
_MAX_PHONE_DIGITS = 15


def normalize_phone(value):
    """Extrai só os dígitos do telefone (DDI+DDD+número). Vazio se for
    grupo/canal/transmissão/LID ou id interno longo demais para ser telefone."""
    text = _as_text(value)
    if not text:
        return ''
    low = text.lower()
    if any(suffix in low for suffix in _NON_PERSONAL_JID_SUFFIXES):
        return ''
    text = text.split('@', 1)[0].split(':', 1)[0]
    digits = _only_digits(text)
    if len(digits) < 8 or len(digits) > _MAX_PHONE_DIGITS:
        return ''
    return digits


def is_group_jid(value):
    """True para IDs de conversa coletiva/não-pessoal: grupo (@g.us), canal
    (@newsletter), transmissão (@broadcast) ou id numérico interno "pelado"."""
    text = _as_text(value).lower()
    if not text:
        return False
    if text.endswith('@g.us') or text.endswith('@newsletter') or text.endswith('@broadcast'):
        return True
    if '@' in text:
        return False
    return len(_only_digits(text)) > _MAX_PHONE_DIGITS


_BROADCAST_FLAG_PATHS = (
    ('broadcast',), ('isStatus',), ('is_status',), ('status',),
    ('data', 'broadcast'), ('data', 'isStatus'), ('data', 'is_status'),
    ('key', 'broadcast'), ('data', 'key', 'broadcast'),
    ('message', 'broadcast'), ('data', 'message', 'broadcast'),
)


def _deep_contains_status_broadcast(node, depth=0):
    if depth > 7:
        return False
    if isinstance(node, str):
        return 'status@broadcast' in node.lower()
    if isinstance(node, dict):
        return any(_deep_contains_status_broadcast(v, depth + 1) for v in node.values())
    if isinstance(node, (list, tuple)):
        return any(_deep_contains_status_broadcast(v, depth + 1) for v in node)
    return False


def _deep_contains_key(node, key_lower, depth=0):
    if depth > 7:
        return False
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(k, str) and k.lower() == key_lower:
                return True
            if _deep_contains_key(v, key_lower, depth + 1):
                return True
        return False
    if isinstance(node, (list, tuple)):
        return any(_deep_contains_key(v, key_lower, depth + 1) for v in node)
    return False


_STATUS_CHAT_PATHS = (
    ('chat', 'id'), ('data', 'chat', 'id'),
    ('chatId',), ('data', 'chatId'),
    ('remoteJid',), ('data', 'remoteJid'),
    ('key', 'remoteJid'), ('data', 'key', 'remoteJid'),
)
_STATUS_MARKER_KEYS = ('posterstatusid',)


def is_status_or_broadcast(payload):
    """True quando o payload é atualização de STATUS/transmissão (ignorar)."""
    if not isinstance(payload, dict):
        return False
    for path in _STATUS_CHAT_PATHS:
        v = _as_text(_safe_get(payload, path)).lower()
        if v == 'status' or v.endswith('@broadcast'):
            return True
    for path in _BROADCAST_FLAG_PATHS:
        if _as_bool(_safe_get(payload, path)):
            return True
    if any(_deep_contains_key(payload, k) for k in _STATUS_MARKER_KEYS):
        return True
    return _deep_contains_status_broadcast(payload)


def _deep_find(node, target_keys, validate):
    for target in target_keys:
        found = _deep_find_key(node, target, validate)
        if found not in (None, ''):
            return found
    return None


def _deep_find_key(node, target_key, validate):
    if isinstance(node, dict):
        for key, value in node.items():
            if (
                isinstance(key, str)
                and key.lower() == target_key
                and not isinstance(value, (dict, list, tuple))
                and value not in (None, '')
                and validate(value)
            ):
                return value
        for value in node.values():
            found = _deep_find_key(value, target_key, validate)
            if found not in (None, ''):
                return found
    elif isinstance(node, (list, tuple)):
        for item in node:
            found = _deep_find_key(item, target_key, validate)
            if found not in (None, ''):
                return found
    return None


def _valid_any(value):
    return value not in (None, '')


def _valid_phone(value):
    return len(normalize_phone(value)) >= 8


def _valid_text(value):
    return isinstance(value, str) and bool(value.strip())


def _valid_name(value):
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return False
    if len(_only_digits(text)) >= 8:
        return False
    return any(ch.isalnum() for ch in text)


# Caminhos onde vem o id da conversa (chat) — para detectar grupo × direta.
_CHAT_ID_PATHS = (
    ('chat', 'id'), ('data', 'chat', 'id'),
    ('chatId',), ('data', 'chatId'),
    ('data', 'key', 'remoteJid'), ('key', 'remoteJid'),
    ('remoteJid',), ('data', 'remoteJid'),
)


def parse_webhook_payload(payload):
    """Extrai os campos úteis do payload da W-API. Devolve dict com:
    event_type, instance_id, phone (remetente, só dígitos), contact_name,
    message_id, message_type, message_text, from_me (bool), is_group (bool),
    chat_id."""
    if not isinstance(payload, dict):
        payload = {}

    event_type = _safe_get(
        payload,
        ('event',), ('eventType',), ('event_type',), ('webhookType',), ('type',),
        ('data', 'event'), ('data', 'eventType'), ('data', 'type'),
    ) or _deep_find(payload, EVENT_KEYS, _valid_any)

    instance_id = _safe_get(
        payload,
        ('instanceId',), ('instance_id',), ('instance', 'id'),
        ('data', 'instanceId'), ('data', 'instance', 'id'),
    )

    phone = ''
    for phone_path in (
        ('sender', 'id'), ('sender', 'phone'), ('sender', 'number'),
        ('data', 'sender', 'id'), ('data', 'sender', 'phone'), ('data', 'sender', 'number'),
        ('data', 'key', 'participant'), ('data', 'key', 'remoteJid'),
        ('data', 'participant'), ('data', 'remoteJid'), ('data', 'from'), ('data', 'sender'),
        ('data', 'senderPhone'), ('data', 'senderNumber'), ('data', 'chatId'),
        ('data', 'phone'), ('data', 'number'), ('data', 'jid'),
        ('data', 'contact', 'phone'), ('data', 'contact', 'number'), ('data', 'contact', 'id'),
        ('data', 'message', 'from'), ('data', 'message', 'sender'), ('data', 'message', 'remoteJid'),
        ('key', 'participant'), ('key', 'remoteJid'),
        ('phone',), ('from',), ('sender',), ('senderPhone',), ('senderNumber',),
        ('remoteJid',), ('participant',), ('jid',), ('number',), ('chatId',),
        ('chat', 'id'), ('data', 'chat', 'id'),
        ('contact', 'phone'), ('contact', 'number'), ('contact', 'id'),
        ('messages', 0, 'key', 'participant'), ('messages', 0, 'key', 'remoteJid'),
        ('data', 'messages', 0, 'key', 'participant'), ('data', 'messages', 0, 'key', 'remoteJid'),
    ):
        candidate = normalize_phone(_safe_get(payload, phone_path))
        if candidate:
            phone = candidate
            break
    if not phone:
        phone = normalize_phone(_deep_find(payload, PHONE_KEYS, _valid_phone))

    contact_name = _safe_get(
        payload,
        ('senderName',), ('pushName',), ('contactName',), ('notifyName',), ('name',),
        ('contact', 'name'), ('contact', 'pushName'),
        ('data', 'senderName'), ('data', 'pushName'), ('data', 'contactName'),
        ('data', 'notifyName'), ('data', 'name'),
        ('data', 'contact', 'name'), ('data', 'contact', 'pushName'),
        ('messages', 0, 'pushName'), ('data', 'messages', 0, 'pushName'),
    )
    if not _valid_name(contact_name):
        contact_name = _deep_find(payload, NAME_KEYS, _valid_name) or contact_name

    message_id = _safe_get(
        payload,
        ('messageId',), ('message_id',), ('id',),
        ('data', 'messageId'), ('data', 'message_id'), ('data', 'id'),
        ('message', 'id'), ('data', 'message', 'id'),
        ('key', 'id'), ('data', 'key', 'id'),
        ('messages', 0, 'key', 'id'), ('data', 'messages', 0, 'key', 'id'),
    )

    message_type = _safe_get(
        payload,
        ('messageType',), ('message_type',), ('typeMessage',),
        ('data', 'messageType'), ('data', 'message_type'), ('data', 'typeMessage'),
        ('message', 'type'), ('data', 'message', 'type'),
    )

    message_text = _safe_get(
        payload,
        ('text',), ('body',), ('content',), ('caption',), ('message',),
        ('data', 'text'), ('data', 'body'), ('data', 'content'), ('data', 'caption'),
        ('data', 'message', 'text'), ('data', 'message', 'body'), ('data', 'message', 'conversation'),
        ('data', 'message', 'extendedTextMessage', 'text'),
        ('data', 'message', 'imageMessage', 'caption'), ('data', 'message', 'videoMessage', 'caption'),
        ('message', 'text'), ('message', 'body'), ('message', 'conversation'),
        ('message', 'extendedTextMessage', 'text'), ('message', 'imageMessage', 'caption'),
        ('textMessage', 'text'), ('data', 'textMessage', 'text'),
        ('messages', 0, 'message', 'conversation'),
        ('messages', 0, 'message', 'extendedTextMessage', 'text'),
        ('data', 'messages', 0, 'message', 'conversation'),
        ('data', 'messages', 0, 'message', 'extendedTextMessage', 'text'),
    )
    if not _valid_text(message_text):
        message_text = _deep_find(payload, TEXT_KEYS, _valid_text) or message_text

    from_me = _safe_get(
        payload,
        ('fromMe',), ('from_me',), ('data', 'fromMe'), ('data', 'from_me'),
        ('key', 'fromMe'), ('data', 'key', 'fromMe'),
        ('message', 'fromMe'), ('data', 'message', 'fromMe'),
        ('messages', 0, 'key', 'fromMe'), ('data', 'messages', 0, 'key', 'fromMe'),
    )

    chat_id = _as_text(_safe_get(payload, *_CHAT_ID_PATHS))
    is_group = _as_bool(_safe_get(payload, ('isGroup',), ('data', 'isGroup'))) or is_group_jid(chat_id)

    return {
        'event_type': _as_text(event_type, 'unknown') or 'unknown',
        'instance_id': _as_text(instance_id),
        'phone': phone,
        'contact_name': _as_text(contact_name),
        'message_id': _as_text(message_id),
        'message_type': _as_text(message_type, 'unknown') or 'unknown',
        'message_text': _as_text(message_text),
        'from_me': _as_bool(from_me),
        'is_group': is_group,
        'chat_id': chat_id,
    }
