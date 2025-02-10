"""Base clients."""

import abc
import warnings
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import attr
from fastapi import Request
from geojson_pydantic.geometries import Geometry
from stac_pydantic import Catalog, Collection, Item, ItemCollection
from stac_pydantic.links import Relations
from stac_pydantic.shared import BBox, MimeTypes
from stac_pydantic.version import STAC_VERSION
from starlette.responses import Response

from stac_fastapi.types import stac
from stac_fastapi.types.access_policy import AccessPolicy
from stac_fastapi.types.config import ApiSettings
from stac_fastapi.types.conformance import BASE_CONFORMANCE_CLASSES
from stac_fastapi.types.extension import ApiExtension
from stac_fastapi.types.requests import get_base_url
from stac_fastapi.types.rfc3339 import DateTimeType
from stac_fastapi.types.search import BaseSearchPostRequest

__all__ = [
    "NumType",
    "StacType",
    "BaseTransactionsClient",
    "AsyncBaseTransactionsClient",
    "LandingPageMixin",
    "BaseCoreClient",
    "AsyncBaseCoreClient",
]

NumType = Union[float, int]
StacType = Dict[str, Any]

api_settings = ApiSettings()


@attr.s  # type:ignore
class BaseTransactionsClient(abc.ABC):
    """Defines a pattern for implementing the STAC API Transaction Extension."""

    @abc.abstractmethod
    def create_item(
        self,
        cat_path: str,
        collection_id: str,
        item: Union[Item, ItemCollection],
        **kwargs,
    ) -> Optional[Union[stac.Item, Response, None]]:
        """Create a new item.

        Called with `POST /collections/{collection_id}/items`.

        Args:
            item: the item or item collection
            collection_id: the id of the collection from the resource path

        Returns:
            The item that was created or None if item collection.
        """
        ...

    @abc.abstractmethod
    def update_item(
        self, cat_path: str, collection_id: str, item_id: str, item: Item, workspace: str, **kwargs
    ) -> Optional[Union[stac.Item, Response]]:
        """Perform a complete update on an existing item.

        Called with `PUT /catalogs/{cat_path}/collections/{collection_id}/items`. It is expected
        that this item already exists.  The update should do a diff against the
        saved item and perform any necessary updates.  Partial updates are not
        supported by the transactions extension.

        Args:
            cat_path: path of the existing catalog containing the parent collection
            item: the item (must be complete)
            collection_id: the id of the collection from the resource path
            workspace: the requesting workspace.

        Returns:
            The updated item.
        """
        ...

    @abc.abstractmethod
    def delete_item(
        self, cat_path: str, item_id: str, collection_id: str, workspace: str, **kwargs
    ) -> Optional[Union[stac.Item, Response]]:
        """Delete an item from a collection.

        Called with `DELETE /catalogs/{cat_path}/collections/{collection_id}/items/{item_id}`

        Args:
            cat_path: path of the existing catalog containing the parent collection.
            item_id: id of the item.
            collection_id: id of the collection.
            workspace: the requesting workspace.

        Returns:
            The deleted item.
        """
        ...

    @abc.abstractmethod
    def create_collection(
        self, cat_path: str, collection: Collection, workspace: str, **kwargs
    ) -> Optional[Union[stac.Collection, Response]]:
        """Create a new collection.

        Called with `POST /catalogs/{cat_path}/collections`.

        Args:
            cat_path: path of the existing catalog containing the collection
            collection: the collection
            workspace: the requesting workspace

        Returns:
            The collection that was created.
        """
        ...

    @abc.abstractmethod
    def update_collection(
        self, cat_path: str, collection_id: str, collection: Collection, workspace: str, **kwargs
    ) -> Optional[Union[stac.Collection, Response]]:
        """Perform a complete update on an existing collection.

        Called with `PUT /catalogs/{cat_path}/collections/{collection_id}`. It is expected that this
        collection already exists.  The update should do a diff against the saved
        collection and perform any necessary updates.  Partial updates are not
        supported by the transactions extension.

        Args:
            cat_path: path of the existing catalog containing the collection
            collection_id: id of the existing collection to be updated
            collection: the updated collection (must be complete)
            workspace: the requesting workspace

        Returns:
            The updated collection.
        """
        ...

    @abc.abstractmethod
    def delete_collection(
        self, cat_path: str, collection_id: str, workspace: str, **kwargs
    ) -> Optional[Union[stac.Collection, Response]]:
        """Delete a collection.

        Called with `DELETE /catalogs/{cat_path}/collections/{collection_id}`

        Args:
            cat_path: path of the existing catalog containing the collection
            collection_id: id of the collection.
            workspace: the requesting workspace.

        Returns:
            The deleted collection.
        """
        ...

    @abc.abstractmethod
    def create_catalog(
        self, catalog: Catalog, cat_path: str, workspace: str, **kwargs
    ) -> Optional[Union[stac.Catalog, Response]]:
        """Create a new catalog.

        Called with `POST /catalogs/{cat_path}/catalogs`.

        Args:
            catalog: the catalog
            cat_path: path of the existing catalog containing the catalog, can be "root" for top-level catalogs
            workspace: the requesting workspace.

        Returns:
            The catalog that was created.
        """
        ...

    @abc.abstractmethod
    def update_catalog(
        self, cat_path: str, catalog: Catalog, workspace: str, **kwargs
    ) -> Optional[Union[stac.Catalog, Response]]:
        """Perform a complete update on an existing catalog.

        Called with `PUT /catalogs/{cat_path}`. It is expected that this
        catalog already exists.  The update should do a diff against the saved
        catalog and perform any necessary updates.  Partial updates are not
        supported by the transactions extension.

        Args:
            cat_path: path of the existing catalog containing the catalog
            catalog_id: id of the existing catalog to be updated
            catalog: the updated catalog (must be complete)
            workspace: the requesting workspace.

        Returns:
            The updated catalog.
        """
        ...

    @abc.abstractmethod
    def delete_catalog(
        self, cat_path: str, workspace: str, **kwargs
    ) -> Optional[Union[stac.Catalog, Response]]:
        """Delete a catalog.

        Called with `DELETE /catalogs/{cat_path}`

        Args:
            cat_path: path of the catalog.
            workspace: the requesting workspace.

        Returns:
            The deleted catalog.
        """
        ...

    @abc.abstractmethod
    def update_collection_access_policy(
        self, cat_path: str, collection_id: str, access_policy: AccessPolicy, workspace: str, **kwargs
    ) -> None:
        """Perform an update of the access policy for a collection.

        Called with `PUT /catalogs/{cat_path}/catalogs/collections/{collection_id}/access-policy`. It is expected that this
        collection already exists.  The update should perform any necessary updates to the collection access-policy.  
        Partial updates are not supported by the transactions extension.

        Args:
            cat_path: path of the existing catalog containing the collection
            collection_id: id of the existing collection to be updated
            access_policy: the access_policy to apply to the collection.
            workspace: the requesting workspace.

        Returns:
            The updated collection.
        """
        ...

    @abc.abstractmethod
    def update_catalog_access_policy(
        self, cat_path: str, access_policy: AccessPolicy, workspace: str, **kwargs
    ) -> None:
        """Perform an update of the access policy for a catalog.

        Called with `PUT /catalogs/{cat_path}/catalogs/{catalog_id}/access-policy`. It is expected that this
        catalog already exists.  The update should perform any necessary updates to the catalog access-policy.  
        Partial updates are not supported by the transactions extension.

        Args:
            cat_path: path of the existing catalog to be updated
            access_policy: the access_policy to apply to the catalog.
            workspace: the requesting workspace.

        Returns:
            The updated catalog.
        """
        ...


