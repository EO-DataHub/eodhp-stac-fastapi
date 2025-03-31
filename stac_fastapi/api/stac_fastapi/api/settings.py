import os

CACHE_CONTROL_HEADERS = os.getenv("CACHE_CONTROL_HEADERS", "max-age=300, stale-while-revalidate=300")
CACHE_CONTROL_CATALOGS = os.getenv("CACHE_CONTROL_CATALOGS", "supported-datasets")
CACHE_CONTROL_CATALOGS_LIST = CACHE_CONTROL_CATALOGS.split(',')