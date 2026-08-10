"""
Phase 6 — Telegram Notification Tests
Tests TelegramProvider, get_notifier factory, and AlertCreate validation.
All tests use mocked HTTP — no real Telegram API calls.
"""
import pytest
import os
from unittest.mock import patch, MagicMock


# --------------------------------------------------------------------------- #
# 1. TelegramProvider Tests
# --------------------------------------------------------------------------- #

class TestTelegramProvider:
    """Tests for TelegramProvider in backend/notifications.py"""

    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token-123"})
    @patch("backend.notifications.requests.post")
    def test_send_alert_success(self, mock_post):
        """TelegramProvider returns True on successful Telegram API response."""
        from backend.notifications import TelegramProvider

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True, "result": {"message_id": 1}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        provider = TelegramProvider()
        result = provider.send_alert("123456789", "Test message")

        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["chat_id"] == "123456789"
        assert call_kwargs[1]["json"]["text"] == "Test message"

    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token-123"})
    @patch("backend.notifications.requests.post")
    def test_send_alert_http_failure(self, mock_post):
        """TelegramProvider returns False on HTTP error."""
        from backend.notifications import TelegramProvider
        import requests

        mock_post.side_effect = requests.exceptions.HTTPError("500 Server Error")

        provider = TelegramProvider()
        result = provider.send_alert("123456789", "Test message")

        assert result is False

    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token-123"})
    @patch("backend.notifications.requests.post")
    def test_send_alert_telegram_api_ok_false(self, mock_post):
        """TelegramProvider returns False when Telegram API returns ok=false."""
        from backend.notifications import TelegramProvider

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": False, "description": "Bad Request: chat not found"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        provider = TelegramProvider()
        result = provider.send_alert("invalid_chat", "Test message")

        assert result is False

    @patch.dict(os.environ, {}, clear=True)
    def test_send_alert_missing_bot_token(self):
        """TelegramProvider returns False when TELEGRAM_BOT_TOKEN is absent."""
        # Remove any inherited env
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        from backend.notifications import TelegramProvider

        provider = TelegramProvider()
        result = provider.send_alert("123456789", "Test message")

        assert result is False

    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token-123"})
    def test_send_alert_missing_chat_id(self):
        """TelegramProvider returns False when chat_id is empty and no default configured."""
        os.environ.pop("TELEGRAM_DEFAULT_CHAT_ID", None)
        from backend.notifications import TelegramProvider

        provider = TelegramProvider()
        result = provider.send_alert("", "Test message")

        assert result is False

    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token-123"})
    @patch("backend.notifications.requests.post")
    def test_send_alert_timeout(self, mock_post):
        """TelegramProvider returns False on request timeout."""
        from backend.notifications import TelegramProvider
        import requests

        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")

        provider = TelegramProvider()
        result = provider.send_alert("123456789", "Test message")

        assert result is False

    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token-123", "TELEGRAM_DEFAULT_CHAT_ID": "default123"})
    @patch("backend.notifications.requests.post")
    def test_send_alert_uses_default_chat_id(self, mock_post):
        """TelegramProvider falls back to TELEGRAM_DEFAULT_CHAT_ID when no chat_id given."""
        from backend.notifications import TelegramProvider

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True, "result": {"message_id": 1}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        provider = TelegramProvider()
        result = provider.send_alert("", "Test message")

        assert result is True
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["chat_id"] == "default123"


# --------------------------------------------------------------------------- #
# 2. get_notifier Factory Tests
# --------------------------------------------------------------------------- #

class TestGetNotifier:
    """Tests for the get_notifier() factory function."""

    def test_get_notifier_telegram(self):
        """get_notifier('telegram') returns TelegramProvider."""
        from backend.notifications import get_notifier, TelegramProvider

        notifier = get_notifier("telegram")
        assert isinstance(notifier, TelegramProvider)

    def test_get_notifier_whatsapp(self):
        """get_notifier('whatsapp') returns TwilioSandboxProvider."""
        from backend.notifications import get_notifier, TwilioSandboxProvider

        notifier = get_notifier("whatsapp")
        assert isinstance(notifier, TwilioSandboxProvider)

    def test_get_notifier_unsupported_channel(self):
        """get_notifier() raises ValueError for unsupported channels."""
        from backend.notifications import get_notifier

        with pytest.raises(ValueError, match="Unsupported notification channel"):
            get_notifier("email")

    def test_get_notifier_empty_channel(self):
        """get_notifier() raises ValueError for empty string."""
        from backend.notifications import get_notifier

        with pytest.raises(ValueError, match="Unsupported notification channel"):
            get_notifier("")