@attr.s  # type:ignore
class AsyncBaseTransactionsClient(abc.ABC):
    """Defines a pattern for implementing the STAC transaction extension."""

    @abc.abstractmethod
    async def create_item(
        self,
        cat_path: str,
        collection_id: str,
        item: Union[Item, ItemCollection],
        workspace: str,
        **kwargs,
    ) -> Optional[Union[stac.Item, Response, None]]:
        """Create a new item.

        Called with `POST /catalogs/{cat_path}/collections/{collection_id}/items`.

        Args:
            cat_path: path of the existing catalog containing the parent collection
            item: the item or item collection
            collection_id: the id of the collection from the resource path
            workspace: the requesting workspace.

        Returns:
            The item that was created or None if item collection.
        """
        ...

    @abc.abstractmethod
    async def update_item(
        self, cat_path: str, collection_id: str, item_id: str, item: Item, workspace: str, **kwargs
    ) -> Optional[Union[stac.Item, Response]]:
        """Perform a complete update on an existing item.

        Called with `PUT /catalogs/{cat_path}/collections/{collection_id}/items`. It is expected
        that this item already exists.  The update should do a diff against the
        saved item and perform any necessary updates. Partial updates are not
        supported by the transactions extension.

        Args:
            cat_path: path of the existing catalog containing the parent collection
            collection_id: the id of the collection from the resource path
            item_id: id of the existing item to be updated
            item: the item (must be complete)
            workspace: the requesting workspace.

        Returns:
            The updated item.
        """
        ...

    @abc.abstractmethod
    async def delete_item(
        self, cat_path: str, item_id: str, collection_id: str, workspace: str, **kwargs
    ) -> Optional[Union[stac.Item, Response]]:
        """Delete an item from a collection.

        Called with `DELETE /catalogs/{cat_path}/collections/{collection_id}/items/{item_id}`

        Args:
            cat_path: path of the existing catalog containing the parent collection
            item_id: id of the item.
            collection_id: id of the collection.
            workspace: the requesting workspace.

        Returns:
            The deleted item.
        """
        ...

    @abc.abstractmethod
    async def create_collection(
        self, cat_path: str, collection: Collection, workspace: str, **kwargs
    ) -> Optional[Union[stac.Collection, Response]]:
        """Create a new collection.

        Called with `POST /catalogs/{cat_path}/collections`.

        Args:
            cat_path: path of the existing catalog containing the collection
            collection: the collection
            workspace: the requesting workspace.

        Returns:
            The collection that was created.
        """
        ...

    @abc.abstractmethod
    async def update_collection(
        self, cat_path: str, collection_id: str, collection: Collection, workspace: str, **kwargs
    ) -> Optional[Union[stac.Collection, Response]]:
        """Perform a complete update on an existing collection.

        Called with `PUT /catalogs/{cat_path}/collections/{collection_id}`. It is expected that this item
        already exists.  The update should do a diff against the saved collection and
        perform any necessary updates.  Partial updates are not supported by the
        transactions extension.

        Args:
            cat_path: path of the existing catalog containing the collection
            collection_id: id of the existing collection to be updated
            collection: the updated collection (must be complete)
            workspace: the requesting workspace.

        Returns:
            The updated collection.
        """
        ...

    @abc.abstractmethod
    async def delete_collection(
        self, cat_path: str, collection_id: str, workspace: str, **kwargs
    ) -> Optional[Union[stac.Collection, Response]]:
        """Delete a collection.

        Called with `DELETE /catalogs/{cat_path}/collections/{collection_id}`

        Args:
            cat_path: path of the existing catalog containing the collection
            collection_id: id of the collection.
            workspace: the requesting workspace.

        Returns:
            The deleted collection.
        """
        ...

    @abc.abstractmethod
    async def create_catalog(
        self, cat_path: str, catalog: Catalog, workspace: str, **kwargs
    ) -> Optional[Union[stac.Catalog, Response]]:
        """Create a new catalog.

        Called with `POST /catalogs/{cat_path}/catalogs`.

        Args:
            cat_path: path of the existing catalog containing the catalog
            catalog: the catalog
            workspace: the requesting workspace.

        Returns:
            The catalog that was created.
        """
        ...

    @abc.abstractmethod
    async def update_catalog(
        self, cat_path: str, catalog: Catalog, workspace: str, **kwargs
    ) -> Optional[Union[stac.Catalog, Response]]:
        """Perform a complete update on an existing catalog.

        Called with `PUT /catalogs/{cat_path}`. It is expected that this item
        already exists.  The update should do a diff against the saved catalog and
        perform any necessary updates.  Partial updates are not supported by the
        transactions extension.

        Args:
            cat_path: path of the existing catalog containing the catalog
            catalog: the updated catalog (must be complete)
            workspace: the requesting workspace.

        Returns:
            The updated catalog.
        """
        ...

    @abc.abstractmethod
    async def delete_catalog(
        self, cat_path: str, workspace: str, **kwargs
    ) -> Optional[Union[stac.Catalog, Response]]:
        """Delete a catalog.

        Called with `DELETE /catalogs/{cat_path}`

        Args:
            cat_path: path of the catalog.
            workspace: the requesting workspace.

        Returns:
            The deleted catalog.
        """
        ...

    @abc.abstractmethod
    def update_collection_access_policy(
        self, cat_path: str, collection_id: str, access_policy: AccessPolicy, workspace: str, **kwargs
    ) -> None:
        """Perform an update of the access policy for a collection.

        Called with `PUT /catalogs/{cat_path}/collections/{collection_id}/access-policy`. It is expected that this
        collection already exists.  The update should perform any necessary updates to the collection access-policy.  
        Partial updates are not supported by the transactions extension.

        Args:
            cat_path: path of the existing catalog containing the collection
            collection_id: id of the existing collection to be updated
            access_policy: the access_policy to apply to the collection.
            workspace: the requesting workspace.

        Returns:
            The updated collection.
        """
        ...

    @abc.abstractmethod
    def update_catalog_access_policy(
        self, cat_path: str, access_policy: AccessPolicy, workspace: str, **kwargs
    ) -> None:
        """Perform an update of the access policy for a catalog.

        Called with `PUT /catalogs/{cat_path}/access-policy`. It is expected that this
        catalog already exists.  The update should perform any necessary updates to the catalog access-policy.  

        Args:
            cat_path: path of the existing catalog to be updated
            access_policy: the access_policy to apply to the catalog.
            workspace: the requesting workspace.

        Returns:
            The updated catalog.
        """
        ...


