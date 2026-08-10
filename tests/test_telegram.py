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


# --------------------------------------------------------------------------- #
# 5. Phase 6.1 Alert Creation Confirmation Tests
# --------------------------------------------------------------------------- #

class TestAlertConfirmation:
    """Tests for Phase 6.1 immediate alert confirmation delivery."""

    def test_build_alert_confirmation_message_telegram(self):
        """Message builder formats HTML confirmation message for Telegram."""
        from backend.notifications import build_alert_confirmation_message

        msg = build_alert_confirmation_message(
            product_title="Sony WH-1000XM5",
            platform="amazon",
            threshold_price=20000.0,
            current_price=24999.0,
            channel="telegram"
        )
        assert "Sony WH-1000XM5" in msg
        assert "₹20,000.00" in msg
        assert "Amazon" in msg
        assert "₹24,999.00" in msg
        assert "Telegram" in msg

    def test_build_alert_confirmation_message_no_price(self):
        """Message builder handles missing current_price with fallback."""
        from backend.notifications import build_alert_confirmation_message

        msg = build_alert_confirmation_message(
            product_title="Logitech MX Master 3S",
            platform="flipkart",
            threshold_price=5000.0,
            current_price=None,
            channel="telegram"
        )
        assert "Not available yet" in msg
        assert "Logitech MX Master 3S" in msg
        assert "₹5,000.00" in msg

    @patch("backend.api_routes.get_notifier")
    def test_create_alert_sends_telegram_confirmation(self, mock_get_notifier):
        """create_alert() sends immediate Telegram confirmation to chat ID after DB commit."""
        from backend.database import Base, engine, SessionLocal
        from backend.models import User, Product, AlertThreshold
        from backend.api_routes import create_alert, AlertCreate
        from unittest.mock import MagicMock
        from starlette.requests import Request
        import uuid

        Base.metadata.create_all(bind=engine)
        db = SessionLocal()

        try:
            # Create user & product
            email = f"confirm_{uuid.uuid4().hex[:6]}@example.com"
            user = User(name="Test User", email=email, password_hash="hash")
            db.add(user)
            db.commit()
            db.refresh(user)

            prod = Product(user_id=user.id, url=f"https://www.amazon.in/dp/B0{uuid.uuid4().hex[:6]}", title="Test Headphones", platform="amazon")
            db.add(prod)
            db.commit()
            db.refresh(prod)

            mock_notifier = MagicMock()
            mock_notifier.send_alert.return_value = True
            mock_get_notifier.return_value = mock_notifier

            mock_req = Request({"type": "http", "path": "/products/1/alerts", "client": ("127.0.0.1", 12345), "headers": []})

            payload = AlertCreate(
                threshold_price=700.0,
                notification_channel="telegram",
                telegram_chat_id="8010225684"
            )

            res = create_alert(request=mock_req, product_id=prod.id, alert=payload, current_user=user, db=db)

            # Assert DB record exists and is Active
            alert_db = db.query(AlertThreshold).filter(AlertThreshold.id == res["id"]).first()
            assert alert_db is not None
            assert alert_db.status == "ACTIVE"
            assert alert_db.telegram_chat_id == "8010225684"

            # Assert confirmation was sent to chat_id
            mock_get_notifier.assert_called_once_with("telegram")
            mock_notifier.send_alert.assert_called_once()
            call_args = mock_notifier.send_alert.call_args
            assert call_args[0][0] == "8010225684"
            assert "Test Headphones" in call_args[0][1]
            assert "700.00" in call_args[0][1]
            assert res["confirmation_sent"] is True
        finally:
            db.close()

    @patch("backend.api_routes.get_notifier")
    def test_create_alert_delivery_failure_does_not_rollback_db(self, mock_get_notifier):
        """Telegram confirmation failure leaves alert record active in DB."""
        from backend.database import Base, engine, SessionLocal
        from backend.models import User, Product, AlertThreshold
        from backend.api_routes import create_alert, AlertCreate
        from unittest.mock import MagicMock
        from starlette.requests import Request
        import uuid

        Base.metadata.create_all(bind=engine)
        db = SessionLocal()

        try:
            email = f"confirm_fail_{uuid.uuid4().hex[:6]}@example.com"
            user = User(name="Test User 2", email=email, password_hash="hash")
            db.add(user)
            db.commit()

            prod = Product(user_id=user.id, url=f"https://www.amazon.in/dp/B0{uuid.uuid4().hex[:6]}", title="Fail Product", platform="amazon")
            db.add(prod)
            db.commit()

            mock_notifier = MagicMock()
            mock_notifier.send_alert.return_value = False  # Delivery fails (e.g. unconfigured token)
            mock_get_notifier.return_value = mock_notifier

            mock_req = Request({"type": "http", "path": "/products/1/alerts", "client": ("127.0.0.1", 12345), "headers": []})

            payload = AlertCreate(
                threshold_price=500.0,
                notification_channel="telegram",
                telegram_chat_id="8010225684"
            )

            res = create_alert(request=mock_req, product_id=prod.id, alert=payload, current_user=user, db=db)

            # Alert record MUST still exist in database
            alert_db = db.query(AlertThreshold).filter(AlertThreshold.id == res["id"]).first()
            assert alert_db is not None
            assert alert_db.status == "ACTIVE"
            assert res["confirmation_sent"] is False
        finally:
            db.close()

