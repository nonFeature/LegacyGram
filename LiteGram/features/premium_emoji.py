from hook_utils import find_class, get_private_field

from LiteGram.data.constants import Keys
from LiteGram.main import LiteGramPlugin
from LiteGram.utils.xposed_utils import BaseHook


def safe_find_class(class_name):
    try:
        return find_class(class_name)
    except Exception:
        return None


# ============================================================
# Class resolution
# ============================================================

Emoji = safe_find_class("org.telegram.messenger.Emoji")
EmojiView = safe_find_class("org.telegram.ui.Components.EmojiView")
EmojiGridAdapter = safe_find_class("org.telegram.ui.Components.EmojiView$EmojiGridAdapter")
EmojiSearchAdapter = safe_find_class("org.telegram.ui.Components.EmojiView$EmojiSearchAdapter")
SuggestEmojiView = safe_find_class("org.telegram.ui.Components.SuggestEmojiView")
ArrayList = safe_find_class("java.util.ArrayList")
MessageObject = safe_find_class("org.telegram.messenger.MessageObject")
StickerEmojiCell = safe_find_class("org.telegram.ui.Cells.StickerEmojiCell")
ChatActivityEnterView = safe_find_class("org.telegram.ui.Components.ChatActivityEnterView")
MediaDataController = safe_find_class("org.telegram.messenger.MediaDataController")
EmojiSearchAdapterRunnable = safe_find_class("org.telegram.ui.Components.EmojiView$EmojiSearchAdapter$5")
EmojiTabsStrip = safe_find_class("org.telegram.ui.Components.EmojiTabsStrip")
SelectAnimatedEmojiDialog = safe_find_class("org.telegram.ui.SelectAnimatedEmojiDialog")
CustomEmojiReactionsWindow = safe_find_class("org.telegram.ui.Components.Reactions.CustomEmojiReactionsWindow")
ReactionsContainerLayout = safe_find_class("org.telegram.ui.Components.ReactionsContainerLayout")
StickerCategoriesListView = safe_find_class("org.telegram.ui.Components.StickerCategoriesListView")
SearchBox = safe_find_class("org.telegram.ui.SelectAnimatedEmojiDialog$SearchBox")
Thread = safe_find_class("java.lang.Thread")

# ============================================================
# Module state
# ============================================================


def _init(plugin):
    pass


# ============================================================
# Core checks
# ============================================================


def _is_non_stock(item) -> bool:
    """True if item is a custom (non-stock) emoji.

    Stock emoji = standard Unicode emoji that existed before Telegram Premium.
    Custom emoji = everything else (from emoji packs, stored with document IDs).

    Works for both string entries (recent emoji, search) and TL documents.
    """
    if isinstance(item, str):
        return item.startswith("animated_")
    if MessageObject:
        try:
            return bool(MessageObject.isAnimatedEmoji(item))
        except Exception:
            pass
    return False


def _is_premium_sticker(document) -> bool:
    """True if a sticker document has premium-only animation (video_thumbs type 'f').

    Pure Python — 0 Java calls for normal (free) stickers.
    Falls back to MessageObject.isPremiumSticker only if attr access fails.
    """
    if document is None:
        return False
    try:
        vthumbs = getattr(document, "video_thumbs", None)
        if vthumbs:
            for j in range(vthumbs.size()):
                try:
                    if getattr(vthumbs.get(j), "type", None) == "f":
                        return True
                except Exception:
                    pass
        return False
    except Exception:
        pass
    if MessageObject:
        try:
            return bool(MessageObject.isPremiumSticker(document))
        except Exception:
            pass
    return False


# ============================================================
# Filtering primitives
# ============================================================


