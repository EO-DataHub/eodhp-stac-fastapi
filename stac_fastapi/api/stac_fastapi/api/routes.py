"""Route factories."""

import copy
import functools
import inspect
import jwt
import logging
import requests
from typing import Any, Callable, Dict, List, Optional, Type, TypedDict, Union

from fastapi import Depends, params
from fastapi.dependencies.utils import get_parameterless_sub_dependant
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Match
from starlette.status import HTTP_204_NO_CONTENT

from stac_fastapi.api.models import APIRequest

from stac_fastapi.api.settings import KEYCLOAK_BASE_URL, REALM, CLIENT_ID, CLIENT_SECRET, CACHE_CONTROL_CATALOGS_LIST, CACHE_CONTROL_HEADERS

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

KEYCLOAK_URL = f"{KEYCLOAK_BASE_URL}/realms/{REALM}/protocol/openid-connect/token"

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
        decoded_jwt = jwt.decode(
            keycloak_token,
            options={"verify_signature": False},
            algorithms=["HS256"],
        )
        workspaces = decoded_jwt.get("workspaces", [])
        user_services = decoded_jwt.get("user_services", None)
        logger.info(f"User is authenticated with workspaces: {workspaces}")
        if user_services:
            logger.info(f"User has access to user service workspace: {user_services}")

        # Append user_services to workspaces if it exists
        headers["X-Workspaces"] = workspaces.append(user_services) if user_services else workspaces
        headers["X-Authenticated"] = True
    else:
        logger.info("User is not authenticated")
        headers["X-Workspaces"] = []
        headers["X-Authenticated"] = False

    return headers  # Allows support for more headers in future, e.g. group information


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
            return _wrap_response(await func(request=request, auth_headers=headers, **request_data.kwargs()),
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
