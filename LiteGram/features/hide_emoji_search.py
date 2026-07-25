from hook_utils import find_class

from LiteGram.data.constants import Keys
from LiteGram.utils.xposed_utils import BaseHook

# ============================================================
# Class resolution
# ============================================================

StickerCategoriesListView = find_class("org.telegram.ui.Components.StickerCategoriesListView")


# ============================================================
# Hooks
# ============================================================


class UpdateCategoriesShownHook(BaseHook):
    def __init__(self, plugin):
        super().__init__(plugin, Keys.hide_emoji_search)

    def before_hooked_method(self, param):
        if not self.is_enabled():
            return
        if param.args and len(param.args) > 0:
            try:
                param.args[0] = False
            except Exception:
                pass


class StickerCategoriesVisibilityHook(BaseHook):
    def __init__(self, plugin):
        super().__init__(plugin, Keys.hide_emoji_search)

    def after_hooked_method(self, param):
        if not self.is_enabled():
            return
        try:
            param.thisObject.setVisibility(8)  # GONE
        except Exception:
            pass


# ============================================================
# Registration
# ============================================================


def register_hide_emoji_search(plugin):
    if StickerCategoriesListView:
        try:
            plugin.hook_all_methods(StickerCategoriesListView, "updateCategoriesShown", UpdateCategoriesShownHook(plugin))
        except Exception:
            pass
        try:
            vis_hook = StickerCategoriesVisibilityHook(plugin)
            plugin.hook_all_methods(StickerCategoriesListView, "onAttachedToWindow", vis_hook)
            plugin.hook_all_constructors(StickerCategoriesListView, vis_hook)
        except Exception:
            pass
