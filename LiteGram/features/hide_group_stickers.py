from hook_utils import find_class

from LiteGram.data.constants import Keys
from LiteGram.utils.xposed_utils import BaseHook


class HideGroupStickerSetHook(BaseHook):
    def __init__(self, plugin):
        super().__init__(plugin, Keys.hide_group_stickers)

    def before_hooked_method(self, param):
        if not self.is_enabled():
            return
        param.setResult(None)


def register_hide_group_stickers(plugin) -> None:
    try:
        MediaDataController = find_class("org.telegram.messenger.MediaDataController")
        if MediaDataController is not None:
            plugin.hook_all_methods(MediaDataController, "getGroupStickerSetById", HideGroupStickerSetHook(plugin))
    except Exception:
        pass
