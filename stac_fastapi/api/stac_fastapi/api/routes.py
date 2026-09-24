"""Route factories."""

import copy
import functools
import inspect
import ipaddress
import jwt
import logging
import os
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Type, TypedDict, Union

from fastapi import Depends, HTTPException, params
from fastapi.dependencies.utils import get_parameterless_sub_dependant
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWTError
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Match
from starlette.status import HTTP_204_NO_CONTENT

from stac_fastapi.api.models import APIRequest

from stac_fastapi.api.settings import CACHE_CONTROL_CATALOGS_LIST, CACHE_CONTROL_HEADERS

# Get the logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set the logging level to INFO for this module

# Create a console handler and set the level to INFO
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create a formatter and set it for the handler
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(console_handler)

def _wrap_response(resp: Any, verb: str, url_path: str) -> Any:
    if resp is not None:
        if verb == "GET":
            if url_path.startswith("/catalogs/"):
                root_catalog = url_path.split("/")[2]
                if root_catalog in CACHE_CONTROL_CATALOGS_LIST:
                    # Add cache control headers
                    return JSONResponse(content=resp, headers={"cache-control": CACHE_CONTROL_HEADERS})
            elif url_path=="/":
                return JSONResponse(content=resp, headers={"cache-control": CACHE_CONTROL_HEADERS})
        # Return with no cache control headers
        return JSONResponse(content=resp, headers={"cache-control": "max-age=0"})
    else:  # None is returned as 204 No Content
        return Response(status_code=HTTP_204_NO_CONTENT, headers={"cache-control": "max-age=0"})



def sync_to_async(func):
    """Run synchronous function asynchronously in a background thread."""

    @functools.wraps(func)
    async def run(*args, **kwargs):
        return await run_in_threadpool(func, *args, **kwargs)

    return run

# Define the OAuth2 scheme for Bearer token
bearer_scheme = HTTPBearer(auto_error=False)

# Domain used to build the Keycloak JWKS endpoint for verifying JWT signatures.
EODH_DOMAIN = os.getenv("EODH_DOMAIN", "dev.eodatahub.org.uk")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "eodhp")

# The Keycloak client IDs platform tokens are issued for (the audience mappers on the eodh and
# eodh-workspaces clients, eodhp-argocd-deployment apps/keycloak/base/realms.yaml). This list is
# duplicated across the platform's services, so change them together.
JWT_AUDIENCE = ["eodh", "eodh-workspaces"]


@lru_cache
def _jwks_client() -> PyJWKClient:
    """One client per process, so the JWKS document is cached rather than re-fetched from
    Keycloak on every request. PyJWKClient does this caching internally, but only across
    calls on the same instance.
    """
    certs_url = f"https://{EODH_DOMAIN}/keycloak/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
    return PyJWKClient(certs_url)


