import time
from typing import Any, Optional

from base_plugin import BasePlugin, HookResult
from ui.bulletin import BulletinHelper

from LiteGram.data.constants import Keys
from LiteGram.features.action_bar import register_action_bar
from LiteGram.features.gift_button import register_gift_button
from LiteGram.features.gift_cards import register_gift_cards
from LiteGram.features.greeting_button import register_greeting_button
from LiteGram.features.hide_ai_features import register_hide_ai_features
from LiteGram.features.hide_articles import register_hide_articles
from LiteGram.features.hide_emoji_search import register_hide_emoji_search
from LiteGram.features.hide_group_stickers import register_hide_group_stickers
from LiteGram.features.hide_premium_features import register_hide_premium_features
from LiteGram.features.media_layout import register_media_layout
from LiteGram.features.premium_badge import register_premium_badge
from LiteGram.features.premium_emoji import filter_response, register_premium_emoji
from LiteGram.features.profile_actions import register_profile_actions
from LiteGram.features.profile_appearance import register_profile_appearance
from LiteGram.features.settings_menu import register_settings_menu
from LiteGram.features.star_rating import register_star_rating
from LiteGram.features.star_reaction import register_star_reaction
from LiteGram.ui.settings import get_main_settings_list
from LiteGram.ui.settings_header import register_settings_header

_PROFILE_GIFT_REQUEST_HOOKS = {
    "TL_users_getFullUser",
    "TL_channels_getFullChannel",
    "TL_messages_getFullChat",
    "TL_contacts_resolveUsername",
    "TL_messages_getDialogs",
    "TL_messages_getPeerDialogs",
    "TL_users_getUsers",
}

_GIFT_SUBSTRING_HOOKS = {"StarGift", "Gifts", "StarGiftUnique"}


