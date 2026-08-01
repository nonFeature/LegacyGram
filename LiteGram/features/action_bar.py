from android.view import View
from hook_utils import find_class, get_private_field

from LiteGram.data.constants import Keys
from LiteGram.utils.xposed_utils import BaseHook

# ProfileActivity item IDs
ADD_SHORTCUT_PROFILE = 14  # Add to home screen
CALL_ITEM = 15  # Start Live Stream / Video Chat
GIFT_PREMIUM = 38  # Send Gift
CHANNEL_STORIES = 39  # Archived Stories
REPORT_PROFILE = 24  # Report Bot in profile

# ChatActivity item IDs
CLEAR_HISTORY_CHAT = 15  # Clear History / Clear All History in chat
REPORT_CHAT = 21  # Report chat / bot
ADD_SHORTCUT_CHAT = 24  # Add to home screen in chat
BOOST_GROUP = 29  # Boost group

# DialogsActivity / Popup item IDs
CLEAR_HISTORY_DIALOGS = 103  # Clear History in dialogs list

_ITEM_KEY_MAP = {
    CALL_ITEM: Keys.hide_action_bar_live_stream,
    CLEAR_HISTORY_CHAT: Keys.hide_action_bar_clear_history,
    CLEAR_HISTORY_DIALOGS: Keys.hide_action_bar_clear_history,
    REPORT_CHAT: Keys.hide_action_bar_report,
    REPORT_PROFILE: Keys.hide_action_bar_report,
    GIFT_PREMIUM: Keys.hide_action_bar_send_gift,
    CHANNEL_STORIES: Keys.hide_action_bar_archived_stories,
    ADD_SHORTCUT_PROFILE: Keys.hide_action_bar_add_shortcut,
    ADD_SHORTCUT_CHAT: Keys.hide_action_bar_add_shortcut,
    BOOST_GROUP: Keys.hide_action_bar_boost_group,
}


R_drawable = find_class("org.telegram.messenger.R$drawable") or find_class("com.exteragram.messenger.R$drawable")
MSG_CLEAR_ID = getattr(R_drawable, "msg_clear", -1) if R_drawable else -1
MSG_DELETE_ID = getattr(R_drawable, "msg_delete", -1) if R_drawable else -1


def _is_clear_history(args) -> bool:
    if not args:
        return False
    item_id = args[0] if len(args) > 0 else -1

    if isinstance(item_id, int) and item_id in (15, 103):
        return True

    if len(args) > 1:
        icon_id = args[1]
        if isinstance(icon_id, int) and icon_id > 0:
            if (MSG_CLEAR_ID > 0 and icon_id == MSG_CLEAR_ID) or (MSG_DELETE_ID > 0 and icon_id == MSG_DELETE_ID):
                return True

    return False


def _should_hide_menu_item(plugin, args) -> bool:
    if not args:
        return False

    if _is_clear_history(args):
        return bool(plugin.get_setting(Keys.hide_action_bar_clear_history, False))

    item_id = args[0]
    if not isinstance(item_id, int):
        return False

    if item_id == 15:
        if plugin.get_setting(Keys.hide_action_bar_clear_history, False) or plugin.get_setting(Keys.hide_action_bar_live_stream, False):
            return True

    if item_id == 24:
        if plugin.get_setting(Keys.hide_action_bar_report, False) or plugin.get_setting(Keys.hide_action_bar_add_shortcut, False):
            return True

    if item_id in _ITEM_KEY_MAP:
        return bool(plugin.get_setting(_ITEM_KEY_MAP[item_id], False))

    return False


class ActionBarMenuItemAddSubItemHook(BaseHook):
    def after_hooked_method(self, param):
        result = param.getResult()
        if result is None or not param.args:
            return
        if _should_hide_menu_item(self.plugin, param.args):
            result.setVisibility(View.GONE)


class ActionBarMenuItemLazilyAddSubItemHook(BaseHook):
    def after_hooked_method(self, param):
        result = param.getResult()
        if result is None or not param.args:
            return
        if _should_hide_menu_item(self.plugin, param.args):
            result.setVisibility(View.GONE)


# calls showSubItem(id); if show is true
# public void setSubItemShown(int id, boolean show)
class ActionBarMenuItemSetSubItemShownHook(BaseHook):
    def before_hooked_method(self, param):
        if not param.args:
            return
        if _should_hide_menu_item(self.plugin, param.args):
            try:
                param.args[1] = False  # boolean show
            except IndexError:
                pass


class ChatActivityCheckActionBarMenuHook(BaseHook):
    def after_hooked_method(self, param):
        if not self.plugin.get_setting(Keys.hide_action_bar_clear_history, False):
            return
        chat_activity = param.thisObject
        if chat_activity is not None:
            try:
                clear_history_item = get_private_field(chat_activity, "clearHistoryItem")
                if clear_history_item is not None:
                    try:
                        clear_history_item.visibility = 8
                    except Exception:
                        pass
                    view = getattr(clear_history_item, "view", None)
                    if view is not None:
                        view.setVisibility(8)
            except Exception:
                pass


class ItemOptionsAddHook(BaseHook):
    def before_hooked_method(self, param):
        if not self.plugin.get_setting(Keys.hide_action_bar_clear_history, False):
            return
        if _is_clear_history(param.args):
            param.setResult(param.thisObject)


class TopicsFragmentUpdateChatInfoHook(BaseHook):
    def after_hooked_method(self, param):
        instance = param.thisObject
        if self.plugin.get_setting(Keys.hide_action_bar_boost_group, False):
            boost_submenu_field = get_private_field(instance, "boostGroupSubmenu")
            if boost_submenu_field is not None:
                boost_submenu_field.setVisibility(8)
        if self.plugin.get_setting(Keys.hide_action_bar_report, False):
            report_submenu_field = get_private_field(instance, "reportSubmenu")
            if report_submenu_field is not None:
                report_submenu_field.setVisibility(8)


def register_action_bar(plugin) -> None:
    ActionBarMenuItem = find_class("org.telegram.ui.ActionBar.ActionBarMenuItem")
    ChatActivity = find_class("org.telegram.ui.ChatActivity")
    TopicsFragment = find_class("org.telegram.ui.TopicsFragment")
    ItemOptions = find_class("org.telegram.ui.Components.ItemOptions")
    if ActionBarMenuItem:
        try:
            plugin.hook_all_methods(ActionBarMenuItem, "addSubItem", ActionBarMenuItemAddSubItemHook(plugin))
        except Exception:
            pass
        try:
            plugin.hook_all_methods(ActionBarMenuItem, "lazilyAddSubItem", ActionBarMenuItemLazilyAddSubItemHook(plugin))
        except Exception:
            pass
        try:
            plugin.hook_all_methods(ActionBarMenuItem, "setSubItemShown", ActionBarMenuItemSetSubItemShownHook(plugin))
        except Exception:
            pass
    if ChatActivity:
        try:
            plugin.hook_all_methods(ChatActivity, "checkActionBarMenu", ChatActivityCheckActionBarMenuHook(plugin))
        except Exception:
            pass
    if ItemOptions:
        try:
            plugin.hook_all_methods(ItemOptions, "add", ItemOptionsAddHook(plugin))
        except Exception:
            pass
    if TopicsFragment:
        try:
            plugin.hook_all_methods(TopicsFragment, "updateChatInfo", TopicsFragmentUpdateChatInfoHook(plugin))
        except Exception:
            pass