def _filter_list(container, *, sub=None, drop_empty=False, drop_non_stock=False, is_sticker=False):
    """Remove premium (and optionally non-stock) items from an ArrayList.

    sub=None           -> items are documents directly
    sub="documents"    -> each item has a .documents sublist
    drop_empty         -> remove items whose sublist becomes empty
    drop_non_stock     -> also remove non-stock custom emoji items
    is_sticker         -> use _is_premium_sticker check (video_thumbs) for leaf docs
    """
    if not container or not ArrayList:
        return 0
    removed = 0
    i = container.size() - 1
    while i >= 0:
        item = container.get(i)
        if sub:
            docs = getattr(item, sub, None)
            if docs is not None:
                _set = getattr(item, "set", None)
                is_emoji_pack = drop_non_stock and _set and getattr(_set, "emojis", False)
                if is_emoji_pack:
                    container.remove(i)
                    removed += 1
                    i -= 1
                    continue
                j = docs.size() - 1
                while j >= 0:
                    doc = docs.get(j)
                    if is_sticker:
                        if _is_premium_sticker(doc):
                            docs.remove(j)
                            removed += 1
                    else:
                        prem = getattr(doc, "premium", None)
                        if prem is not None and bool(prem):
                            docs.remove(j)
                            removed += 1
                    j -= 1
                if drop_empty and docs.size() == 0:
                    container.remove(i)
                    removed += 1
        else:
            obj = container.get(i)
            if drop_non_stock and _is_non_stock(obj):
                container.remove(i)
                removed += 1
            elif is_sticker:
                if _is_premium_sticker(obj):
                    container.remove(i)
                    removed += 1
            elif not drop_non_stock:
                prem = getattr(obj, "premium", None)
                if prem is not None and bool(prem):
                    container.remove(i)
                    removed += 1
        i -= 1
    return removed


def _filter_reactions_list(container):
    """Remove custom emoji reactions (any with documentId or document_id != 0)."""
    if not container:
        return 0
    removed = 0
    i = container.size() - 1
    while i >= 0:
        item = container.get(i)
        doc_id = getattr(item, "documentId", 0) or getattr(item, "document_id", 0)
        if doc_id != 0:
            container.remove(i)
            removed += 1
        i -= 1
    return removed


def _is_featured_premium(pack):
    """Check if a StickerSetCovered is a premium pack."""
    if not pack or not MessageObject:
        return False
    try:
        return bool(MessageObject.isPremiumEmojiPack(pack))
    except Exception:
        pass
    for attr in ("documents", "covers"):
        docs = getattr(pack, attr, None)
        if docs:
            for j in range(docs.size()):
                try:
                    if getattr(docs.get(j), "premium", False):
                        return True
                except Exception:
                    pass
    return False


def _is_featured_non_stock(pack):
    """Check if a StickerSetCovered is a custom emoji pack (no stock emoji)."""
    if not pack:
        return False
    sticker_set = getattr(pack, "set", None)
    if sticker_set:
        try:
            return bool(sticker_set.emojis)
        except Exception:
            pass
    return False


def _filter_featured_sets(sets):
    """Remove premium emoji packs AND custom emoji packs from featured sets."""
    if not sets:
        return 0
    removed = 0
    i = sets.size() - 1
    while i >= 0:
        pack = sets.get(i)
        if _is_featured_premium(pack) or _is_featured_non_stock(pack):
            sets.remove(i)
            removed += 1
        i -= 1
    return removed


def _is_premium_sticker_pack(pack):
    """Check if a StickerSetCovered is a premium sticker pack by its cover."""
    if not pack:
        return False
    cover = getattr(pack, "cover", None)
    if cover and _is_premium_sticker(cover):
        return True
    return False


def _filter_featured_sticker_sets(sets):
    """Remove premium packs from featured sticker sets."""
    if not sets:
        return 0
    removed = 0
    i = sets.size() - 1
    while i >= 0:
        if _is_premium_sticker_pack(sets.get(i)):
            sets.remove(i)
            removed += 1
        i -= 1
    return removed


# ============================================================
# Search-specific filtering
# ============================================================


def _filter_search_results(results):
    """Filter non-stock emoji and premium items from search results."""
    if not results:
        return 0
    removed = 0
    i = results.size() - 1
    while i >= 0:
        r = results.get(i)
        emoji = getattr(r, "emoji", None)
        if emoji is None:
            try:
                emoji = str(r)
            except Exception:
                i -= 1
                continue
        if _is_non_stock(emoji):
            results.remove(i)
            removed += 1
            i -= 1
            continue
        try:
            if getattr(r, "premium", False):
                results.remove(i)
                removed += 1
        except Exception:
            pass
        i -= 1
    return removed


