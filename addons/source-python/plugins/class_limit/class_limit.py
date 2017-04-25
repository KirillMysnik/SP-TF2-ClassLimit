# =============================================================================
# >> IMPORTS
# =============================================================================
# Python
import json
from random import choice

# Source.Python
from auth.manager import auth_manager
from engines.server import global_vars
from engines.sound import Sound
from events import Event
from filters.players import PlayerIter
from listeners import OnLevelInit
from loggers import LogManager
from messages import SayText2, TextMsg, VGUIMenu
from players.dictionary import PlayerDictionary
from players.entity import Player

# Class Limit
from .core.cvars import cvar_logging_areas, cvar_logging_level
from .core.paths import CLASS_LIMIT_CFG_PATH
from .core.strings import common_strings, insert_chat_tag
from .info import info


# =============================================================================
# >> FUNCTIONS
# =============================================================================
def get_server_file(path):
    server_path = path.dirname() / (path.namebase + "_server" + path.ext)
    if server_path.isfile():
        return server_path
    return path


def reload_limits_file():
    global limits, last_loaded_limits_file

    for path in (CLASS_LIMIT_CFG_PATH / "limits" / "maps").files('*.json'):
        if global_vars.map_name.startswith(path.namebase):
            break
    else:
        path = get_server_file(
            CLASS_LIMIT_CFG_PATH / "limits" / "default.json")

    with open(path) as f:
        limits = json.load(f)

    last_loaded_limits_file = path


def get_team_size_and_class_quantities(team):
    team_size = 0
    player_classes = {key: 0 for key in range(1, 10)}

    for player in PlayerIter(TEAM_NAMES[team]):
        balanced_player = balanced_players[player.index]
        if balanced_player.player_class not in CLASS_NAME_BY_ID:
            continue

        team_size += 1
        player_classes[balanced_player.player_class] += 1

    return team_size, player_classes


def is_class_full(player_class, player_class_size, team_size):
    class_name = CLASS_NAME_BY_ID[player_class]
    if class_name not in limits:
        return False

    limit_info = limits[class_name]
    limit_type = limit_info.get('type', "percentage")
    limit = limit_info.get('limit', 100)

    if limit_type not in LIMIT_FUNCTIONS:
        logger.log_warning(
            "Unknown limit type '{}' for class '{}' in file {}".format(
                limit_type, class_name, last_loaded_limits_file))

        limit_type = 'absolute'

    limit_func = LIMIT_FUNCTIONS[limit_type]
    try:
        ok = limit_func(player_class_size, team_size, limit)
    except ArithmeticError:
        return False

    return not ok


def get_substitute_class(player_classes, team_size):
    min_class_size = min(player_classes.values())
    available_classes = []

    for player_class, class_size in player_classes.items():
        if class_size == min_class_size:
            available_classes.append(player_class)

    available_classes = list(filter(
        lambda player_class: not is_class_full(
            player_class, player_classes[player_class], team_size),
        available_classes))

    if not available_classes:
        logger.log_warning(
            "Can't pick spare class for a player! Classes:\n{}".format(
                "\n".join(
                    "{} - {}".format(
                        CLASS_NAME_BY_ID[player_classes], class_size
                    ) for player_class, class_size in player_classes.values()
                )
            )
        )
        return None

    return choice(available_classes)


def get_spare_class(team):
    team_size, player_classes = get_team_size_and_class_quantities(team)
    return get_substitute_class(player_classes, team_size)


# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
BYPASS_PERMISSION_BASE = "class_limit.bypass"
VGUI_PANEL_NAMES = {2: 'class_red', 3: 'class_blue'}
TEAM_NAMES = {2: 'red', 3: 'blue'}
CLASS_NAME_BY_ID = {
    1: 'scout',
    2: 'sniper',
    3: 'soldier',
    4: 'demo',
    5: 'medic',
    6: 'heavy',
    7: 'pyro',
    8: 'spy',
    9: 'engineer',
}
CLASS_ID_BY_NAME = {name: id_ for id_, name in CLASS_NAME_BY_ID.items()}
LIMIT_FUNCTIONS = {
    'percentage': lambda player_class_size, team_size, limit: (
        player_class_size == 1 or  # Always allow at least 1 player
        player_class_size / team_size * 100 <= limit
    ),
    'absolute': lambda player_class_size, team_size, limit: (
        player_class_size <= limit)
}

logger = LogManager(info.name, cvar_logging_level, cvar_logging_areas)

limits = None
last_loaded_limits_file = None
reload_limits_file()

msg_not_allowed = TextMsg(common_strings['not_allowed'])
msg_you_were_switched = SayText2(insert_chat_tag(
    common_strings['you_were_switched']))

snd_not_allowed = Sound("common/wpn_denyselect.wav")


# =============================================================================
# >> CLASSES
# =============================================================================
class BalancedPlayer:
    def __init__(self, index):
        self.player = Player(index)

    def get_player_class(self):
        return self.player.get_property_uchar("m_PlayerClass.m_iClass")

    def set_player_class(self, player_class):
        self.player.set_property_uchar(
            "m_PlayerClass.m_iClass", player_class)

        self.player.set_property_uchar(
            "m_Shared.m_iDesiredPlayerClass", player_class)

    player_class = property(get_player_class, set_player_class)

    def force_class_change(self, player_class):
        self.player_class = player_class
        if self.player.team in VGUI_PANEL_NAMES:
            VGUIMenu(
                VGUI_PANEL_NAMES[self.player.team]).send(self.player.index)

    def is_authorized_to_bypass(self, player_class):
        permission = (
            BYPASS_PERMISSION_BASE + '.' + CLASS_NAME_BY_ID[player_class])

        return auth_manager.is_player_authorized(self.player.index, permission)


# =============================================================================
# >> PLAYER DICTIONARIES
# =============================================================================
balanced_players = PlayerDictionary(BalancedPlayer)


# =============================================================================
# >> EVENTS
# =============================================================================
@Event('player_changeclass')
def on_player_changeclass(game_event):
    player_class = game_event['class']
    if player_class not in CLASS_NAME_BY_ID:
        return

    balanced_player = balanced_players.from_userid(game_event['userid'])
    team = balanced_player.player.team
    if team not in TEAM_NAMES:
        return

    if balanced_player.is_authorized_to_bypass(player_class):
        return

    team_size, player_classes = get_team_size_and_class_quantities(team)
    if not is_class_full(
            player_class, player_classes[player_class] + 1, team_size):

        return

    new_player_class = get_substitute_class(player_classes, team_size)
    if new_player_class is None:
        return

    balanced_player.force_class_change(new_player_class)
    msg_not_allowed.send(balanced_player.player.index)
    snd_not_allowed.play(balanced_player.player.index)


@Event('player_death')
def on_player_death(game_event):
    balanced_player = balanced_players.from_userid(game_event['userid'])
    team = balanced_player.player.team
    if team not in TEAM_NAMES:
        return

    player_class = balanced_player.player_class
    if player_class not in CLASS_NAME_BY_ID:
        return

    if balanced_player.is_authorized_to_bypass(player_class):
        return

    team_size, player_classes = get_team_size_and_class_quantities(team)
    if not is_class_full(
            player_class, player_classes[player_class], team_size):

        return

    new_player_class = get_substitute_class(player_classes, team_size)
    if new_player_class is None:
        return

    balanced_player.force_class_change(new_player_class)
    msg_you_were_switched.send(balanced_player.player.index)


# =============================================================================
# >> LISTENERS
# =============================================================================
@OnLevelInit
def listener_on_level_init(map_name):
    reload_limits_file()
