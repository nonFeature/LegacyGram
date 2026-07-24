from typing import Any

from hook_utils import find_class, get_private_field, set_private_field
from java import jint

from LiteGram.data.constants import Keys
from LiteGram.utils.xposed_utils import BaseHook

"""
EXPLANATION
code from updateTabs, but it's looks same in SharedMediaLayout constructor
boolean hasGifts = giftsContainer != null && (userInfo != null && userInfo.stargifts_count > 0 || info != null && info.stargifts_count > 0);
hasGifts = giftsContainer NOT null AND (userInfo NOT null AND userInfo.stargifts_count > 0 OR info not null AND info.stargifts_count > 0)
hasGifts = true AND (true AND false OR false) -> true AND (false) -> false -> tab won't be appeared

Similar to gifts, we change 'stories_pinned_available' and 'stories' collection to prevent appearing tab.
also we hook setChatInfo and setUserInfo which move you to stories tab sometimes
... .setInitialTabId(... ? TAB_ARCHIVED_STORIES : TAB_STORIES);
for weird StoriesCollections logic we just set visibility to false (I'm a little lazy to check they logic, it's working fine)

Also we hook includeStories, isStoriesView, and isArchivedOnlyStoriesView to return False when hide_stories_tab is active,
which prevents story and archived story tabs from being generated in self profile (myProfile) and normal profiles.
"""

TL_profileTabGifts = find_class("org.telegram.tgnet.TLRPC$TL_profileTabGifts")
TL_profileTabPosts = find_class("org.telegram.tgnet.TLRPC$TL_profileTabPosts")


class SharedMediaLayoutHook(BaseHook):
    def __init__(self, plugin, is_constructor: bool):
        super().__init__(plugin)
        self.is_constructor = is_constructor

    def _get_info_objects(self, param) -> tuple[Any, Any]:
        if self.is_constructor:
            try:
                return param.args[5], param.args[6]
            except IndexError:
                return None, None
        else:
            # updateTabs: info stored in instance fields
            instance = param.thisObject
            chat_info = get_private_field(instance, "info")  # TLRPC.ChatFull
            user_info = get_private_field(instance, "userInfo")  # TLRPC.UserFull
            return chat_info, user_info

    def before_hooked_method(self, param):
        gifts = bool(self.plugin.get_setting(Keys.hide_gifts_tab, False))
        stories = bool(self.plugin.get_setting(Keys.hide_stories_tab, False))

        if not gifts and not stories:
            return

        chat_info, user_info = self._get_info_objects(param)

        for target in [chat_info, user_info]:
            if gifts:
                remove_gifts(target)
            if stories:
                remove_stories(target)

    def after_hooked_method(self, param):
        stories = bool(self.plugin.get_setting(Keys.hide_stories_tab, False))

        if not stories:
            return

        try:
            rebuild_tabs_without_stories(get_private_field(param.thisObject, "scrollSlidingTextTabStrip"))
        except Exception:
            pass


class SharedMediaLayoutSetInfoHook(BaseHook):
    def before_hooked_method(self, param):
        if not self.is_enabled():
            return
        try:
            info_obj = param.args[0]
        except IndexError:
            return
        remove_stories(info_obj)


class ReturnFalseHook(BaseHook):
    def before_hooked_method(self, param):
        if not self.is_enabled():
            return
        param.setResult(False)


# not the best how you can do it, but still fine
class ProfileStoriesCollectionTabsSetVisibilityHook(BaseHook):
    def before_hooked_method(self, param):
        if not self.is_enabled():
            return
        try:
            if param.args[0]:  # boolean visibility
                param.args[0] = False
        except IndexError:
            pass


def remove_gifts(obj: Any):
    if obj:
        set_private_field(obj, "stargifts_count", jint(0))
        main_tab = get_private_field(obj, "main_tab")

        if TL_profileTabGifts and isinstance(main_tab, TL_profileTabGifts):
            set_private_field(obj, "main_tab", None)


def remove_stories(obj: Any):
    if obj:
        set_private_field(obj, "stories_pinned_available", False)
        set_private_field(obj, "stories", None)
        main_tab = get_private_field(obj, "main_tab")

        if TL_profileTabPosts and isinstance(main_tab, TL_profileTabPosts):
            set_private_field(obj, "main_tab", None)


def rebuild_tabs_without_stories(tab_strip) -> None:
    if tab_strip is None:
        return
    if not tab_strip.hasTab(8) and not tab_strip.hasTab(9) and not tab_strip.hasTab(13):
        return

    current_tab_id = tab_strip.getCurrentTabId()
    removed_tab_ids = {8, 9, 13}
    tab_ids = list(tab_strip.getTabIds())
    cached_tabs = tab_strip.removeTabs()
    first_available_tab = None

    for tab_id in tab_ids:
        if tab_id in removed_tab_ids:
            continue

        view = cached_tabs.get(tab_id)
        tab_text = ""
        try:
            tab_text = view.getText()
        except Exception:
            pass
        tab_strip.addTextTab(tab_id, tab_text, cached_tabs)
        if first_available_tab is None:
            first_available_tab = tab_id

    tab_strip.finishAddingTabs()

    if first_available_tab is None:
        return

    if current_tab_id in removed_tab_ids:
        tab_strip.scrollTo(first_available_tab)
    else:
        tab_strip.selectTabWithId(current_tab_id, 1.0)


def register_media_layout(plugin) -> None:
    SharedMediaLayout = find_class("org.telegram.ui.Components.SharedMediaLayout")
    if SharedMediaLayout:
        try:
            constructor_hook = SharedMediaLayoutHook(plugin, is_constructor=True)
            plugin.hook_all_constructors(SharedMediaLayout, constructor_hook)
        except Exception:
            pass

        try:
            update_tabs_hook = SharedMediaLayoutHook(plugin, is_constructor=False)
            plugin.hook_all_methods(SharedMediaLayout, "updateTabs", update_tabs_hook)
        except Exception:
            pass

        try:
            info_hook = SharedMediaLayoutSetInfoHook(plugin, Keys.hide_stories_tab)
            plugin.hook_all_methods(SharedMediaLayout, "setChatInfo", info_hook)
            plugin.hook_all_methods(SharedMediaLayout, "setUserInfo", info_hook)
        except Exception:
            pass

        try:
            return_false_hook = ReturnFalseHook(plugin, Keys.hide_stories_tab)
            plugin.hook_all_methods(SharedMediaLayout, "includeStories", return_false_hook)
            plugin.hook_all_methods(SharedMediaLayout, "isStoriesView", return_false_hook)
            plugin.hook_all_methods(SharedMediaLayout, "isArchivedOnlyStoriesView", return_false_hook)
        except Exception:
            pass

    ProfileStoriesCollectionTabs = find_class("org.telegram.ui.ProfileStoriesCollectionTabs")
    if ProfileStoriesCollectionTabs:
        try:
            visibility_hook = ProfileStoriesCollectionTabsSetVisibilityHook(plugin, Keys.hide_stories_tab)
            plugin.hook_all_methods(ProfileStoriesCollectionTabs, "setVisibility", visibility_hook)
        except Exception:
            pass
