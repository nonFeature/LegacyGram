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

Also we hook includeStories and isArchivedOnlyStoriesView to return False when hide_stories_tab is active,
which prevents story and archived story tabs from being generated in self profile (myProfile) and normal profiles.
"""

TL_profileTabGifts = find_class("org.telegram.tgnet.TLRPC$TL_profileTabGifts")
TL_profileTabPosts = find_class("org.telegram.tgnet.TLRPC$TL_profileTabPosts")


class SharedMediaLayoutHook(BaseHook):
    def __init__(self, plugin, is_constructor: bool):
        super().__init__(plugin)
        self.is_constructor = is_constructor

    def _get_active_flags(self) -> tuple[bool, bool]:
        return (
            bool(self.plugin.get_setting(Keys.hide_gifts_tab, False)),
            bool(self.plugin.get_setting(Keys.hide_stories_tab, False)),
        )

    def _get_info_objects(self, param) -> tuple[Any, Any]:
        if self.is_constructor:
            try:
                return param.args[5], param.args[6]
            except IndexError:
                return None, None
        else:
            instance = param.thisObject
            chat_info = get_private_field(instance, "info")
            user_info = get_private_field(instance, "userInfo")
            return chat_info, user_info

    def before_hooked_method(self, param):
        gifts, stories = self._get_active_flags()
        if not gifts and not stories:
            return

        chat_info, user_info = self._get_info_objects(param)
        for target in (chat_info, user_info):
            if gifts:
                remove_gifts(target)
            if stories:
                remove_stories(target)

    def after_hooked_method(self, param):
        gifts, stories = self._get_active_flags()
        if not gifts and not stories:
            return

        try:
            instance = param.thisObject
            tab_strip = get_private_field(instance, "scrollSlidingTextTabStrip")
            is_self = is_self_profile(instance)

            removable_tab_ids = set()
            if stories:
                removable_tab_ids.update((8, 9, 13))
            if gifts:
                removable_tab_ids.add(14)
            if gifts and stories and is_self:
                removable_tab_ids.update((11, 12))

            rebuild_profile_tabs(tab_strip, removable_tab_ids)

            if tab_strip is not None:
                if tab_strip.getTabsCount() == 0:
                    clear_empty_media_selection(instance, tab_strip)
                else:
                    restore_media_page_visibility(instance)
                    ensure_valid_tab_selected(instance, tab_strip)
        except Exception:
            pass


class SharedMediaLayoutSetInfoHook(BaseHook):
    def before_hooked_method(self, param):
        gifts = bool(self.plugin.get_setting(Keys.hide_gifts_tab, False))
        stories = bool(self.plugin.get_setting(Keys.hide_stories_tab, False))

        if not gifts and not stories:
            return

        try:
            info_obj = param.args[0]
        except IndexError:
            return

        if gifts:
            remove_gifts(info_obj)
        if stories:
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


def is_self_profile(instance) -> bool:
    try:
        return bool(instance.isSelf())
    except Exception:
        pass
    try:
        profile_activity = get_private_field(instance, "profileActivity")
        return bool(getattr(profile_activity, "myProfile", False))
    except Exception:
        return False


def rebuild_profile_tabs(tab_strip, removable_tab_ids: set[int] | None = None) -> None:
    if tab_strip is None or not removable_tab_ids:
        return
    if not any(tab_strip.hasTab(tab_id) for tab_id in removable_tab_ids):
        return

    current_tab_id = tab_strip.getCurrentTabId()
    tab_ids = list(tab_strip.getTabIds())
    cached_tabs = tab_strip.removeTabs()
    first_available_tab = None

    for tab_id in tab_ids:
        if tab_id in removable_tab_ids:
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

    if current_tab_id in removable_tab_ids:
        tab_strip.scrollTo(first_available_tab)
    else:
        tab_strip.selectTabWithId(current_tab_id, 1.0)


def ensure_valid_tab_selected(instance, tab_strip=None) -> None:
    try:
        if tab_strip is None:
            tab_strip = get_private_field(instance, "scrollSlidingTextTabStrip")
        if tab_strip is None or tab_strip.getTabsCount() == 0:
            return

        current_tab_id = tab_strip.getCurrentTabId()
        if not tab_strip.hasTab(current_tab_id):
            first_tab_id = tab_strip.getFirstTabId()
            if first_tab_id != -1:
                tab_strip.setInitialTabId(first_tab_id)
                current_tab_id = first_tab_id

        media_pages = get_private_field(instance, "mediaPages")
        if media_pages is not None and len(media_pages) > 0 and media_pages[0] is not None:
            current_selected = media_pages[0].selectedType
            if current_selected != current_tab_id and current_tab_id != -1:
                set_private_field(media_pages[0], "selectedType", jint(current_tab_id))
                instance.switchToCurrentSelectedMode(False)
    except Exception:
        pass


def clear_empty_media_selection(instance, tab_strip) -> None:
    """Clear stale media selection after both profile tabs were removed."""
    try:
        tab_strip.setInitialTabId(-1)
    except Exception:
        pass

    try:
        media_pages = get_private_field(instance, "mediaPages")
        saved_container = get_private_field(instance, "savedMessagesContainer")
        if media_pages is not None:
            for index in range(2):
                page = media_pages[index]
                if page is None:
                    continue
                set_private_field(page, "selectedType", -1)
                if saved_container is not None and saved_container.getParent() == page:
                    saved_container.chatActivity.onRemoveFromParent()
                    page.removeView(saved_container)
                page.setVisibility(8)
    except Exception:
        pass

    try:
        instance.setVisibility(8)
    except Exception:
        pass


def restore_media_page_visibility(instance) -> None:
    try:
        media_pages = get_private_field(instance, "mediaPages")
        if media_pages is not None:
            for index in range(2):
                page = media_pages[index]
                if page is not None:
                    page.setVisibility(0)
        instance.setVisibility(0)
    except Exception:
        pass


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
            info_hook = SharedMediaLayoutSetInfoHook(plugin)
            plugin.hook_all_methods(SharedMediaLayout, "setChatInfo", info_hook)
            plugin.hook_all_methods(SharedMediaLayout, "setUserInfo", info_hook)
        except Exception:
            pass

        try:
            return_false_hook = ReturnFalseHook(plugin, Keys.hide_stories_tab)
            plugin.hook_all_methods(SharedMediaLayout, "includeStories", return_false_hook)
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