@attr.s
class LandingPageMixin(abc.ABC):
    """Create a STAC landing page (GET /)."""

    stac_version: str = attr.ib(default=STAC_VERSION)
    landing_page_id: str = attr.ib(default=api_settings.stac_fastapi_landing_id)
    title: str = attr.ib(default=api_settings.stac_fastapi_title)
    description: str = attr.ib(default=api_settings.stac_fastapi_description)

    def _landing_page(
        self,
        base_url: str,
        conformance_classes: List[str],
        extension_schemas: List[str],
    ) -> stac.LandingPage:
        landing_page = stac.LandingPage(
            type="Catalog",
            id=self.landing_page_id,
            title=self.title,
            description=self.description,
            stac_version=self.stac_version,
            conformsTo=conformance_classes,
            links=[
                {
                    "rel": Relations.self.value,
                    "type": MimeTypes.json.value,
                    "href": base_url,
                },
                {
                    "rel": Relations.root.value,
                    "type": MimeTypes.json.value,
                    "href": base_url,
                },
                {
                    "rel": Relations.data.value,
                    "type": MimeTypes.json.value,
                    "href": urljoin(base_url, "collections"),
                },
                {
                    "rel": Relations.conformance.value,
                    "type": MimeTypes.json.value,
                    "title": "STAC/OGC conformance classes implemented by this server",
                    "href": urljoin(base_url, "conformance"),
                },
                {
                    "rel": Relations.search.value,
                    "type": MimeTypes.geojson.value,
                    "title": "STAC search",
                    "href": urljoin(base_url, "search"),
                    "method": "GET",
                },
                {
                    "rel": Relations.search.value,
                    "type": MimeTypes.geojson.value,
                    "title": "STAC search",
                    "href": urljoin(base_url, "search"),
                    "method": "POST",
                },
            ],
            stac_extensions=extension_schemas,
        )

        return landing_page


