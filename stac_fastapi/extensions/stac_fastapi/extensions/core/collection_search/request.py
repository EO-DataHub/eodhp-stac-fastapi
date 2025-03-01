"""Request models for the Collection-Search extension."""

from datetime import datetime as dt
from typing import Any, List, Optional, Tuple, cast, Union, Dict

import attr
from fastapi import Query, Path
from pydantic import BaseModel, Field, field_validator
from stac_pydantic.api.search import SearchDatetime
from stac_pydantic.shared import BBox
from typing_extensions import Annotated

from stac_fastapi.types.rfc3339 import DateTimeType
from stac_fastapi.types.search import (
    APIRequest,
    Limit,
    _bbox_converter,
    _datetime_converter,
    str2list,
    _filter_converter,
    _filter_lang_converter
)
from stac_fastapi.extensions.core.filter.request import FilterLang
@attr.s
class BaseCollectionSearchAllGetRequest(APIRequest):
    """Basics additional Collection-Search parameters for the GET request."""

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
    filter: Optional[str] = attr.ib(default=None, converter=_filter_converter)
    filter_lang: Optional[FilterLang] = attr.ib(default="cql2-text", converter=_filter_lang_converter)

class BaseCollectionSearchPostRequest(BaseModel):
    """Collection-Search POST model."""

    bbox: Optional[BBox] = None
    datetime: Optional[str] = None
    limit: Optional[Limit] = Field(
        10,
        description="Limits the number of results that are included in each page of the response (capped to 10_000).",  # noqa: E501
    )
    q: Optional[List[str]] = Field(
        None,
        description="Free-text search terms to query against collection metadata. Separate multiple terms with commas.",
        json_schema_extra={
            "example": "climate,temperature,optical",
        },
    )
    filter: Optional[Union[str, Dict[str, Any]]] = Field(
        default=None,
        alias="filter",
        description="A CQL filter expression for filtering items.",
        json_schema_extra={
            "example": {
                "op": "and",
                "args": [
                    {
                        "op": "=",
                        "args": [
                            {"property": "id"},
                            "LC08_L1TP_060247_20180905_20180912_01_T1_L1TP",
                        ],
                    },
                    {"op": "=", "args": [{"property": "collection"}, "landsat8_l1tp"]},
                ],
            },
        }
    )
    filter_lang: Optional[FilterLang] = Field(
        alias="filter-lang",
        default="cql2-json",
        description="The CQL filter encoding that the 'filter' value uses."
    )
    # Private properties to store the parsed datetime values.
    # Not part of the model schema.
    _start_date: Optional[dt] = None
    _end_date: Optional[dt] = None

    # Properties to return the private values
    @property
    def start_date(self) -> Optional[dt]:
        """start date."""
        return self._start_date

    @property
    def end_date(self) -> Optional[dt]:
        """end date."""
        return self._end_date

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v: BBox) -> BBox:
        """validate bbox."""
        if v:
            # Validate order
            if len(v) == 4:
                xmin, ymin, xmax, ymax = cast(Tuple[int, int, int, int], v)
            else:
                xmin, ymin, min_elev, xmax, ymax, max_elev = cast(
                    Tuple[int, int, int, int, int, int], v
                )
                if max_elev < min_elev:
                    raise ValueError(
                        "Maximum elevation must greater than minimum elevation"
                    )

            if xmax < xmin:
                raise ValueError(
                    "Maximum longitude must be greater than minimum longitude"
                )

            if ymax < ymin:
                raise ValueError(
                    "Maximum longitude must be greater than minimum longitude"
                )

            # Validate against WGS84
            if xmin < -180 or ymin < -90 or xmax > 180 or ymax > 90:
                raise ValueError("Bounding box must be within (-180, -90, 180, 90)")

        return v

    @field_validator("datetime")
    @classmethod
    def validate_datetime(cls, value: str) -> str:
        """validate datetime."""
        # Split on "/" and replace no value or ".." with None
        values = [v if v and v != ".." else None for v in value.split("/")]

        # If there are more than 2 dates, it's invalid
        if len(values) > 2:
            raise ValueError(
                """Invalid datetime range. Too many values.
                Must match format: {begin_date}/{end_date}"""
            )

        # If there is only one date, duplicate to use for both start and end dates
        if len(values) == 1:
            values = [values[0], values[0]]

        # Cast because pylance gets confused by the type adapter and annotated type
        dates = cast(
            List[Optional[dt]],
            [
                # Use the type adapter to validate the datetime strings,
                # strict is necessary due to pydantic issues #8736 and #8762
                SearchDatetime.validate_strings(v, strict=True) if v else None
                for v in values
            ],
        )

        # If there is a start and end date,
        # check that the start date is before the end date
        if dates[0] and dates[1] and dates[0] > dates[1]:
            raise ValueError(
                "Invalid datetime range. Begin date after end date. "
                "Must match format: {begin_date}/{end_date}"
            )

        # Store the parsed dates
        cls._start_date = dates[0]
        cls._end_date = dates[1]

        # Return the original string value
        return value