def _reindex_search_sets(sets):
    """Rebuild search sets keeping header-group structure, dropping non-stock + premium."""
    if not sets or not ArrayList:
        return
    rebuilt = ArrayList()
    buffer = ArrayList()
    dirty = False
    for i in range(sets.size()):
        item = sets.get(i)
        if item and getattr(item, "title", None) is not None:
            if buffer.size() > 0:
                rebuilt.add(item)
                for d in range(buffer.size()):
                    rebuilt.add(buffer.get(d))
            buffer = ArrayList()
            continue
        if _is_non_stock(item):
            dirty = True
        else:
            buffer.add(item)
    for d in range(buffer.size()):
        rebuilt.add(buffer.get(d))
    if dirty:
        sets.clear()
        sets.addAll(rebuilt)


def _filter_search_packs(packs_list):
    """Remove custom (non-stock) emoji packs from search packs list."""
    if not packs_list:
        return 0
    removed = 0
    i = packs_list.size() - 1
    while i >= 0:
        pack_info = packs_list.get(i)
        docs = getattr(pack_info, "documents", None)
        if docs:
            _filter_list(docs, drop_non_stock=True)
            if docs.size() == 0:
                packs_list.remove(i)
                removed += 1
        else:
            packs_list.remove(i)
            removed += 1
        i -= 1
    return removed


# ============================================================
# TL response handlers
# ============================================================

HANDLERS = {
    "TL_messages_getFeaturedStickers": lambda r, p: (
        _filter_featured_sticker_sets(getattr(r, "sets", None)) if p.get_setting(Keys.hide_premium_stickers_grid, False) else None
    ),
    "TL_messages_searchStickers": lambda r, p: (
        _filter_list(getattr(r, "stickers", None), is_sticker=True) if p.get_setting(Keys.hide_premium_stickers_search, False) else None
    ),
    "TL_messages_getRecentStickers": lambda r, p: (
        _filter_list(getattr(r, "stickers", None), is_sticker=True) if p.get_setting(Keys.hide_premium_stickers_recent, False) else None
    ),
    "TL_messages_getStickers": lambda r, p: (
        _filter_list(getattr(r, "stickers", None), is_sticker=True) if p.get_setting(Keys.hide_premium_stickers_search, False) else None
    ),
    "TL_messages_getStickerSet": lambda r, p: (
        _filter_list(getattr(r, "documents", None), is_sticker=True) if p.get_setting(Keys.hide_premium_stickers_search, False) else None
    ),
}


def filter_response(request_name, response):
    handler = HANDLERS.get(request_name)
    if handler is None:
        return
    try:
        plugin = LiteGramPlugin.get_instance()
        handler(response, plugin)
    except Exception:
        pass


# ============================================================
# UI hooks — recent emoji
# ============================================================


class BlockNonStockHook(BaseHook):
    """Prevent custom emoji from being added to recents."""

    def before_hooked_method(self, param):
        if not self.is_enabled():
            return
        if not param.args:
            return
        source = param.args[0]
        if isinstance(source, str) and source.startswith("animated_"):
            param.setResult(None)


class FilterRecentEmojiHook(BaseHook):
    """Remove custom emoji from recent emoji list without mutating Telegram's internal cache."""

    def after_hooked_method(self, param):
        if not self.is_enabled():
            return
        recent = param.getResult()
        if not recent or not ArrayList:
            return
        size = recent.size()
        has_non_stock = False
        for i in range(size):
            item = recent.get(i)
            if isinstance(item, str) and item.startswith("animated_"):
                has_non_stock = True
                break
        if not has_non_stock:
            return
        filtered = ArrayList()
        for i in range(size):
            item = recent.get(i)
            if isinstance(item, str):
                if not item.startswith("animated_"):
                    filtered.add(item)
            else:
                filtered.add(item)
        param.setResult(filtered)


# ============================================================
# UI hooks — search
# ============================================================


class FilterSearchResultsHook(BaseHook):
    def before_hooked_method(self, param):
        if not self.is_enabled():
            return
        if not param.args or len(param.args) < 3:
            return
        _filter_search_results(param.args[1])
        _reindex_search_sets(param.args[2])


