"""Tests de parseo de payloads de WhatsApp e Instagram.

Estos tests son puramente unitarios: no tocan BD, Redis ni APIs externas.
"""
from app.workers.instagram import _extract_dm
from app.workers.whatsapp import _extract_message


# ─────────────────────────────────────────────────────────────────────────────
# WhatsApp Cloud API
# ─────────────────────────────────────────────────────────────────────────────

WA_TEXT = {
    "entry": [{
        "changes": [{
            "value": {
                "messages": [{
                    "id": "wamid.TEST001",
                    "from": "56912345678",
                    "type": "text",
                    "text": {"body": "Hola, necesito ayuda"},
                }],
                "metadata": {"phone_number_id": "PN_ABC"},
                "contacts": [{"profile": {"name": "Ana García"}}],
            }
        }]
    }]
}

WA_IMAGE = {
    "entry": [{
        "changes": [{
            "value": {
                "messages": [{
                    "id": "wamid.IMG001",
                    "from": "56900000000",
                    "type": "image",
                    "image": {"id": "img123"},
                }],
                "metadata": {"phone_number_id": "PN_ABC"},
                # sin contacts → usa default [{}] del parser
            }
        }]
    }]
}


class TestExtractWhatsappMessage:
    def test_text_message_parsed_correctly(self):
        msg = _extract_message(WA_TEXT)
        assert msg is not None
        assert msg["wamid"] == "wamid.TEST001"
        assert msg["from_wa_id"] == "56912345678"
        assert msg["text"] == "Hola, necesito ayuda"
        assert msg["msg_type"] == "text"
        assert msg["phone_number_id"] == "PN_ABC"
        assert msg["contact_name"] == "Ana García"

    def test_image_message_parsed(self):
        """Mensajes no-texto se parsean (el worker los filtra después)."""
        msg = _extract_message(WA_IMAGE)
        assert msg is not None
        assert msg["msg_type"] == "image"
        assert msg["text"] == ""

    def test_empty_payload_returns_none(self):
        assert _extract_message({}) is None

    def test_missing_entry_returns_none(self):
        assert _extract_message({"entry": []}) is None

    def test_missing_messages_returns_none(self):
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "PN_ABC"},
                    }
                }]
            }]
        }
        assert _extract_message(payload) is None

    def test_no_contact_name_returns_none(self):
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{"id": "w1", "from": "56900000001", "type": "text",
                                      "text": {"body": "test"}}],
                        "metadata": {"phone_number_id": "PN_XYZ"},
                        # sin contacts
                    }
                }]
            }]
        }
        msg = _extract_message(payload)
        assert msg is not None
        assert msg["contact_name"] is None


# ─────────────────────────────────────────────────────────────────────────────
# Instagram Messaging API
# ─────────────────────────────────────────────────────────────────────────────

IG_DM = {
    "entry": [{
        "id": "IG_BIZ_001",
        "messaging": [{
            "sender": {"id": "USER_IGSID_999"},
            "recipient": {"id": "IG_BIZ_001"},
            "message": {"mid": "mid.XYZ", "text": "Hola desde Instagram"},
        }]
    }]
}

IG_ECHO = {
    "entry": [{
        "id": "IG_BIZ_001",
        "messaging": [{
            "sender": {"id": "IG_BIZ_001"},      # mismo ID → eco saliente
            "recipient": {"id": "IG_BIZ_001"},
            "message": {"mid": "mid.ECO", "text": "respuesta que enviamos nosotros"},
        }]
    }]
}

IG_NO_TEXT = {
    "entry": [{
        "id": "IG_BIZ_001",
        "messaging": [{
            "sender": {"id": "USER_000"},
            "recipient": {"id": "IG_BIZ_001"},
            "message": {"mid": "mid.STICKER"},    # sticker, sin campo text
        }]
    }]
}


class TestExtractInstagramDM:
    def test_dm_parsed_correctly(self):
        dm = _extract_dm(IG_DM)
        assert dm is not None
        assert dm["ig_user_id"] == "IG_BIZ_001"
        assert dm["sender_igsid"] == "USER_IGSID_999"
        assert dm["text"] == "Hola desde Instagram"
        assert dm["mid"] == "mid.XYZ"

    def test_echo_message_ignored(self):
        """Mensajes enviados por nuestra propia cuenta no deben procesarse."""
        assert _extract_dm(IG_ECHO) is None

    def test_empty_payload_returns_none(self):
        assert _extract_dm({}) is None

    def test_missing_messaging_returns_none(self):
        assert _extract_dm({"entry": [{"id": "X"}]}) is None

    def test_no_text_returns_empty_string(self):
        """Mensajes sin campo text (stickers, reacciones) retornan texto vacío."""
        dm = _extract_dm(IG_NO_TEXT)
        assert dm is not None
        assert dm["text"] == ""
