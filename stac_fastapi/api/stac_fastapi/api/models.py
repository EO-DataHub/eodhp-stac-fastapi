"""Api request/response models."""

from typing import List, Optional, Type, Union

import attr
from fastapi import Path, Query
from pydantic import BaseModel, create_model
from stac_pydantic.shared import BBox
from typing_extensions import Annotated

from stac_fastapi.types.extension import ApiExtension
from stac_fastapi.types.rfc3339 import DateTimeType
from stac_fastapi.types.search import (
    APIRequest,
    BaseSearchGetRequest,
    BaseSearchPostRequest,
    BaseSearchAllGetRequest,
    Limit,
    _bbox_converter,
    _datetime_converter,
    str2list,
)

try:
    import orjson  # noqa
    from fastapi.responses import ORJSONResponse as JSONResponse
except ImportError:  # pragma: nocover
    from starlette.responses import JSONResponse


def create_request_model(
    model_name="SearchGetRequest",
    base_model: Union[Type[BaseModel], APIRequest] = BaseSearchGetRequest,
    extensions: Optional[List[ApiExtension]] = None,
    mixins: Optional[Union[List[BaseModel], List[APIRequest]]] = None,
    request_type: Optional[str] = "GET",
) -> Union[Type[BaseModel], APIRequest]:
    """Create a pydantic model for validating request bodies."""
    fields = {}
    extension_models = []

    # Check extensions for additional parameters to search
    for extension in extensions or []:
        if extension_model := extension.get_request_model(request_type):
            extension_models.append(extension_model)

    mixins = mixins or []

    models = [base_model] + extension_models + mixins

    # Handle GET requests
    if all([issubclass(m, APIRequest) for m in models]):
        return attr.make_class(model_name, attrs={}, bases=tuple(models))

    # Handle POST requests
    elif all([issubclass(m, BaseModel) for m in models]):
        for model in models:
            for k, field_info in model.model_fields.items():
                fields[k] = (field_info.annotation, field_info)
        return create_model(model_name, **fields, __base__=base_model)

    raise TypeError("Mixed Request Model types. Check extension request types.")


def create_get_request_model(
    extensions: Optional[List[ApiExtension]],
    base_model: BaseSearchGetRequest = BaseSearchGetRequest,
) -> APIRequest:
    """Wrap create_request_model to create the GET request model."""

    return create_request_model(
        "SearchGetRequest",
        base_model=base_model,
        extensions=extensions,
        request_type="GET",
    )

def create_get_all_request_model(
    extensions: Optional[List[ApiExtension]],
    base_model: BaseSearchAllGetRequest = BaseSearchAllGetRequest,
) -> APIRequest:
    """Wrap create_request_model to create the GET request model."""

    return create_request_model(
        "SearchAllGetRequest",
        base_model=base_model,
        extensions=extensions,
        request_type="GET",
    )


def create_post_request_model(
    extensions: Optional[List[ApiExtension]],
    base_model: BaseSearchPostRequest = BaseSearchPostRequest,
) -> Type[BaseModel]:
    """Wrap create_request_model to create the POST request model."""
    return create_request_model(
        "SearchPostRequest",
        base_model=base_model,
        extensions=extensions,
        request_type="POST",
    )

@attr.s
class CatalogUri(APIRequest):
    """Get or delete catalog."""

    cat_path: Annotated[str, Path(description="Catalog path", regex=r"^([^/]+)(/catalogs/[^/]+)*$")] = attr.ib()

@attr.s
class BaseCatalogUri(APIRequest):
    """Get or delete catalog."""

    catalog_id: Annotated[str, Path(description="Catalog ID", regex=r"^([^/]+)$")] = attr.ib()


@attr.s
class GetCatalogUri(APIRequest):
    """Get or delete catalog."""

    cat_path: Annotated[str, Path(description="Catalog path", regex=r"^([^/]+)(/catalogs/[^/]+)*$")] = attr.ib()
    catalog_id: Annotated[str, Path(description="Catalog ID", regex=r"^([^/]+)$")] = attr.ib()

@attr.s
class CreateCatalogUri(APIRequest):
    """Get or delete catalog."""

    cat_path: Annotated[str, Path(description="Catalog path", regex=r"root$|(^([^/]+)(/catalogs/[^/]+)*$)")] = attr.ib()

@attr.s
class BaseCollectionSearchGetRequest(APIRequest):
    """Get or delete catalog."""

    cat_path: Annotated[str, Path(description="Catalog path", regex=r"root$|(^([^/]+)(/catalogs/[^/]+)*$)")] = attr.ib()
    bbox: Optional[BBox] = attr.ib(default=None, converter=_bbox_converter)
    datetime: Optional[DateTimeType] = attr.ib(
        default=None, converter=_datetime_converter
    )
    limit: Annotated[
        Optional[Limit],
        Query(
            description="Limits the number of results that are included in each page of the response."  # noqa: E501
        ),
    ] = attr.ib(default=10)
    q: Optional[List[str]] = attr.ib(default=None, converter=str2list)



@attr.s
class CollectionUri(CatalogUri):
    """Get or delete collection."""

    collection_id: Annotated[str, Path(description="Collection ID")] = attr.ib()
    

@attr.s
class ItemUri(CollectionUri):
    """Get or delete item."""

    item_id: Annotated[str, Path(description="Item ID")] = attr.ib()


@attr.s
class EmptyRequest(APIRequest):
    """Empty request."""

    ...


@attr.s
class ItemCollectionUri(CollectionUri):
    """Get item collection."""

    limit: Annotated[
        Optional[Limit],
        Query(
            description="Limits the number of results that are included in each page of the response (capped to 10_000)."  # noqa: E501
        ),
    ] = attr.ib(default=10)
    bbox: Optional[BBox] = attr.ib(default=None, converter=_bbox_converter)
    datetime: Optional[DateTimeType] = attr.ib(
        default=None, converter=_datetime_converter
    )


class GeoJSONResponse(JSONResponse):
    """JSON with custom, vendor content-type."""

    media_type = "application/geo+json"


class JSONSchemaResponse(JSONResponse):
    """JSON with custom, vendor content-type."""

    media_type = "application/schema+json"
