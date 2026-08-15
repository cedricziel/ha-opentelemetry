"""Tests for the OpenTelemetry config flow."""
from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from custom_components.opentelemetry.const import (
    CONF_ENDPOINT,
    CONF_INSECURE,
    CONF_PROTOCOL,
    CONF_SERVICE_NAME,
    CONF_TENANT_ID,
    DOMAIN,
)

USER_INPUT = {
    CONF_ENDPOINT: "192.168.178.6:4317",
    CONF_PROTOCOL: "grpc",
    CONF_INSECURE: True,
    "auth_header": "Bearer sk-test",
    CONF_TENANT_ID: "homelab",
    "dataset_id": "",
    CONF_SERVICE_NAME: "homeassistant",
}


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    """A complete, valid submission creates a config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    with patch(
        "custom_components.opentelemetry.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
        await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    assert result["title"] == "OpenTelemetry (homelab)"
    assert result["data"][CONF_ENDPOINT] == "192.168.178.6:4317"


async def test_user_flow_requires_endpoint_and_tenant(hass: HomeAssistant) -> None:
    """Blank endpoint/tenant fields are rejected with field errors."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    bad_input = {**USER_INPUT, CONF_ENDPOINT: "", CONF_TENANT_ID: ""}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], bad_input
    )
    assert result["type"] == "form"
    assert result["errors"] == {
        CONF_ENDPOINT: "endpoint_required",
        CONF_TENANT_ID: "tenant_required",
    }


async def test_duplicate_entry_aborts(hass: HomeAssistant) -> None:
    """A second entry with the same endpoint/tenant is aborted as a duplicate."""
    with patch(
        "custom_components.opentelemetry.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
        await hass.async_block_till_done()

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"