@attr.s  # type:ignore
class BaseCoreClient(LandingPageMixin, abc.ABC):
    """Defines a pattern for implementing STAC api core endpoints.

    Attributes:
        extensions: list of registered api extensions.
    """

    base_conformance_classes: List[str] = attr.ib(
        factory=lambda: BASE_CONFORMANCE_CLASSES
    )
    extensions: List[ApiExtension] = attr.ib(default=attr.Factory(list))
    post_request_model = attr.ib(default=None)

    @post_request_model.validator
    def _deprecate_post_model(self, attribute, value):
        """Check and raise warning if `post_request_model` is set."""
        if value is not None:
            warnings.warn(
                "`post_request_model` attribute is deprecated and will be removed in 3.1",
                DeprecationWarning,
            )

    def __attrs_post_init__(self):
        """Set default value for post_request_model."""
        self.post_request_model = self.post_request_model or BaseSearchPostRequest

    def conformance_classes(self) -> List[str]:
        """Generate conformance classes by adding extension conformance to base
        conformance classes."""
        base_conformance_classes = self.base_conformance_classes.copy()

        for extension in self.extensions:
            extension_classes = getattr(extension, "conformance_classes", [])
            base_conformance_classes.extend(extension_classes)

        return list(set(base_conformance_classes))

    def extension_is_enabled(self, extension: str) -> bool:
        """Check if an api extension is enabled."""
        return any([type(ext).__name__ == extension for ext in self.extensions])

    def list_conformance_classes(self):
        """Return a list of conformance classes, including implemented extensions."""
        base_conformance = BASE_CONFORMANCE_CLASSES

        for extension in self.extensions:
            extension_classes = getattr(extension, "conformance_classes", [])
            base_conformance.extend(extension_classes)

        return base_conformance

    def landing_page(self, **kwargs) -> stac.LandingPage:
        """Landing page.

        Called with `GET /`.

        Returns:
            API landing page, serving as an entry point to the API.
        """
        request: Request = kwargs["request"]
        base_url = get_base_url(request)

        landing_page = self._landing_page(
            base_url=base_url,
            conformance_classes=self.conformance_classes(),
            extension_schemas=[],
        )

        # Add Queryables link
        if self.extension_is_enabled("FilterExtension"):
            landing_page["links"].append(
                {
                    "rel": Relations.queryables.value,
                    "type": MimeTypes.jsonschema.value,
                    "title": "Queryables",
                    "href": urljoin(base_url, "queryables"),
                }
            )

        # Add Aggregation links
        if self.extension_is_enabled("AggregationExtension"):
            landing_page["links"].extend(
                [
                    {
                        "rel": "aggregate",
                        "type": "application/json",
                        "title": "Aggregate",
                        "href": urljoin(base_url, "aggregate"),
                    },
                    {
                        "rel": "aggregations",
                        "type": "application/json",
                        "title": "Aggregations",
                        "href": urljoin(base_url, "aggregations"),
                    },
                ]
            )

        # Add Collections links
        collections = self.all_collections(request=kwargs["request"])

        for collection in collections["collections"]:
            landing_page["links"].append(
                {
                    "rel": Relations.child.value,
                    "type": MimeTypes.json.value,
                    "title": collection.get("title") or collection.get("id"),
                    "href": urljoin(base_url, f"collections/{collection['id']}"),
                }
            )

        # Add OpenAPI URL
        landing_page["links"].append(
            {
                "rel": Relations.service_desc.value,
                "type": MimeTypes.openapi.value,
                "title": "OpenAPI service description",
                "href": str(request.url_for("openapi")),
            }
        )

        # Add human readable service-doc
        landing_page["links"].append(
            {
                "rel": Relations.service_doc.value,
                "type": MimeTypes.html.value,
                "title": "OpenAPI service documentation",
                "href": str(request.url_for("swagger_ui_html")),
            }
        )

        return stac.LandingPage(**landing_page)

    def conformance(self, **kwargs) -> stac.Conformance:
        """Conformance classes.

        Called with `GET /conformance`.

        Returns:
            Conformance classes which the server conforms to.
        """
        return stac.Conformance(conformsTo=self.conformance_classes())

    @abc.abstractmethod
    def post_search(
        self, search_request: BaseSearchPostRequest, workspaces: Optional[List[str]], cat_path: str = None, **kwargs
    ) -> stac.ItemCollection:
        """Cross catalog search (POST).

        Called with `POST /catalogs/{cat_path}/search`.

        Args:
            search_request: search request parameters.
            workspaces: list of workspaces to search.
            cat_path: path of the catalog to search.

        Returns:
            ItemCollection containing items which match the search criteria.
        """
        ...

    @abc.abstractmethod
    def get_search(
        self,
        cat_path: str,
        collections: Optional[List[str]] = None,
        ids: Optional[List[str]] = None,
        bbox: Optional[BBox] = None,
        intersects: Optional[Geometry] = None,
        datetime: Optional[DateTimeType] = None,
        limit: Optional[int] = 10,
        **kwargs,
    ) -> stac.ItemCollection:
        """Cross catalog search (GET).

        Called with `GET /catalogs/{cat_path}/search`.

        Returns:
            ItemCollection containing items which match the search criteria.
        """
        ...

    @abc.abstractmethod
    def get_item(self, cat_path: str, item_id: str, collection_id: str, workspaces: Optional[List[str]], **kwargs) -> stac.Item:
        """Get item by id.

        Called with `GET /catalogs/{cat_path}/collections/{collection_id}/items/{item_id}`.

        Args:
            cat_path: Path of the catalog.
            item_id: Id of the item.
            collection_id: Id of the collection.
            workspaces: list of workspaces to search.

        Returns:
            Item.
        """
        ...

    @abc.abstractmethod
    def all_collections(self, **kwargs) -> stac.Collections:
        """Get all available collections.

        Called with `GET /collections`.

        Returns:
            A list of collections.
        """
        ...

    @abc.abstractmethod
    def get_collection(self, cat_path: str, collection_id: str, workspaces: Optional[List[str]], **kwargs) -> stac.Collection:
        """Get collection by id.

        Called with `GET /catalogs/{cat_path}/collections/{collection_id}`.

        Args:
            cat_path: Path of the catalog.
            collection_id: Id of the collection.
            workspaces: list of workspaces to search.

        Returns:
            Collection.
        """
        ...

    @abc.abstractmethod
    def all_catalogs(self, **kwargs) -> stac.Catalogs:
        """Get all available catalogs.

        Called with `GET /catalogs`.

        Returns:
            A list of catalogs.
        """
        ...

    @abc.abstractmethod
    def get_catalog(self, cat_path: str, catalog_id: str, **kwargs) -> stac.Catalog:
        """Get catalog by id.

        Called with `GET /catalogs/{cat_path}/catalogs/{catalog_id}`.

        Args:
            cat_path: Path of the catalog.
            catalog_id: Id of the catalog.

        Returns:
            Catalog.
        """
        ...

    @abc.abstractmethod
    def item_collection(
        self,
        cat_path: str,
        collection_id: str,
        workspaces: Optional[List[str]], 
        bbox: Optional[BBox] = None,
        datetime: Optional[DateTimeType] = None,
        limit: int = 10,
        token: str = None,
        **kwargs,
    ) -> stac.ItemCollection:
        """Get all items from a specific collection.

        Called with `GET /catalogs/{cat_path}/collections/{collection_id}/items`

        Args:
            cat_path: Path of the catalog.
            collection_id: id of the collection.
            workspaces: list of workspaces to search.
            bbox: bounding box to filter items.
            datetime: datetime to filter items.
            limit: number of items to return.
            token: pagination token.

        Returns:
            An ItemCollection.
        """
        ...