class FilterSuggestResultsHook(BaseHook):
    def __init__(self, plugin, arg_index, label):
        super().__init__(plugin, Keys.hide_premium_suggestions)
        self._arg_index = arg_index
        self._label = label

    def before_hooked_method(self, param):
        if not self.is_enabled():
            return
        if not param.args or len(param.args) <= self._arg_index:
            return
        target = param.args[self._arg_index]
        if not target:
            return
        i = target.size() - 1
        while i >= 0:
            item = target.get(i)
            emoji = getattr(item, "emoji", None)
            if emoji is None:
                try:
                    emoji = str(item)
                except Exception:
                    i -= 1
                    continue
            if _is_non_stock(emoji):
                target.remove(i)
            i -= 1


# ============================================================
# UI hooks — premium stickers
# ============================================================


def _hide_view(view) -> None:
    if view is None:
        return
    try:
        if view.getVisibility() != 8:
            view.setVisibility(8)
    except Exception:
        pass


def _restore_view(view) -> None:
    if view is None:
        return
    try:
        if view.getVisibility() != 0:
            view.setVisibility(0)
    except Exception:
        pass


class CheckDocumentsHook(BaseHook):
    """Remove premium stickers from recentStickers and favouriteStickers in EmojiView without in-place mutation."""

    def after_hooked_method(self, param):
        if not self.is_enabled():
            return
        obj = param.thisObject
        for field in ("favouriteStickers", "recentStickers"):
            lst = get_private_field(obj, field)
            if not lst:
                continue
            i = lst.size() - 1
            while i >= 0:
                if _is_premium_sticker(lst.get(i)):
                    lst.remove(i)
                i -= 1


class HidePremiumStickerCellHook(BaseHook):
    """Hide StickerEmojiCell if document is premium; restore visibility otherwise (recycling fix)."""

    def before_hooked_method(self, param):
        if not self.is_enabled():
            return
        if not param.args:
            return
        doc = param.args[0]
        view = param.thisObject
        if _is_premium_sticker(doc):
            _hide_view(view)
            param.setResult(None)
        else:
            _restore_view(view)


# ============================================================
# UI hooks — keyboard performance & category hiding
# ============================================================


class SkipEmojiPacksHook(BaseHook):
    def __init__(self, plugin):
        super().__init__(plugin, Keys.hide_premium_emoji_keyboard)

    def before_hooked_method(self, param):
        if not self.is_enabled():
            return
        param.setResult(None)


class FilterEmojiPacksHook(BaseHook):
    def __init__(self, plugin):
        super().__init__(plugin, Keys.hide_premium_emoji_keyboard)

    def before_hooked_method(self, param):
        if not self.is_enabled():
            return
        if ArrayList:
            param.setResult(ArrayList())


class FilterSearchV7Hook(BaseHook):
    def __init__(self, plugin):
        super().__init__(plugin, Keys.hide_premium_search)

    def before_hooked_method(self, param):
        if not self.is_enabled():
            return
        if not param.args or len(param.args) < 3:
            return
        _filter_search_results(param.args[1])
        _reindex_search_sets(param.args[2])


class FilterSearchV12_8_1Hook(BaseHook):
    def before_hooked_method(self, param):
        if not self.is_enabled():
            return
        if not param.args or len(param.args) < 5:
            return

        runnable_instance = param.thisObject
        search_adapter = getattr(runnable_instance, "this$0", None)
        if search_adapter:
            result_pre = get_private_field(search_adapter, "resultPre")
            if result_pre:
                _filter_search_results(result_pre)

        _filter_search_results(param.args[1])
        _filter_search_packs(param.args[2])
        _filter_search_packs(param.args[3])


class BlockGlobalSearchHook(BaseHook):
    def before_hooked_method(self, param):
        if not self.is_enabled():
            return
        if not param.args:
            return
        method_name = param.method.getName()
        if method_name == "searchEmoji":
            runnable = param.args[0]
        else:
            runnable = param.args[-1]
        if runnable:
            runnable.run()
        param.setResult(None)


class HideGroupStickerSetHook(BaseHook):
    def __init__(self, plugin):
        super().__init__(plugin, Keys.hide_group_stickers)

    def before_hooked_method(self, param):
        if not self.is_enabled():
            return
        param.setResult(None)


