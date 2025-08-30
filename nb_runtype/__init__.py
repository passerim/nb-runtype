"""
nb-runtype: Automatic runtime type validation for functions in Jupyter notebooks, with flexible configuration and per-function exclusion.

Example:
    from nb_runtype import enable_runtype

    # Enable type validation for all new functions
    enable_runtype()

    # This function should be defined in a subsequent cell so it will be automatically validated
    def add(x: int, y: int) -> int:
        return x + y
"""

from nb_runtype.runtype import (
    RuntypeError,
    disable_runtype,
    enable_runtype,
    get_runtype_config,
    is_runtype_enabled,
    no_runtype,
)

__all__ = [
    "enable_runtype",
    "disable_runtype",
    "no_runtype",
    "get_runtype_config",
    "is_runtype_enabled",
    "RuntypeError",
]