@attr.s  # type:ignore
class AsyncBaseCoreClient(LandingPageMixin, abc.ABC):
    """Defines a pattern for implementing STAC api core endpoints.

    Attributes:
        extensions: list of registered api extensions.
    """

    base_conformance_classes: List[str] = attr.ib(
        factory=lambda: BASE_CONFORMANCE_CLASSES
    )
    extensions: List[ApiExtension] = attr.ib(default=attr.Factory(list))
    post_request_model = attr.ib(default=None)

    @post_request_model.validator
    def _deprecate_post_model(self, attribute, value):
        """Check and raise warning if `post_request_model` is set."""
        if value is not None:
            warnings.warn(
                "`post_request_model` attribute is deprecated and will be removed in 3.1",
                DeprecationWarning,
            )

    def __attrs_post_init__(self):
        """Set default value for post_request_model."""
        self.post_request_model = self.post_request_model or BaseSearchPostRequest

    def conformance_classes(self) -> List[str]:
        """Generate conformance classes by adding extension conformance to base
        conformance classes."""
        conformance_classes = self.base_conformance_classes.copy()

        for extension in self.extensions:
            extension_classes = getattr(extension, "conformance_classes", [])
            conformance_classes.extend(extension_classes)

        return list(set(conformance_classes))

    def extension_is_enabled(self, extension: str) -> bool:
        """Check if an api extension is enabled."""
        return any([type(ext).__name__ == extension for ext in self.extensions])

    async def landing_page(self, **kwargs) -> stac.LandingPage:
        """Landing page.

        Called with `GET /`.

        Returns:
            API landing page, serving as an entry point to the API.
        """
        request: Request = kwargs["request"]
        base_url = get_base_url(request)

        landing_page = self._landing_page(
            base_url=base_url,
            conformance_classes=self.conformance_classes(),
            extension_schemas=[],
        )

        # Add Queryables link
        if self.extension_is_enabled("FilterExtension"):
            landing_page["links"].append(
                {
                    "rel": Relations.queryables.value,
                    "type": MimeTypes.jsonschema.value,
                    "title": "Queryables",
                    "href": urljoin(base_url, "queryables"),
                    "method": "GET",
                }
            )

        # Add Aggregation links
        if self.extension_is_enabled("AggregationExtension"):
            landing_page["links"].extend(
                [
                    {
                        "rel": "aggregate",
                        "type": "application/json",
                        "title": "Aggregate",
                        "href": urljoin(base_url, "aggregate"),
                    },
                    {
                        "rel": "aggregations",
                        "type": "application/json",
                        "title": "Aggregations",
                        "href": urljoin(base_url, "aggregations"),
                    },
                ]
            )

        # Add Collections links
        collections = await self.all_collections(request=kwargs["request"])

        for collection in collections["collections"]:
            landing_page["links"].append(
                {
                    "rel": Relations.child.value,
                    "type": MimeTypes.json.value,
                    "title": collection.get("title") or collection.get("id"),
                    "href": urljoin(base_url, f"collections/{collection['id']}"),
                }
            )

        # Add OpenAPI URL
        landing_page["links"].append(
            {
                "rel": Relations.service_desc.value,
                "type": MimeTypes.openapi.value,
                "title": "OpenAPI service description",
                "href": str(request.url_for("openapi")),
            }
        )

        # Add human readable service-doc
        landing_page["links"].append(
            {
                "rel": Relations.service_doc.value,
                "type": MimeTypes.html.value,
                "title": "OpenAPI service documentation",
                "href": str(request.url_for("swagger_ui_html")),
            }
        )

        return stac.LandingPage(**landing_page)

    async def conformance(self, **kwargs) -> stac.Conformance:
        """Conformance classes.

        Called with `GET /conformance`.

        Returns:
            Conformance classes which the server conforms to.
        """
        return stac.Conformance(conformsTo=self.conformance_classes())

    @abc.abstractmethod
    async def post_search(
        self, search_request: BaseSearchPostRequest, **kwargs
    ) -> stac.ItemCollection:
        """Cross catalog search (POST).

        Called with `POST /search`.

        Args:
            search_request: search request parameters.

        Returns:
            ItemCollection containing items which match the search criteria.
        """
        ...

    @abc.abstractmethod
    async def get_search(
        self,
        collections: Optional[List[str]] = None,
        ids: Optional[List[str]] = None,
        bbox: Optional[BBox] = None,
        intersects: Optional[Geometry] = None,
        datetime: Optional[DateTimeType] = None,
        limit: Optional[int] = 10,
        **kwargs,
    ) -> stac.ItemCollection:
        """Cross catalog search (GET).

        Called with `GET /search`.

        Returns:
            ItemCollection containing items which match the search criteria.
        """
        ...

    @abc.abstractmethod
    async def get_item(self, cat_path: str, item_id: str, collection_id: str, workspaces: Optional[List[str]], **kwargs) -> stac.Item:
        """Get item by id.

        Called with `GET /catalogs/{cat_path}/collections/{collection_id}/items/{item_id}`.

        Args:
            cat_path: Path of the catalog.
            item_id: Id of the item.
            collection_id: Id of the collection.
            workspaces: list of workspaces to search.

        Returns:
            Item.
        """
        ...

    @abc.abstractmethod
    async def all_collections(self, **kwargs) -> stac.Collections:
        """Get all available collections.

        Called with `GET /collections`.

        Returns:
            A list of collections.
        """
        ...

    @abc.abstractmethod
    async def get_collection(self, cat_path: str, collection_id: str, workspaces: Optional[List[str]], **kwargs) -> stac.Collection:
        """Get collection by id.

        Called with `GET /catalogs/{cat_path}/collections/{collection_id}`.

        Args:
            cat_path: Path of the catalog.
            collection_id: Id of the collection.
            workspaces: list of workspaces to search.

        Returns:
            Collection.
        """
        ...

    @abc.abstractmethod
    def all_catalogs(self, **kwargs) -> stac.Catalogs:
        """Get all available catalogs.

        Called with `GET /catalogs`.

        Returns:
            A list of catalogs.
        """
        ...

    @abc.abstractmethod
    def get_catalog(self, cat_path: str, catalog_id: str, workspaces: Optional[List[str]], **kwargs) -> stac.Catalog:
        """Get catalog by id.

        Called with `GET /catalogs/{cat_path}/catalogs/{catalog_id}`.

        Args:
            cat_path: Path of the catalog.
            catalog_id: Id of the catalog.
            workspaces: list of workspaces to search.

        Returns:
            Catalog.
        """
        ...

    @abc.abstractmethod
    async def item_collection(
        self,
        cat_path: str,
        collection_id: str,
        workspaces: Optional[List[str]], 
        bbox: Optional[BBox] = None,
        datetime: Optional[DateTimeType] = None,
        limit: int = 10,
        token: str = None,
        **kwargs,
    ) -> stac.ItemCollection:
        """Get all items from a specific collection.

        Called with `GET /catalogs/{cat_path}/collections/{collection_id}/items`

        Args:
            cat_path: Path of the catalog.
            collection_id: id of the collection.
            workspaces: list of workspaces to search.
            bbox: bounding box to filter items.
            datetime: datetime to filter items.
            limit: number of items to return.
            token: pagination token.

        Returns:
            An ItemCollection.
        """
        ...
