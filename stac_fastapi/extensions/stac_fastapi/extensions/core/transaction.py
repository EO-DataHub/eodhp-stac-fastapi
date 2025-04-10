"""Transaction extension."""

from typing import List, Optional, Type, Union

import attr
from fastapi import APIRouter, Body, FastAPI, Path
from stac_pydantic import Catalog, Collection, Item, ItemCollection
from stac_pydantic.shared import MimeTypes
from starlette.responses import JSONResponse, Response
from typing_extensions import Annotated

from stac_fastapi.api.models import CatalogUri, GetCatalogUri, BaseCatalogUri, CreateCatalogUri, CollectionUri, ItemUri
from stac_fastapi.api.routes import create_async_endpoint
from stac_fastapi.types.access_policy import AccessPolicy
from stac_fastapi.types.config import ApiSettings
from stac_fastapi.types.core import AsyncBaseTransactionsClient, BaseTransactionsClient
from stac_fastapi.types.extension import ApiExtension
from stac_fastapi.types.search import APIRequest


@attr.s
class PostItem(CollectionUri):
    """Create Item."""

    workspace: str = attr.ib()
    item: Annotated[Union[Item, ItemCollection], Body()] = attr.ib(default=None)

@attr.s
class PutItem(ItemUri):
    """Update Item."""

    workspace: str = attr.ib()
    item: Annotated[Item, Body()] = attr.ib(default=None)

@attr.s
class DeleteItem(ItemUri):
    """Delete Item."""

    workspace: str = attr.ib()

@attr.s
class PostCollection(CreateCatalogUri):
    """Create Collection."""

    workspace: str = attr.ib()
    collection: Annotated[Collection, Body()] = attr.ib(default=None)

@attr.s
class PutCollection(CollectionUri):
    """Update Collection."""

    workspace: str = attr.ib()
    collection: Annotated[Collection, Body()] = attr.ib(default=None)

@attr.s
class PutCollectionAccessControl(CollectionUri):
    """Update Collection."""

    workspace: str = attr.ib()
    access_policy: Union[AccessPolicy] = attr.ib(default=Body(None))

@attr.s
class DeleteCollection(CollectionUri):
    """Delete Collection."""

    workspace: str = attr.ib()

@attr.s
class PostRootCatalog(APIRequest):
    """Create Root Catalog."""

    workspace: str = attr.ib()
    catalog: Annotated[Catalog, Body()] = attr.ib(default=None)

@attr.s
class PostCatalog(CreateCatalogUri):
    """Create Catalog."""

    workspace: str = attr.ib()
    catalog: Annotated[Catalog, Body()] = attr.ib(default=None)

@attr.s
class PutCatalog(CatalogUri):
    """Update Catalog."""

    workspace: str = attr.ib()
    catalog: Annotated[Catalog, Body()] = attr.ib(default=None)

@attr.s
class PutCatalogAccessControl(CatalogUri):
    """Update Catalog."""

    workspace: str = attr.ib()
    access_policy: Union[AccessPolicy] = attr.ib(default=Body(None))

@attr.s
class DeleteCatalog(CatalogUri):
    """Delete Catalog."""

    workspace: str = attr.ib()