# --------------------------------------------------------------------------- #
# 3. AlertCreate Pydantic Model Tests
# --------------------------------------------------------------------------- #

class TestAlertCreate:
    """Tests for the AlertCreate Pydantic model validation."""

    def test_valid_whatsapp_alert(self):
        """AlertCreate accepts valid WhatsApp payload."""
        from backend.api_routes import AlertCreate

        alert = AlertCreate(
            threshold_price=25000.0,
            notification_channel="whatsapp",
            phone_number="+919876543210"
        )
        assert alert.notification_channel == "whatsapp"
        assert alert.phone_number == "+919876543210"
        assert alert.threshold_price == 25000.0

    def test_valid_telegram_alert(self):
        """AlertCreate accepts valid Telegram payload."""
        from backend.api_routes import AlertCreate

        alert = AlertCreate(
            threshold_price=15000.0,
            notification_channel="telegram",
            telegram_chat_id="123456789"
        )
        assert alert.notification_channel == "telegram"
        assert alert.telegram_chat_id == "123456789"
        assert alert.threshold_price == 15000.0

    def test_whatsapp_default_channel(self):
        """AlertCreate defaults to 'whatsapp' when notification_channel is omitted."""
        from backend.api_routes import AlertCreate

        alert = AlertCreate(
            threshold_price=10000.0,
            phone_number="+919876543210"
        )
        assert alert.notification_channel == "whatsapp"

    def test_reject_unsupported_channel(self):
        """AlertCreate rejects unsupported notification channel."""
        from backend.api_routes import AlertCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AlertCreate(
                threshold_price=10000.0,
                notification_channel="email",
                phone_number="+919876543210"
            )

    def test_telegram_without_chat_id_model_accepts(self):
        """
        AlertCreate model-level validation allows telegram_chat_id=None.
        The endpoint-level validation enforces the requirement.
        """
        from backend.api_routes import AlertCreate

        alert = AlertCreate(
            threshold_price=10000.0,
            notification_channel="telegram"
        )
        assert alert.telegram_chat_id is None

    def test_whatsapp_without_phone_model_accepts(self):
        """
        AlertCreate model-level validation allows phone_number=None.
        The endpoint-level validation enforces the requirement.
        """
        from backend.api_routes import AlertCreate

        alert = AlertCreate(
            threshold_price=10000.0,
            notification_channel="whatsapp"
        )
        assert alert.phone_number is None

    def test_existing_whatsapp_behavior_preserved(self):
        """Existing WhatsApp alert creation pattern still works."""
        from backend.api_routes import AlertCreate

        # Original payload format still works
        alert = AlertCreate(
            phone_number="+919876543210",
            threshold_price=20000.0
        )
        assert alert.notification_channel == "whatsapp"
        assert alert.phone_number == "+919876543210"
        assert alert.threshold_price == 20000.0


# --------------------------------------------------------------------------- #
# 4. SUPPORTED_CHANNELS constant test
# --------------------------------------------------------------------------- #

class TestSupportedChannels:
    """Tests for the SUPPORTED_CHANNELS constant."""

    def test_supported_channels_contains_whatsapp(self):
        from backend.notifications import SUPPORTED_CHANNELS
        assert "whatsapp" in SUPPORTED_CHANNELS

    def test_supported_channels_contains_telegram(self):
        from backend.notifications import SUPPORTED_CHANNELS
        assert "telegram" in SUPPORTED_CHANNELS

    def test_supported_channels_no_extras(self):
        from backend.notifications import SUPPORTED_CHANNELS
        assert len(SUPPORTED_CHANNELS) == 2
