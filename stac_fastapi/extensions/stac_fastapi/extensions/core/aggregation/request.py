"""Request model for the Aggregation extension."""

from typing import List, Optional

import attr
from fastapi import Query, Path, Body
from pydantic import Field
from typing_extensions import Annotated

from stac_fastapi.types.search import (
    BaseSearchGetRequest,
    BaseSearchPostRequest,
    str2list,
)
from stac_fastapi.api.models import APIRequest


def _agg_converter(
    val: Annotated[
        Optional[str],
        Query(description="A list of aggregations to compute and return."),
    ] = None,
) -> Optional[List[str]]:
    return str2list(val)


@attr.s
class AggregationExtensionGetRequest(BaseSearchGetRequest):
    """Aggregation Extension GET request model."""

    aggregations: Optional[List[str]] = attr.ib(default=None, converter=_agg_converter)


class TempAggregationExtensionPostRequest(BaseSearchPostRequest):
    """Aggregation Extension POST request model."""

    aggregations: Optional[List[str]] = Field(
        default=None,
        description="A list of aggregations to compute and return.",
    )


class AggregationExtensionPostRequest(BaseSearchPostRequest):
    """Aggregation Extension POST request model."""

    #cat_path: Annotated[str, Path(description="Catalog path", regex=r"^(catalogs/[^/]+)(/catalogs/[^/]+)*")] = attr.ib()
    # request_body: TempAggregationExtensionPostRequest = Body(...)
    aggregations: Optional[List[str]] = Field(
        default=None,
        description="A list of aggregations to compute and return.",
    )
