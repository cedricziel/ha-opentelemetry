"""Config flow for the OpenTelemetry integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_AUTH_HEADER,
    CONF_DATASET_ID,
    CONF_ENABLE_LOGS,
    CONF_ENABLE_METRICS,
    CONF_ENABLE_TRACES,
    CONF_ENDPOINT,
    CONF_EXCLUDE_ENTITIES,
    CONF_INCLUDE_DOMAINS,
    CONF_INSECURE,
    CONF_PROTOCOL,
    CONF_SCAN_INTERVAL,
    CONF_SCOPE_ENTITIES,
    CONF_SCOPE_SYSTEM,
    CONF_SERVICE_NAME,
    CONF_TENANT_ID,
    DEFAULT_ENABLE_LOGS,
    DEFAULT_ENABLE_METRICS,
    DEFAULT_ENABLE_TRACES,
    DEFAULT_INSECURE,
    DEFAULT_PROTOCOL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SCOPE_ENTITIES,
    DEFAULT_SCOPE_SYSTEM,
    DEFAULT_SERVICE_NAME,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    PROTOCOLS,
)


def _connection_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_ENDPOINT, default=defaults.get(CONF_ENDPOINT, "")
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Required(
                CONF_PROTOCOL, default=defaults.get(CONF_PROTOCOL, DEFAULT_PROTOCOL)
            ): SelectSelector(SelectSelectorConfig(options=PROTOCOLS)),
            vol.Required(
                CONF_INSECURE, default=defaults.get(CONF_INSECURE, DEFAULT_INSECURE)
            ): BooleanSelector(),
            vol.Optional(
                CONF_AUTH_HEADER, default=defaults.get(CONF_AUTH_HEADER, "")
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            vol.Required(
                CONF_TENANT_ID, default=defaults.get(CONF_TENANT_ID, "")
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Optional(
                CONF_DATASET_ID, default=defaults.get(CONF_DATASET_ID, "")
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Required(
                CONF_SERVICE_NAME,
                default=defaults.get(CONF_SERVICE_NAME, DEFAULT_SERVICE_NAME),
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
        }
    )


def _validate_connection(data: dict[str, Any]) -> dict[str, str]:
    """Validate user input, returning a dict of field -> error code."""
    errors: dict[str, str] = {}
    if not data.get(CONF_ENDPOINT, "").strip():
        errors[CONF_ENDPOINT] = "endpoint_required"
    if not data.get(CONF_TENANT_ID, "").strip():
        errors[CONF_TENANT_ID] = "tenant_required"
    return errors


class OpenTelemetryConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpenTelemetry."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial connection step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_connection(user_input)
            if not errors:
                await self.async_set_unique_id(
                    f"{user_input[CONF_ENDPOINT]}::{user_input[CONF_TENANT_ID]}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"OpenTelemetry ({user_input[CONF_TENANT_ID]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_connection_schema(user_input),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the OTLP connection details of an existing entry."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()
        if user_input is not None:
            errors = _validate_connection(user_input)
            if not errors:
                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    title=f"OpenTelemetry ({user_input[CONF_TENANT_ID]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_connection_schema(user_input or reconfigure_entry.data),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Create the options flow."""
        return OpenTelemetryOptionsFlow()


class OpenTelemetryOptionsFlow(OptionsFlow):
    """Handle options for the OpenTelemetry integration (what to export)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the export options."""
        if user_input is not None:
            include_domains = [
                domain.strip()
                for domain in user_input.get(CONF_INCLUDE_DOMAINS, "").split(",")
                if domain.strip()
            ]
            exclude_entities = [
                entity.strip()
                for entity in user_input.get(CONF_EXCLUDE_ENTITIES, "").split(",")
                if entity.strip()
            ]
            options = {**user_input}
            options[CONF_INCLUDE_DOMAINS] = include_domains
            options[CONF_EXCLUDE_ENTITIES] = exclude_entities
            return self.async_create_entry(title="", data=options)

        current = self.config_entry.options
        current_include = current.get(CONF_INCLUDE_DOMAINS, [])
        current_exclude = current.get(CONF_EXCLUDE_ENTITIES, [])

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ENABLE_TRACES,
                    default=current.get(CONF_ENABLE_TRACES, DEFAULT_ENABLE_TRACES),
                ): BooleanSelector(),
                vol.Required(
                    CONF_ENABLE_METRICS,
                    default=current.get(CONF_ENABLE_METRICS, DEFAULT_ENABLE_METRICS),
                ): BooleanSelector(),
                vol.Required(
                    CONF_ENABLE_LOGS,
                    default=current.get(CONF_ENABLE_LOGS, DEFAULT_ENABLE_LOGS),
                ): BooleanSelector(),
                vol.Required(
                    CONF_SCOPE_SYSTEM,
                    default=current.get(CONF_SCOPE_SYSTEM, DEFAULT_SCOPE_SYSTEM),
                ): BooleanSelector(),
                vol.Required(
                    CONF_SCOPE_ENTITIES,
                    default=current.get(CONF_SCOPE_ENTITIES, DEFAULT_SCOPE_ENTITIES),
                ): BooleanSelector(),
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL, step=1
                    )
                ),
                vol.Optional(
                    CONF_INCLUDE_DOMAINS, default=", ".join(current_include)
                ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
                vol.Optional(
                    CONF_EXCLUDE_ENTITIES, default=", ".join(current_exclude)
                ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
