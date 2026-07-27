from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from custom_components.handballnet.api import HandballNetAPI


@contextmanager
def mocked_handball_api(hass=None):
    """Provide a HandballNetAPI instance with external HA dependencies mocked."""
    with patch("custom_components.handballnet.api.HandballNetUtils", MagicMock()), patch(
        "custom_components.handballnet.api.async_get_clientsession", MagicMock()
    ):
        yield HandballNetAPI(hass or MagicMock())