class EmojiTabsStripConstructorHook(BaseHook):
    def __init__(self, plugin):
        super().__init__(plugin, Keys.hide_premium_emoji_keyboard)

    def before_hooked_method(self, param):
        if not self.is_enabled():
            return
        if not param.args or len(param.args) < 6:
            return
        # Arg 4 (includeSettings) is True ONLY for main keyboard (EmojiView), False for all SelectAnimatedEmojiDialogs (Status, Reactions, etc.)
        if not param.args[4]:
            return
        # In EmojiTabsStrip constructor, arg 6 is type: 0 = main EmojiView keyboard
        if len(param.args) > 6 and isinstance(param.args[6], int):
            if param.args[6] != 0:
                return
        try:
            param.args[5] = False
        except Exception:
            pass


class FilterReactionsLayoutHook(BaseHook):
    """Filter custom emoji reactions in ReactionsContainerLayout quick bar."""

    def __init__(self, plugin):
        super().__init__(plugin, Keys.hide_premium_emoji_reactions)

    def before_hooked_method(self, param):
        if not self.is_enabled():
            return
        layout = param.thisObject
        if not layout:
            return
        try:
            all_reactions = get_private_field(layout, "allReactionsList")
            if all_reactions:
                _filter_reactions_list(all_reactions)
        except Exception:
            pass


_in_reactions_dialog_update = False


class FilterStickerSetsType5Hook(BaseHook):
    def after_hooked_method(self, param):
        global _in_reactions_dialog_update
        if _in_reactions_dialog_update:
            if ArrayList:
                param.setResult(ArrayList())


class FilterFeaturedEmojiSetsHook(BaseHook):
    def after_hooked_method(self, param):
        global _in_reactions_dialog_update
        if _in_reactions_dialog_update:
            if ArrayList:
                param.setResult(ArrayList())


class SelectAnimatedEmojiDialogUpdateRowsHook(BaseHook):
    """Filter custom emoji and hide category bar EXCLUSIVELY in Reactions window (types 1, 8, 11)."""

    def before_hooked_method(self, param):
        global _in_reactions_dialog_update
        dialog = param.thisObject
        if not dialog:
            return
        try:
            dtype = get_private_field(dialog, "type")
            plugin = self.plugin

            # STRICT FILTER: ONLY Reactions window (types 1, 8, 11). Ignore status, colors, effects, etc.!
            if dtype in (1, 8, 11) and plugin.get_setting(Keys.hide_premium_emoji_reactions, False):
                _in_reactions_dialog_update = True

                # 1. Remove custom emoji reactions
                recent_to_set = get_private_field(dialog, "recentReactionsToSet")
                if recent_to_set:
                    _filter_reactions_list(recent_to_set)

                # 2. Empty frozenEmojiPacks so updateRows() will not add custom emoji packs
                frozen = get_private_field(dialog, "frozenEmojiPacks")
                if frozen is not None:
                    try:
                        frozen.clear()
                    except Exception:
                        pass
                else:
                    if ArrayList:
                        try:
                            dialog.frozenEmojiPacks = ArrayList()
                        except Exception:
                            pass
        except Exception:
            pass

    def after_hooked_method(self, param):
        global _in_reactions_dialog_update
        _in_reactions_dialog_update = False
        dialog = param.thisObject
        if not dialog:
            return
        try:
            dtype = get_private_field(dialog, "type")
            plugin = self.plugin

            # STRICT FILTER: Hide category bar EXCLUSIVELY in Reactions window (types 1, 8, 11)
            if dtype in (1, 8, 11) and plugin.get_setting(Keys.hide_premium_emoji_reactions, False):
                tabs = get_private_field(dialog, "emojiTabs")
                if tabs:
                    _hide_view(tabs)
                shadow = get_private_field(dialog, "emojiTabsShadow")
                if shadow:
                    _hide_view(shadow)

                # Also clear packs array if populated during updateRows
                packs = get_private_field(dialog, "packs")
                if packs:
                    try:
                        packs.clear()
                    except Exception:
                        pass
        except Exception:
            pass


# ============================================================
# Registration
# ============================================================


