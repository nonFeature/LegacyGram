from hook_utils import find_class

from LiteGram.data.constants import Keys
from LiteGram.utils.xposed_utils import BaseHook


class MessagesControllerRichEditorAvailableHook(BaseHook):
    def __init__(self, plugin):
        super().__init__(plugin, Keys.hide_articles_editor)

    def before_hooked_method(self, param):
        if not self.is_enabled():
            return
        param.setResult(False)


def register_hide_articles(plugin) -> None:
    try:
        from LiteGram.utils.utils import get_client_version, parse_version

        if parse_version(get_client_version()) < (12, 9, 0):
            return

        MessagesController = find_class("org.telegram.messenger.MessagesController")
        if MessagesController is not None:
            plugin.hook_all_methods(MessagesController, "richEditorAvailable", MessagesControllerRichEditorAvailableHook(plugin))
    except Exception:
        pass
