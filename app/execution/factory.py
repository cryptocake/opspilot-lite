from app.config import Settings, get_settings
from app.errors import ConfigurationError
from app.execution.dry_run import DryRunExecutor
from app.execution.webhook import WebhookExecutor


def get_action_executor(settings: Settings | None = None):
    settings = settings or get_settings()
    if settings.execution_mode == "dry_run":
        return DryRunExecutor()
    if settings.execution_mode == "webhook":
        if not settings.webhook_sink_url:
            raise ConfigurationError("Webhook execution mode requires OPSPILOT_WEBHOOK_SINK_URL")
        return WebhookExecutor(settings.webhook_sink_url, settings.webhook_timeout_seconds)
    raise ConfigurationError(f"Unsupported execution mode: {settings.execution_mode}")
