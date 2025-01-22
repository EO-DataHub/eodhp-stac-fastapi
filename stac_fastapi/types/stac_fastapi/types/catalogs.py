from typing import List, Optional

from pydantic import model_validator

from stac_pydantic.catalog import Catalog
from stac_pydantic.api.links import Links
from stac_pydantic.links import Relations
from stac_pydantic.shared import StacBaseModel


class Catalogs(StacBaseModel):
    """
    https://github.com/radiantearth/stac-api-spec/tree/v1.0.0/ogcapi-features#endpoints
    https://github.com/radiantearth/stac-api-spec/tree/v1.0.0/ogcapi-features#collections-collections
    """

    links: Links
    catalogs: List[Catalog]
    numberMatched: Optional[int] = None
    numberReturned: Optional[int] = None

    @model_validator(mode="after")
    def required_links(self) -> "Catalogs":
        links_rel = []
        for link in self.links.root:
            links_rel.append(link.rel)

        required_rels = [Relations.root, Relations.self]

        for rel in required_rels:
            assert (
                rel in links_rel
            ), f"STAC API Catalogs conform Catalogs pages must include a `{rel}` link."

        return self