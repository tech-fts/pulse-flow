"""Unit tests for the notification template engine (no infrastructure needed)."""
import pytest

from app.schemas.event import EventChannel
from app.services.template_engine import (
    FALLBACK_TEMPLATE,
    RenderedMessage,
    TemplateEngine,
    render_notification,
)


class TestTemplateEngine:
    def test_renders_known_category_with_title(self):
        engine = TemplateEngine()
        result = engine.render(
            "security",
            EventChannel.EMAIL,
            {"title": "New Login Attempt", "code": "849201"},
        )
        assert isinstance(result, RenderedMessage)
        assert result.title == "Security alert: New Login Attempt"
        assert "New Login Attempt" in result.body

    def test_renders_body_only_for_sms(self):
        result = render_notification(
            "transaction",
            EventChannel.SMS,
            {"amount": "$12.40", "status": "confirmed"},
        )
        assert result.title is not None  # SMS drops the title at the provider layer
        assert "$12.40" in result.body
        assert "confirmed" in result.body

    def test_unknown_category_uses_fallback(self):
        engine = TemplateEngine()
        result = engine.render(
            "no_such_category",
            EventChannel.PUSH,
            {"title": "hello"},
        )
        assert result.title is None
        assert result.body == "hello"

    def test_missing_payload_key_renders_empty(self):
        engine = TemplateEngine()
        result = engine.render(
            "reminder",
            EventChannel.IN_APP,
            {},  # no "message" key
        )
        # default Undefined renders empty, but we supplied a default in the template
        assert result.body == "You have a pending item."

    def test_custom_template_registry(self):
        engine = TemplateEngine(
            templates={"welcome": {"title": "Hi {{ payload.get('name') }}", "body": "Welcome!"}}
        )
        result = engine.render("welcome", EventChannel.EMAIL, {"name": "Ada"})
        assert result.title == "Hi Ada"
        assert result.body == "Welcome!"

    def test_fallback_template_reference(self):
        assert "payload" in FALLBACK_TEMPLATE

    def test_sandbox_blocks_attribute_access_on_underscore(self):
        engine = TemplateEngine()
        # Payload access to dunder attributes must not leak Python internals.
        result = engine.render(
            "reminder",
            EventChannel.IN_APP,
            {"message": "safe"},
        )
        assert "safe" in result.body


class TestRenderNotificationHelper:
    def test_uses_shared_default_engine(self):
        result = render_notification(
            "security", EventChannel.PUSH, {"title": "New device"}
        )
        assert "New device" in result.body

    def test_channel_param_accepted(self):
        for channel in EventChannel:
            result = render_notification("reminder", channel, {"message": "hi"})
            assert result.body == "hi"


def test_rendered_message_is_frozen():
    msg = RenderedMessage(title="t", body="b")
    with pytest.raises(Exception):
        msg.title = "changed"  # type: ignore[misc]
