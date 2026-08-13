"""Jinja2 template rendering for notification content.

Renders per-category notification templates against an event payload.  Templates
run inside a sandboxed Jinja environment so untrusted payload data cannot reach
Python internals.  Missing payload keys render as empty strings rather than
raising, so a sparse payload never crashes a delivery.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from jinja2 import TemplateError
from jinja2.sandbox import SandboxedEnvironment

from app.schemas.event import EventChannel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RenderedMessage:
    """Rendered notification content.

    ``title`` is ``None`` for channels that carry no subject line (e.g. SMS).
    """

    title: str | None
    body: str


# ── Default template registry ──────────────────────────────────
# Keyed by category; each entry carries an optional ``title`` and a required
# ``body`` Jinja2 template.  The event payload is exposed as ``payload``.
DEFAULT_TEMPLATES: dict[str, dict[str, str]] = {
    "security": {
        "title": "Security alert: {{ payload.get('title', 'New activity') }}",
        "body": (
            "We detected {{ payload.get('title', 'unusual activity') }} on your "
            "account. If this was you, no further action is needed."
        ),
    },
    "transaction": {
        "title": "Transaction {{ payload.get('status', 'update') }}",
        "body": (
            "Your {{ payload.get('kind', 'transaction') }} of "
            "{{ payload.get('amount', 'an unspecified amount') }} was "
            "{{ payload.get('status', 'processed') }}."
        ),
    },
    "reminder": {
        "title": "Reminder",
        "body": "{{ payload.get('message', 'You have a pending item.') }}",
    },
}

FALLBACK_TEMPLATE = (
    "{{ payload.get('message') or payload.get('title') or "
    "'You have a new notification.' }}"
)


class TemplateEngine:
    """Renders notification templates in a sandboxed Jinja environment."""

    def __init__(self, templates: dict[str, dict[str, str]] | None = None) -> None:
        self._templates = templates if templates is not None else DEFAULT_TEMPLATES
        # Sandboxed + no autoescape: content is plain text / escaped by the
        # provider adapter, not by this renderer.
        self._env = SandboxedEnvironment(autoescape=False)

    def render(
        self,
        category: str,
        channel: EventChannel,
        payload: dict,
    ) -> RenderedMessage:
        """Render a message for ``category`` against ``payload``.

        ``channel`` is accepted for future per-channel template selection and
        is intentionally unused by the default registry.
        """
        del channel  # reserved for per-channel templates
        spec = self._templates.get(category)

        if spec is None:
            title_template: str | None = None
            body_template: str = FALLBACK_TEMPLATE
        else:
            title_template = spec.get("title")
            body_template = spec.get("body") or FALLBACK_TEMPLATE

        title: str | None = None
        if title_template:
            title = self._render(title_template, payload)
        body = self._render(body_template, payload)
        return RenderedMessage(title=title, body=body)

    def _render(self, template: str, payload: dict) -> str:
        try:
            return self._env.from_string(template).render(payload=payload).strip()
        except TemplateError as exc:
            logger.warning("Template render failed (%s); using raw fallback", exc)
            return str(payload.get("message") or payload.get("title") or "")


_default_engine = TemplateEngine()


def render_notification(
    category: str,
    channel: EventChannel,
    payload: dict,
) -> RenderedMessage:
    """Convenience wrapper over the shared default :class:`TemplateEngine`."""
    return _default_engine.render(category, channel, payload)