# TODO: Also extract group information from the headers
def extract_headers(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Dict[str, Any]:
    """Extract headers from request.

    Args:
        token: The OAuth2 token extracted from the Authorization header.

    Returns:
        Dict of headers.
    """
    headers = {}
    if credentials:
        # Exchange the token
        keycloak_token = credentials.credentials
        # The signature is verified against Keycloak's own published key, rather than
        # trusting an upstream gateway to have checked it: a gateway sitting in front of
        # the public path does not cover traffic that reaches this service directly from
        # elsewhere on the cluster network.
        try:
            signing_key = _jwks_client().get_signing_key_from_jwt(keycloak_token)
            decoded_jwt = jwt.decode(
                keycloak_token,
                signing_key.key,
                audience=JWT_AUDIENCE,
                algorithms=["RS256"],
            )
        except PyJWTError as e:
            logger.warning(f"Rejected invalid JWT: {e}")
            raise HTTPException(status_code=401, detail="Invalid JWT token") from e

        username = decoded_jwt.get("preferred_username", None)
        if "workspaces" not in decoded_jwt:
            # If the JWT does not contain the workspaces claim, set it to an empty set
            workspaces = set([])
            logger.warning("JWT for username: %s does not contain 'workspaces' claim", username)
        else:
            workspaces = set(decoded_jwt.get("workspaces", []))
            logger.info(f"User is authenticated with workspaces: {workspaces}")

        user_services = decoded_jwt.get("user_services", None)
        if user_services:
            logger.info(f"User has access to user service workspace: {user_services}")
            # user_services is a single string, convert it to a set
            user_services = set([user_services])
            # Take union of workspaces and user_services
            workspaces |= user_services
        
        # Add the workspaces to the headers
        headers["X-Workspaces"] = list(workspaces)
        headers["X-Authenticated"] = True
    else:
        logger.info("User is not authenticated")
        headers["X-Workspaces"] = []
        headers["X-Authenticated"] = False

    return headers  # Allows support for more headers in future, e.g. group information


def _is_loopback(host: Optional[str]) -> bool:
    try:
        return host is not None and ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _authorize_workspace(
    workspace: Optional[str], headers: Dict[str, Any], client_host: Optional[str] = None
) -> None:
    """Reject a write to a workspace the caller's verified token doesn't grant access to.

    `workspace` is a client-supplied request field (path/query param), not derived from
    the verified JWT, so without this check a caller could set it to any workspace
    regardless of which ones their token actually verifies membership of - e.g. writing
    an item into a workspace they don't own.

    Unauthenticated requests from loopback are exempt: the stac-fastapi-ingester sidecar
    writes to the read-write container over localhost with a `workspace` param and no
    token. That container binds 127.0.0.1 only, so loopback means "from inside the pod".
    A request that does carry a token is always checked against it.
    """
    if workspace is None:
        return
    if not headers.get("X-Authenticated") and _is_loopback(client_host):
        return
    if workspace not in headers.get("X-Workspaces", []):
        raise HTTPException(status_code=403, detail="Not authorized for this workspace")


def create_async_endpoint(
    func: Callable,
    request_model: Union[Type[APIRequest], Type[BaseModel], Dict],
):
    """Wrap a function in a coroutine which may be used to create a FastAPI endpoint.

    Synchronous functions are executed asynchronously using a background thread.
    """

    if not inspect.iscoroutinefunction(func):
        func = sync_to_async(func)

    if issubclass(request_model, APIRequest):

        async def _endpoint(
            request: Request,
            request_data: request_model = Depends(),  # type:ignore
            headers=Depends(extract_headers),
        ):
            """Endpoint."""
            kwargs = request_data.kwargs()
            _authorize_workspace(
                kwargs.get("workspace"), headers, request.client.host if request.client else None
            )
            return _wrap_response(await func(request=request, auth_headers=headers, **kwargs),
                                  request.method,
                                  request.url.path)

    elif issubclass(request_model, BaseModel):

        async def _endpoint(
            request: Request,
            request_data: request_model,  # type:ignore
            headers=Depends(extract_headers),
        ):
            """Endpoint."""
            return _wrap_response(await func(request_data, auth_headers=headers, request=request),
                                  request.method,
                                  request.url.path)

    else:

        async def _endpoint(
            request: Request,
            request_data: Dict[str, Any],  # type:ignore
            headers=Depends(extract_headers),
        ):
            """Endpoint."""
            return _wrap_response(await func(request_data, auth_headers=headers, request=request),
                                  request.method,
                                  request.url.path)

    return _endpoint


class Scope(TypedDict, total=False):
    """More strict version of Starlette's Scope."""

    # https://github.com/encode/starlette/blob/6af5c515e0a896cbf3f86ee043b88f6c24200bcf/starlette/types.py#L3
    path: str
    method: str
    type: Optional[str]


def add_route_dependencies(
    routes: List[BaseRoute], scopes: List[Scope], dependencies=List[params.Depends]
) -> None:
    """Add dependencies to routes.

    Allows a developer to add dependencies to a route after the route has been
    defined.

    "*" can be used for path or method to match all allowed routes.

    Returns:
        None
    """
    for scope in scopes:
        _scope = copy.deepcopy(scope)
        for route in routes:
            if scope["path"] == "*":
                _scope["path"] = route.path

            if scope["method"] == "*":
                _scope["method"] = list(route.methods)[0]

            match, _ = route.matches({"type": "http", **_scope})
            if match != Match.FULL:
                continue

            # Ignore paths without dependants, e.g. /api, /api.html, /docs/oauth2-redirect
            if not hasattr(route, "dependant"):
                continue

            # Mimicking how APIRoute handles dependencies:
            # https://github.com/tiangolo/fastapi/blob/1760da0efa55585c19835d81afa8ca386036c325/fastapi/routing.py#L408-L412
            for depends in dependencies[::-1]:
                route.dependant.dependencies.insert(
                    0,
                    get_parameterless_sub_dependant(
                        depends=depends, path=route.path_format
                    ),
                )

            # Register dependencies directly on route so that they aren't ignored if
            # the routes are later associated with an app (e.g.
            # app.include_router(router))
            # https://github.com/tiangolo/fastapi/blob/58ab733f19846b4875c5b79bfb1f4d1cb7f4823f/fastapi/applications.py#L337-L360
            # https://github.com/tiangolo/fastapi/blob/58ab733f19846b4875c5b79bfb1f4d1cb7f4823f/fastapi/routing.py#L677-L678
            route.dependencies.extend(dependencies)
