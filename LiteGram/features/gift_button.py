from hook_utils import find_class

from LiteGram.data.constants import Keys
from LiteGram.utils.xposed_utils import BaseHook

BUTTON_GIFT = 1


class ChatActivityEnterViewCreateGiftButtonHook(BaseHook):
    def before_hooked_method(self, param):
        if self.is_enabled():
            param.setResult(None)


class ChatActivityEnterViewUpdateGiftButtonHook(BaseHook):
    def before_hooked_method(self, param):
        if self.is_enabled():
            param.setResult(None)


class ChatActivityEnterViewAddGiftViewHook(BaseHook):
    def before_hooked_method(self, param):
        if not self.is_enabled():
            return
        if not param.args:
            return
        try:
            view = param.args[0]
            if hasattr(view, "getContentDescription"):
                desc = str(view.getContentDescription() or "").lower()
                if "gift" in desc:
                    param.setResult(None)
        except Exception:
            pass


class ChatActivityShowGiftButtonHook(BaseHook):
    def before_hooked_method(self, param):
        if self.is_enabled():
            param.setResult(None)


class ChatActivityChannelButtonsLayoutShowButtonHook(BaseHook):
    def before_hooked_method(self, param):
        if self.is_enabled():
            try:
                if param.args[0] == BUTTON_GIFT:
                    param.setResult(None)
            except IndexError:
                pass


def register_gift_button(plugin) -> None:
    ChatActivityEnterView = find_class("org.telegram.ui.Components.ChatActivityEnterView")
    if ChatActivityEnterView:
        try:
            plugin.hook_all_methods(ChatActivityEnterView, "createGiftButton", ChatActivityEnterViewCreateGiftButtonHook(plugin, Keys.hide_bottom_gift_button))
        except Exception:
            pass
        try:
            plugin.hook_all_methods(ChatActivityEnterView, "updateGiftButton", ChatActivityEnterViewUpdateGiftButtonHook(plugin, Keys.hide_bottom_gift_button))
        except Exception:
            pass
        try:
            plugin.hook_all_methods(ChatActivityEnterView, "addView", ChatActivityEnterViewAddGiftViewHook(plugin, Keys.hide_bottom_gift_button))
        except Exception:
            pass

    ChatActivity = find_class("org.telegram.ui.ChatActivity")
    if ChatActivity:
        try:
            plugin.hook_all_methods(ChatActivity, "showGiftButton", ChatActivityShowGiftButtonHook(plugin, Keys.hide_bottom_gift_button))
        except Exception:
            pass

    try:
        ChatActivityChannelButtonsLayout = find_class("org.telegram.ui.Components.chat.layouts.ChatActivityChannelButtonsLayout")
        if ChatActivityChannelButtonsLayout:
            plugin.hook_all_methods(
                ChatActivityChannelButtonsLayout, "showButton", ChatActivityChannelButtonsLayoutShowButtonHook(plugin, Keys.hide_bottom_gift_button)
            )
    except Exception:
        pass
