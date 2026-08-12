"""Plugin discovery, activation, and plugin-declared API dispatch."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from sqlmodel import Session

from src.chitrika.database import get_transactional_session, session_scope
from src.chitrika.repositories.plugin_state_repository import PluginStateRepository
from src.chitrika.schemas.plugin_schemas import (
    PluginActionResponse,
    PluginAPIResponse,
    PluginConfigFieldResponse,
    PluginConfigOptionResponse,
    PluginConfigResponse,
    PluginConfigUpdate,
    PluginEndpointResponse,
    PluginResponse,
    PluginScanResponse,
    PluginUpdate,
)
from src.chitrika.services.plugin_runtime import (
    PluginConfigService,
    PluginDiscoveryService,
    PluginError,
    PluginInvoker,
)
from src.chitrika.uow import UnitOfWork

logger = logging.getLogger("chitrika.routes.plugins")

router = APIRouter(tags=["plugins"])


def _plugin_services(session: Session, request: Request):
    return request.app.state.container.plugin_services(session)


@router.get("/plugins", response_model=list[PluginResponse])
def list_plugins(
    request: Request,
    session: Session = Depends(get_transactional_session),
):
    states, invoker = _plugin_services(session, request)
    PluginDiscoveryService(states, request.app.state.container.plugin_registry).discover()
    results: list[PluginResponse] = []
    for record in states.available():
        item = PluginResponse.model_validate(record)
        if record.enabled and record.available:
            api = invoker.get_api(record.id)
            if api is not None:
                item.plugin_api = PluginAPIResponse(
                    endpoints=[
                        PluginEndpointResponse(**asdict(endpoint))
                        for endpoint in api.endpoints
                    ]
                )
            item.has_config = invoker.get_config(record.id) is not None
        results.append(item)
    return results


# ---------------------------------------------------------------------------
# Plugin Config API — editable fields + action buttons (like provider config)
# ---------------------------------------------------------------------------


def _config_response(config, values: dict[str, str]) -> PluginConfigResponse:
    return PluginConfigResponse(
        fields=[
            PluginConfigFieldResponse(
                key=field.key,
                label=field.label,
                input_type=field.input_type,
                required=field.required,
                secret=field.secret,
                default=field.default,
                placeholder=field.placeholder,
                help_text=field.help_text,
                options=[
                    PluginConfigOptionResponse(value=option.value, label=option.label)
                    for option in field.options
                ],
                summary=field.summary,
            )
            for field in config.fields
        ],
        values=values,
        actions=[
            PluginActionResponse(
                key=action.key,
                label=action.label,
                method=action.method,
                path=action.path,
                confirm=action.confirm,
            )
            for action in config.actions
        ],
    )


@router.get("/plugins/{plugin_id}/config", response_model=PluginConfigResponse)
def get_plugin_config(
    plugin_id: str,
    request: Request,
    session: Session = Depends(get_transactional_session),
):
    states, invoker = _plugin_services(session, request)
    config = invoker.get_config(plugin_id)
    record = states.get(plugin_id)
    if config is None or record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin '{plugin_id}' is not enabled or exposes no config",
        )

    try:
        values = PluginConfigService(record, config).read()
    except PluginError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    for field in config.fields:
        if field.key not in values and field.default:
            values[field.key] = field.default
    return _config_response(config, values)


@router.patch("/plugins/{plugin_id}/config", response_model=PluginConfigResponse)
def update_plugin_config(
    plugin_id: str,
    body: PluginConfigUpdate,
    request: Request,
    session: Session = Depends(get_transactional_session),
):
    states, invoker = _plugin_services(session, request)
    config = invoker.get_config(plugin_id)
    record = states.get(plugin_id)
    if config is None or record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin '{plugin_id}' is not enabled or exposes no config",
        )

    try:
        values = PluginConfigService(record, config).update(body.values)
    except PluginError as exc:
        status = 422 if str(exc).startswith("Unknown config keys") else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc

    for field in config.fields:
        if field.key not in values and field.default:
            values[field.key] = field.default
    return _config_response(config, values)


@router.post("/plugins/rescan", response_model=PluginScanResponse)
def rescan_plugins(
    request: Request,
    session: Session = Depends(get_transactional_session),
) -> PluginScanResponse:
    states, _ = _plugin_services(session, request)
    records, invalid = PluginDiscoveryService(
        states, request.app.state.container.plugin_registry
    ).discover()
    return PluginScanResponse(discovered=len(records), invalid=invalid)


@router.patch("/plugins/{plugin_id}", response_model=PluginResponse)
def update_plugin(
    plugin_id: str,
    body: PluginUpdate,
    request: Request,
    session: Session = Depends(get_transactional_session),
):
    try:
        states, invoker = _plugin_services(session, request)
        if states.get(plugin_id) is None:
            PluginDiscoveryService(
                states, request.app.state.container.plugin_registry
            ).discover()
        return invoker.set_enabled(plugin_id, body.enabled)
    except PluginError as exc:
        status = 404 if "was not found" in str(exc) else 422
        raise HTTPException(status_code=status, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Plugin-declared HTTP API (Plugin OpenAPI) — surfaced to the operation panel
# ---------------------------------------------------------------------------


@router.get("/plugins/{plugin_id}/api", response_model=PluginAPIResponse)
def get_plugin_api_metadata(
    plugin_id: str,
    request: Request,
    session: Session = Depends(get_transactional_session),
):
    """Return the endpoints a plugin exposes to the frontend operation panel."""
    _, invoker = _plugin_services(session, request)
    api = invoker.get_api(plugin_id)
    if api is None:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin '{plugin_id}' is not enabled or exposes no API",
        )
    return PluginAPIResponse(
        endpoints=[
            PluginEndpointResponse(**asdict(endpoint)) for endpoint in api.endpoints
        ]
    )


@router.api_route(
    "/plugins/{plugin_id}/api/{path:path}",
    methods=["GET", "POST", "PATCH", "DELETE"],
)
async def dispatch_plugin_api(
    plugin_id: str,
    path: str,
    request: Request,
):
    """Dispatch a request to a handler declared by the plugin's ``get_plugin_api``.

    Handlers receive ``(query: dict, body: dict)`` and return a JSON-serializable
    dict. Endpoint matching uses ``"{METHOD} /path"`` — e.g. ``GET /status``.
    """
    with UnitOfWork(session_factory=session_scope) as uow:
        _, invoker = _plugin_services(uow.session, request)
        api = invoker.get_api(plugin_id)
    if api is None:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin '{plugin_id}' is not enabled or exposes no API",
        )

    normalized_path = f"/{path.rstrip('/')}"
    method = request.method.upper()
    key = f"{method} {normalized_path}"
    handler = api.handlers.get(key)

    if handler is None:
        known_methods = {
            endpoint.method
            for endpoint in api.endpoints
            if endpoint.path.rstrip("/") == normalized_path
        }
        if known_methods:
            raise HTTPException(status_code=405, detail=f"Endpoint exists but not via {method}")
        raise HTTPException(status_code=404, detail=f"Plugin endpoint '{key}' not found")

    body: dict = {}
    if method in ("POST", "PATCH", "DELETE"):
        raw_bytes = await request.body()
        if raw_bytes:
            try:
                raw = json.loads(raw_bytes)
            except json.JSONDecodeError:
                raw = None
            if isinstance(raw, dict):
                body = raw
            elif isinstance(raw, list):
                body = {"items": raw}

    try:
        result = await run_in_threadpool(handler, dict(request.query_params), body)
    except Exception as exc:
        with UnitOfWork(session_factory=session_scope) as uow:
            states = PluginStateRepository(uow.session)
            record = states.get(plugin_id)
            if record is not None:
                states.set_error(record, f"API handler failed: {exc}")
        logger.exception("Plugin '%s' API handler %s failed", plugin_id, key)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return JSONResponse(content=result or {})
