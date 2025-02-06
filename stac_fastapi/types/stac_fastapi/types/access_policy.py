"""Access Policy Types"""

import sys
from typing import Any, Dict, List, Literal, Optional, Union

from stac_pydantic.shared import BBox

# Avoids a Pydantic error:
# TypeError: You should use `typing_extensions.TypedDict` instead of
# `typing.TypedDict` with Python < 3.12.0.  Without it, there is no way to
# differentiate required and optional fields when subclassed.
if sys.version_info < (3, 12, 0):
    from typing_extensions import TypedDict
else:
    from typing import TypedDict

class AccessPolicy(TypedDict, total=False):
    """Metadata Access Policy."""

    public: bool