def register_premium_emoji(plugin):
    _init(plugin)
    classes = []

    if SelectAnimatedEmojiDialog:
        try:
            plugin.hook_all_methods(SelectAnimatedEmojiDialog, "updateRows", SelectAnimatedEmojiDialogUpdateRowsHook(plugin))
            classes.append("SelectAnimatedEmojiDialog")
        except Exception:
            pass

    if ReactionsContainerLayout:
        try:
            rx_hook = FilterReactionsLayoutHook(plugin)
            plugin.hook_all_methods(ReactionsContainerLayout, "showCustomEmojiReactionDialog", rx_hook)
            plugin.hook_all_constructors(ReactionsContainerLayout, rx_hook)
            classes.append("ReactionsContainerLayout")
        except Exception:
            pass

    if Emoji:
        try:
            plugin.hook_all_methods(Emoji, "addRecentEmoji", BlockNonStockHook(plugin, Keys.hide_premium_emoji_keyboard))
            classes.append("Emoji")
        except Exception:
            pass

    if EmojiTabsStrip:
        try:
            plugin.hook_all_constructors(EmojiTabsStrip, EmojiTabsStripConstructorHook(plugin))
            classes.append("EmojiTabsStrip")
        except Exception:
            pass

    if EmojiView:
        try:
            plugin.hook_all_methods(EmojiView, "getRecentEmoji", FilterRecentEmojiHook(plugin, Keys.hide_premium_emoji_keyboard))
        except Exception:
            pass
        try:
            plugin.hook_all_methods(EmojiView, "checkDocuments", CheckDocumentsHook(plugin, Keys.hide_premium_stickers_recent))
        except Exception:
            pass
        try:
            plugin.hook_all_methods(EmojiView, "getEmojipacks", FilterEmojiPacksHook(plugin))
        except Exception:
            pass
        classes.append("EmojiView")

    if EmojiSearchAdapter:
        try:
            plugin.hook_all_methods(EmojiSearchAdapter, "lambda$search$5", FilterSearchResultsHook(plugin, Keys.hide_premium_search))
        except Exception:
            pass
        try:
            plugin.hook_all_methods(EmojiSearchAdapter, "lambda$search$7", FilterSearchV7Hook(plugin))
        except Exception:
            pass
        try:
            plugin.hook_all_methods(EmojiSearchAdapter, "lambda$search$3", BlockGlobalSearchHook(plugin, Keys.hide_premium_search))
        except Exception:
            pass
        try:
            plugin.hook_all_methods(EmojiSearchAdapter, "searchEmoji", BlockGlobalSearchHook(plugin, Keys.hide_premium_search))
        except Exception:
            pass
        classes.append("EmojiSearchAdapter")

    if EmojiSearchAdapterRunnable:
        try:
            plugin.hook_all_methods(EmojiSearchAdapterRunnable, "lambda$run$7", FilterSearchV12_8_1Hook(plugin, Keys.hide_premium_search))
            classes.append("EmojiSearchAdapterRunnable")
        except Exception:
            pass

    if SuggestEmojiView:
        try:
            plugin.hook_all_methods(SuggestEmojiView, "lambda$searchKeywords$3", FilterSuggestResultsHook(plugin, 4, "keywords"))
        except Exception:
            pass
        try:
            plugin.hook_all_methods(SuggestEmojiView, "lambda$searchAnimated$5", FilterSuggestResultsHook(plugin, 2, "animated"))
        except Exception:
            pass
        classes.append("SuggestEmojiView")

    if StickerEmojiCell:
        try:
            plugin.hook_all_methods(StickerEmojiCell, "setSticker", HidePremiumStickerCellHook(plugin, Keys.hide_premium_stickers_grid))
            classes.append("StickerEmojiCell")
        except Exception:
            pass

    if MediaDataController:
        try:
            plugin.hook_all_methods(MediaDataController, "getStickerSets", FilterStickerSetsType5Hook(plugin))
        except Exception:
            pass
        try:
            plugin.hook_all_methods(MediaDataController, "getFeaturedEmojiSets", FilterFeaturedEmojiSetsHook(plugin))
        except Exception:
            pass
        classes.append("MediaDataController")
