# =============================================================================
# >> IMPORTS
# =============================================================================
# Custom Package
from controlled_cvars import ControlledConfigManager
from controlled_cvars.handlers import int_handler

# Class Limit
from ..info import info
from .strings import config_strings


# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
with ControlledConfigManager(
        info.name + "/main", cvar_prefix='class_limit_') as config_manager:

    config_manager.section(config_strings['section logging'])
    cvar_logging_level = config_manager.controlled_cvar(
        int_handler,
        "logging_level",
        default=4,
        description=config_strings['logging_level'],
    )
    cvar_logging_areas = config_manager.controlled_cvar(
        int_handler,
        "logging_areas",
        default=5,
        description=config_strings['logging_areas'],
    )