class LiteGramPlugin(BasePlugin):
    _instance: Optional["LiteGramPlugin"] = None

    def get_setting(self, key: str, default: Any = False) -> Any:
        if not hasattr(self, "_settings_cache"):
            self._settings_cache = {}

        now = time.monotonic()
        cached = self._settings_cache.get(key)
        if cached is None or (now - cached[1] > 1.0):
            val = super().get_setting(key, default)
            self._settings_cache[key] = (val, now)
            return val
        return cached[0]

    def set_setting(self, key: str, value: Any, reload_settings: bool = False) -> None:
        if hasattr(self, "_settings_cache"):
            self._settings_cache[key] = (value, time.monotonic())
        super().set_setting(key, value, reload_settings)

        if key == Keys.hide_premium_features and value:
            try:
                from hook_utils import find_class

                MessagesController = find_class("org.telegram.messenger.MessagesController")
                if MessagesController:
                    for i in range(4):
                        try:
                            instance = MessagesController.getInstance(i)
                            if instance:
                                field = instance.getClass().getDeclaredField("folderTags")
                                field.setAccessible(True)
                                field.setBoolean(instance, False)
                        except Exception:
                            pass
            except Exception:
                pass

    def on_plugin_load(self) -> None:
        LiteGramPlugin._instance = self
        tl_hooks = [
            "TL_messages_getEmojiStickers",
            "TL_messages_getFeaturedEmojiStickers",
            "TL_messages_getFeaturedStickers",
            "TL_messages_searchEmojiStickerSets",
            "TL_messages_searchStickers",
            "TL_messages_getRecentReactions",
            "TL_messages_getRecentStickers",
            "TL_messages_getStickers",
            "TL_messages_getStickerSet",
        ]
        for name in tl_hooks:
            try:
                self.add_hook(name)
            except Exception:
                pass
        for name in _PROFILE_GIFT_REQUEST_HOOKS:
            try:
                self.add_hook(name)
            except Exception:
                pass
        for name in _GIFT_SUBSTRING_HOOKS:
            try:
                self.add_hook(name, match_substring=True)
            except Exception:
                pass
        self.register_hooks()

    def post_request_hook(self, request_name: str, account: int, response: Any, error: Any) -> HookResult:
        if error is not None or response is None:
            return HookResult()
        if (
            self.get_setting(Keys.hide_premium_emoji_keyboard, False)
            or self.get_setting(Keys.hide_premium_emoji_reactions, False)
            or self.get_setting(Keys.hide_premium_search, False)
            or self.get_setting(Keys.hide_premium_suggestions, False)
            or self.get_setting(Keys.hide_premium_stickers_recent, False)
            or self.get_setting(Keys.hide_premium_stickers_search, False)
            or self.get_setting(Keys.hide_premium_stickers_grid, False)
            or self.get_setting(Keys.hide_group_stickers, False)
        ):
            filter_response(request_name, response)
        if self.get_setting(Keys.hide_gifts_tab, False):
            if self._is_gift_request(request_name):
                self._sanitize_gifts_payload(response)
        return HookResult()

    def on_update_hook(self, update_name: str, account: int, update: Any) -> HookResult:
        if self.get_setting(Keys.hide_gifts_tab, False) and update is not None:
            self._sanitize_gifts_payload(update)
        return HookResult()

    def on_updates_hook(self, container_name: str, account: int, updates: Any) -> HookResult:
        if self.get_setting(Keys.hide_gifts_tab, False) and updates is not None:
            self._sanitize_gifts_payload(updates)
        return HookResult()

    def _is_gift_request(self, name: str) -> bool:
        if name in _PROFILE_GIFT_REQUEST_HOOKS:
            return True
        name_lower = str(name).lower()
        return "gift" in name_lower or "stargift" in name_lower

    @staticmethod
    def _sanitize_gifts_payload(obj, visited=None, depth=0):
        if obj is None or depth > 4 or isinstance(obj, (int, float, str, bool, bytes)):
            return
        if visited is None:
            visited = set()
        try:
            oid = id(obj)
            if oid in visited:
                return
            visited.add(oid)
        except Exception:
            pass
        try:
            for field in ("gifts", "saved_gifts", "profileGifts", "profile_gifts", "profileTabs"):
                container = getattr(obj, field, None)
                if container is not None and hasattr(container, "clear"):
                    container.clear()
            tabs = getattr(obj, "tabs", None)
            if tabs is not None:
                try:
                    if hasattr(tabs, "size") and hasattr(tabs, "remove"):
                        i = tabs.size() - 1
                        while i >= 0:
                            tab = tabs.get(i)
                            if hasattr(tab, "id") and tab.id == 14:
                                tabs.remove(i)
                            i -= 1
                    elif hasattr(tabs, "__iter__"):
                        to_remove = [t for t in tabs if hasattr(t, "id") and t.id == 14]
                        for t in to_remove:
                            try:
                                tabs.remove(t)
                            except Exception:
                                pass
                except Exception:
                    pass
        except Exception:
            pass
        for key in ("users", "chats", "list", "items"):
            try:
                val = getattr(obj, key, None)
                if val is not None and hasattr(val, "__iter__"):
                    for item in val:
                        LiteGramPlugin._sanitize_gifts_payload(item, visited, depth + 1)
            except Exception:
                pass
        for key in ("user", "chat", "full_user", "full_chat", "peer", "data", "result"):
            try:
                LiteGramPlugin._sanitize_gifts_payload(getattr(obj, key, None), visited, depth + 1)
            except Exception:
                pass

    def create_settings(self) -> list[Any]:
        return get_main_settings_list()

    def register_hooks(self) -> None:
        register_action_bar(self)
        register_star_rating(self)
        register_media_layout(self)
        register_settings_menu(self)
        register_gift_button(self)
        register_gift_cards(self)
        register_greeting_button(self)
        register_profile_appearance(self)
        register_profile_actions(self)
        register_premium_emoji(self)
        register_premium_badge(self)
        register_star_reaction(self)
        register_hide_emoji_search(self)
        register_hide_premium_features(self)
        register_hide_ai_features(self)
        register_hide_articles(self)
        register_hide_group_stickers(self)
        register_settings_header(self)

    @classmethod
    def get_instance(cls) -> "LiteGramPlugin":
        if cls._instance is None:
            BulletinHelper.show_error("Error while getting LiteGramPlugin Instance!")
            raise RuntimeError("Error while getting LiteGramPlugin Instance!")
        return cls._instance