@attr.s
class TransactionExtension(ApiExtension):
    """Transaction Extension.

    The transaction extension adds several endpoints which allow the creation,
    deletion, and updating of items and collections:
        POST /collections
        PUT /collections/{collection_id}
        DELETE /collections/{collection_id}
        POST /collections/{collection_id}/items
        PUT /collections/{collection_id}/items
        DELETE /collections/{collection_id}/items

    https://github.com/stac-api-extensions/transaction
    https://github.com/stac-api-extensions/collection-transaction

    Attributes:
        client: CRUD application logic

    """

    client: Union[AsyncBaseTransactionsClient, BaseTransactionsClient] = attr.ib()
    settings: ApiSettings = attr.ib()
    conformance_classes: List[str] = attr.ib(
        factory=lambda: [
            "https://api.stacspec.org/v1.0.0/ogcapi-features/extensions/transaction",
            "https://api.stacspec.org/v1.0.0/collections/extensions/transaction",
        ]
    )
    schema_href: Optional[str] = attr.ib(default=None)
    router: APIRouter = attr.ib(factory=APIRouter)
    response_class: Type[Response] = attr.ib(default=JSONResponse)

    def register_create_item(self):
        """Register create item endpoint (POST /collections/{collection_id}/items)."""
        self.router.add_api_route(
            name="Create Item",
            path="/catalogs/{cat_path:path}/collections/{collection_id}/items",
            status_code=201,
            response_model=Item if self.settings.enable_response_models else None,
            responses={
                201: {
                    "content": {
                        MimeTypes.geojson.value: {},
                    },
                    "model": Item,
                }
            },
            response_class=self.response_class,
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
            methods=["POST"],
            endpoint=create_async_endpoint(self.client.create_item, PostItem),
        )

    def register_update_item(self):
        """Register update item endpoint (PUT
        /collections/{collection_id}/items/{item_id})."""
        self.router.add_api_route(
            name="Update Item",
            path="/catalogs/{cat_path:path}/collections/{collection_id}/items/{item_id}",
            response_model=Item if self.settings.enable_response_models else None,
            responses={
                200: {
                    "content": {
                        MimeTypes.geojson.value: {},
                    },
                    "model": Item,
                }
            },
            response_class=self.response_class,
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
            methods=["PUT"],
            endpoint=create_async_endpoint(self.client.update_item, PutItem),
        )

    def register_delete_item(self):
        """Register delete item endpoint (DELETE
        /collections/{collection_id}/items/{item_id})."""
        self.router.add_api_route(
            name="Delete Item",
            path="/catalogs/{cat_path:path}/collections/{collection_id}/items/{item_id}",
            response_model=Item if self.settings.enable_response_models else None,
            responses={
                200: {
                    "content": {
                        MimeTypes.geojson.value: {},
                    },
                    "model": Item,
                }
            },
            response_class=self.response_class,
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
            methods=["DELETE"],
            endpoint=create_async_endpoint(self.client.delete_item, DeleteItem),
        )

    def register_patch_item(self):
        """Register patch item endpoint (PATCH
        /collections/{collection_id}/items/{item_id})."""
        raise NotImplementedError

    def register_create_collection(self):
        """Register create collection endpoint (POST /collections)."""
        self.router.add_api_route(
            name="Create Collection",
            path="/catalogs/{cat_path:path}/collections",
            status_code=201,
            response_model=Collection if self.settings.enable_response_models else None,
            responses={
                201: {
                    "content": {
                        MimeTypes.json.value: {},
                    },
                    "model": Collection,
                }
            },
            response_class=self.response_class,
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
            methods=["POST"],
            endpoint=create_async_endpoint(self.client.create_collection, PostCollection),
        )

    def register_update_collection(self):
        """Register update collection endpoint (PUT /collections/{collection_id})."""
        self.router.add_api_route(
            name="Update Collection",
            path="/catalogs/{cat_path:path}/collections/{collection_id}",
            response_model=Collection if self.settings.enable_response_models else None,
            responses={
                200: {
                    "content": {
                        MimeTypes.json.value: {},
                    },
                    "model": Collection,
                }
            },
            response_class=self.response_class,
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
            methods=["PUT"],
            endpoint=create_async_endpoint(self.client.update_collection, PutCollection),
        )


    def register_delete_collection(self):
        """Register delete collection endpoint (DELETE /collections/{collection_id})."""
        self.router.add_api_route(
            name="Delete Collection",
            path="/catalogs/{cat_path:path}/collections/{collection_id}",
            response_model=Collection if self.settings.enable_response_models else None,
            responses={
                200: {
                    "content": {
                        MimeTypes.json.value: {},
                    },
                    "model": Collection,
                }
            },
            response_class=self.response_class,
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
            methods=["DELETE"],
            endpoint=create_async_endpoint(self.client.delete_collection, DeleteCollection),
        )

    def register_create_catalog(self):
        """Register create Catalog endpoint (POST /catalogs/{cat_path}/catalogs)."""
        self.router.add_api_route(
            name="Create Catalog",
            path="/catalogs/{cat_path:path}/catalogs",
            status_code=201,
            response_model=Catalog if self.settings.enable_response_models else None,
            responses={
                201: {
                    "content": {
                        MimeTypes.json.value: {},
                    },
                    "model": Catalog,
                }
            },
            response_class=self.response_class,
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
            methods=["POST"],
            endpoint=create_async_endpoint(self.client.create_catalog, PostCatalog),
        )

    def register_create_root_catalog(self):
        """Register create root Catalog endpoint (POST /catalogs)."""
        self.router.add_api_route(
            name="Create Root Catalog",
            path="/catalogs",
            status_code=201,
            response_model=Catalog if self.settings.enable_response_models else None,
            responses={
                201: {
                    "content": {
                        MimeTypes.json.value: {},
                    },
                    "model": Catalog,
                }
            },
            response_class=self.response_class,
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
            methods=["POST"],
            endpoint=create_async_endpoint(self.client.create_catalog, PostRootCatalog),
        )

    def register_update_catalog(self):
        """Register update catalog endpoint (PUT /collections/{collection_id})."""
        self.router.add_api_route(
            name="Update Catalog",
            path="/catalogs/{cat_path:path}",
            response_model=Catalog if self.settings.enable_response_models else None,
            responses={
                200: {
                    "content": {
                        MimeTypes.json.value: {},
                    },
                    "model": Catalog,
                }
            },
            response_class=self.response_class,
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
            methods=["PUT"],
            endpoint=create_async_endpoint(self.client.update_catalog, PutCatalog),
        )


    def register_update_collection_access_control(self):
        """Register update collection endpoint (PUT /collections/{collection_id})."""
        self.router.add_api_route(
            name="Update Collection Access Policy",
            path="/catalogs/{cat_path:path}/collections/{collection_id}/access-policy",
            response_model=Collection if self.settings.enable_response_models else None,
            responses={
                200: {
                    "content": {
                        MimeTypes.json.value: {},
                    },
                    "model": Collection,
                }
            },
            response_class=self.response_class,
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
            methods=["PUT"],
            endpoint=create_async_endpoint(self.client.update_collection_access_policy, PutCollectionAccessControl),
        )

    def register_update_catalog_access_control(self):
        """Register update catalog endpoint (PUT /collections/{collection_id})."""
        self.router.add_api_route(
            name="Update Catalog Access Policy",
            path="/catalogs/{cat_path:path}/access-policy",
            response_model=Catalog if self.settings.enable_response_models else None,
            responses={
                200: {
                    "content": {
                        MimeTypes.json.value: {},
                    },
                    "model": Catalog,
                }
            },
            response_class=self.response_class,
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
            methods=["PUT"],
            endpoint=create_async_endpoint(self.client.update_catalog_access_policy, PutCatalogAccessControl),
        )

    def register_delete_catalog(self):
        """Register delete catalog endpoint (DELETE /catalogs/{cat_path})."""
        self.router.add_api_route(
            name="Delete Catalog",
            path="/catalogs/{cat_path:path}",
            response_model=Catalog if self.settings.enable_response_models else None,
            responses={
                200: {
                    "content": {
                        MimeTypes.json.value: {},
                    },
                    "model": Catalog,
                }
            },
            response_class=self.response_class,
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
            methods=["DELETE"],
            endpoint=create_async_endpoint(self.client.delete_catalog, DeleteCatalog),
        )

    def register_patch_collection(self):
        """Register patch collection endpoint (PATCH /collections/{collection_id})."""
        raise NotImplementedError

    def register(self, app: FastAPI) -> None:
        """Register the extension with a FastAPI application.

        Args:
            app: target FastAPI application.

        Returns:
            None
        """
        self.router.prefix = app.state.router_prefix
        self.register_create_item()
        self.register_update_item()
        self.register_delete_item()
        self.register_update_catalog_access_control()
        self.register_update_collection_access_control()
        self.register_create_collection()
        self.register_update_collection()
        self.register_delete_collection()
        self.register_create_catalog()
        self.register_create_root_catalog()
        self.register_update_catalog()
        
        self.register_delete_catalog()
        app.include_router(self.router, tags=["Transaction Extension"])
