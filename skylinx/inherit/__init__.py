"""
skylinx/inherit/

Extension infrastructure for Skylinx — model field injection and CBV replacement.

Key public symbols re-exported here for convenience:

    from skylinx.inherit import SkylinxViewInheritMixin   # view extension
    from skylinx.inherit import SkylinxModelBase           # model metaclass
    from skylinx.inherit import INJECTION_MAP              # migration routing
    from skylinx.inherit import VIEW_REGISTRY              # registered views
"""

from skylinx.inherit.extension_registry import INJECTION_MAP
from skylinx.inherit.model_inherit import EXTENSION_REGISTRY, SkylinxModelBase
from skylinx.inherit.view_inherit import SkylinxViewInheritMixin
from skylinx.inherit.view_registry import VIEW_REGISTRY

__all__ = [
    "SkylinxViewInheritMixin",
    "SkylinxModelBase",
    "INJECTION_MAP",
    "EXTENSION_REGISTRY",
    "VIEW_REGISTRY",
]
