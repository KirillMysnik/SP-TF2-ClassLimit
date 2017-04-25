# =============================================================================
# >> IMPORTS
# =============================================================================
# Source.Python
from colors import Color
from translations.strings import LangStrings

# Map Cycle
from ..info import info


# =============================================================================
# >> FUNCTIONS
# =============================================================================
def insert_chat_tag(message):
    message = message.tokenized(**message.tokens, **COLOR_SCHEME)
    message = common_strings['chat_base'].tokenized(
        message=message, **COLOR_SCHEME)

    return message


# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
# Map color variables in translation files to actual Color instances
COLOR_SCHEME = {
    'color_tag': Color(242, 242, 242),
    'color_highlight': Color(0, 250, 190),
    'color_default': Color(242, 242, 242),
    'color_error': Color(255, 54, 54),
}

common_strings = LangStrings(info.name + "/strings")
config_strings = LangStrings(info.name + "/config")
