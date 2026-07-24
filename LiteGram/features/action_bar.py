from android.view import View
from hook_utils import find_class, get_private_field

from LiteGram.data.constants import Keys
from LiteGram.utils.xposed_utils import BaseHook

"""
A LITTLE EXPLANATION
There's a separate code paths for addSubItem and lazilyAddSubItems
addSubItem(id, ...) -> creates view -> adds to popupLayout -> returns View
    If we return null: caller stores null -> later setVisibility() from showSubItem -> app crashed

lazilyAddSubItem(id, ...) -> stores in lazyList -> later layoutLazyItems() creates view
    If we return null: lazyMap has null -> ... -> crashed

So we just View.GONE, instead setResult(None)

We also hook setSubItemShown to remove some elements, that sets visibility to true
And hook for topics (boost group button, report button)
"""

# from ProfileActivity class
CALL_ITEM = 15  # Start Live Stream / Video Chat | NOT CALLS IN DM!
GIFT_PREMIUM = 38
CHANNEL_STORIES = 39  # Archived Stories
ADD_SHORTCUT_PROFILE = 14  # Add to home screen

# from ChatActivity class
ADD_SHORTCUT_CHAT = 24
BOOST_GROUP = 29

# from TopicsFragment class
BOOST_GROUP_TOPIC = 14

_ITEM_KEY_MAP = {
    CALL_ITEM: Keys.hide_action_bar_live_stream,
    GIFT_PREMIUM: Keys.hide_action_bar_send_gift,
    CHANNEL_STORIES: Keys.hide_action_bar_archived_stories,
    ADD_SHORTCUT_PROFILE: Keys.hide_action_bar_add_shortcut,
    ADD_SHORTCUT_CHAT: Keys.hide_action_bar_add_shortcut,
    BOOST_GROUP: Keys.hide_action_bar_boost_group,
}

R_drawable = find_class("org.telegram.messenger.R$drawable")
MSG_REPORT_ID = getattr(R_drawable, "msg_report", -1) if R_drawable else -1


def _is_report(args) -> bool:
    if not args:
        return False
    item_id = args[0]
    if len(args) > 1 and MSG_REPORT_ID > 0 and args[1] == MSG_REPORT_ID:
        return True
    if len(args) > 2 and args[2] is not None:
        txt = str(args[2]).lower()
        if "report" in txt or "пожалова" in txt:
            return True
    if item_id == 21:
        return True
    return False


def _should_hide_menu_item(plugin, args) -> bool:
    if not args:
        return False
    item_id = args[0]

    if _is_report(args):
        return bool(plugin.get_setting(Keys.hide_action_bar_report, False))

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
    TopicsFragment = find_class("org.telegram.ui.TopicsFragment")
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
    if TopicsFragment:
        try:
            plugin.hook_all_methods(TopicsFragment, "updateChatInfo", TopicsFragmentUpdateChatInfoHook(plugin))
        except Exception:
            pass
