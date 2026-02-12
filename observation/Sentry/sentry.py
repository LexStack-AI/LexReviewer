"""Sentry initialization helper for FastAPI + background tasks."""

import os

from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration


class SentryObservation:
    """Configure Sentry once on startup if a DSN is provided."""

    def __init__(self) -> None:
        load_dotenv()
        sentry_dsn = os.getenv("SENTRY_DSN")
        if not sentry_dsn:
            pass
        sentry_sdk.init(
            dsn=sentry_dsn,
            send_default_pii=True,
            # Enable sending logs to Sentry
            enable_logs=True,
            # Set traces_sample_rate to 1.0 to capture 100% of transactions for tracing.
            traces_sample_rate=1.0,
            profile_session_sample_rate=1.0,
            profile_lifecycle="trace",
            integrations=[
                FastApiIntegration(
                    transaction_style="endpoint",
                    failed_request_status_codes={403, *range(500, 599)},
                    http_methods_to_capture=("GET", "POST", "DELETE", "OPTIONS"),
                ),
            ]
        )
