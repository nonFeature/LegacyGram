from hook_utils import find_class
from java import jint
from java.lang.reflect import Modifier

from LiteGram.data.constants import Keys
from LiteGram.utils.xposed_utils import BaseHook

_fields_cache = {}
_field_cache = {}


def get_row_fields(clazz):
    class_name = clazz.getName()
    if class_name not in _fields_cache:
        row_fields = []
        try:
            fields = clazz.getDeclaredFields()
            for field in fields:
                try:
                    if field.getType().getName() == "int" and "row" in field.getName().lower():
                        if not (field.getModifiers() & Modifier.STATIC):
                            field.setAccessible(True)
                            row_fields.append(field)
                except Exception:
                    pass
        except Exception:
            pass
        _fields_cache[class_name] = row_fields
    return _fields_cache[class_name]


def get_cached_field(clazz, field_name):
    class_name = clazz.getName()
    key = (class_name, field_name)
    if key not in _field_cache:
        try:
            field = clazz.getDeclaredField(field_name)
            field.setAccessible(True)
            _field_cache[key] = field
        except Exception:
            _field_cache[key] = None
    return _field_cache[key]


def hide_row(clazz, instance, field_name):
    try:
        field = get_cached_field(clazz, field_name)
        if field is None:
            return
        row_idx = field.getInt(instance)
        if row_idx != -1:
            row_count_field = get_cached_field(clazz, "rowCount")
            if row_count_field is None:
                return
            row_count = row_count_field.getInt(instance)

            row_fields = get_row_fields(clazz)

            field.setInt(instance, jint(-1))
            for f in row_fields:
                val = f.getInt(instance)
                if row_idx < val < row_count:
                    f.setInt(instance, jint(val - 1))
            row_count_field.setInt(instance, jint(row_count - 1))
    except Exception:
        pass


class PrivacySettingsActivityUpdateRowsHook(BaseHook):
    def after_hooked_method(self, param):
        if not self.plugin.get_setting(Keys.hide_premium_features, False):
            return
        instance = param.thisObject
        if not instance:
            return
        try:
            clazz = instance.getClass()
            voices_row_field = get_cached_field(clazz, "voicesRow")
            if voices_row_field is None:
                return
            voices_row = voices_row_field.getInt(instance)
            if voices_row != -1:
                row_count_field = get_cached_field(clazz, "rowCount")
                if row_count_field is None:
                    return
                row_count = row_count_field.getInt(instance)

                row_fields = get_row_fields(clazz)

                voices_row_field.setInt(instance, jint(-1))
                for f in row_fields:
                    val = f.getInt(instance)
                    if voices_row < val < row_count:
                        f.setInt(instance, jint(val - 1))
                row_count_field.setInt(instance, jint(row_count - 1))
        except Exception:
            pass


class PrivacySettingsActivityAddPremiumStarHook(BaseHook):
    def before_hooked_method(self, param):
        if not self.plugin.get_setting(Keys.hide_premium_features, False):
            return
        args = param.args
        if args and args[0]:
            param.setResult(args[0])


class PrivacyControlActivitySetMessageTextHook(BaseHook):
    def before_hooked_method(self, param):
        if not self.plugin.get_setting(Keys.hide_premium_features, False):
            return
        instance = param.thisObject
        try:
            clazz = instance.getClass()
            rules_type_field = get_cached_field(clazz, "rulesType")
            if rules_type_field is None:
                return
            rules_type = rules_type_field.getInt(instance)
            if rules_type == 10:  # PRIVACY_RULES_TYPE_MESSAGES
                hide_row(clazz, instance, "payRow")
                hide_row(clazz, instance, "priceButtonRow")
        except Exception:
            pass


class FiltersSetupActivityUpdateRowsHook(BaseHook):
    def after_hooked_method(self, param):
        if not self.plugin.get_setting(Keys.hide_premium_features, False):
            return
        instance = param.thisObject
        try:
            clazz = instance.getClass()
            show_tags_row_field = clazz.getDeclaredField("showTagsRow")
            show_tags_row_field.setAccessible(True)
            show_tags_row = show_tags_row_field.getInt(instance)
            if show_tags_row != -1:
                items_field = clazz.getDeclaredField("items")
                items_field.setAccessible(True)
                items = items_field.get(instance)
                if items and show_tags_row < items.size():
                    # Remove the showTagsRow item and its following shadow item by int index
                    items.remove(int(show_tags_row))
                    if show_tags_row < items.size():
                        items.remove(int(show_tags_row))

                    show_tags_row_field.setInt(instance, jint(-1))
                    try:
                        folder_tags_position_field = clazz.getDeclaredField("folderTagsPosition")
                        folder_tags_position_field.setAccessible(True)
                        folder_tags_position_field.setInt(instance, jint(-1))
                    except Exception:
                        pass

                    adapter_field = clazz.getDeclaredField("adapter")
                    adapter_field.setAccessible(True)
                    adapter = adapter_field.get(instance)
                    if adapter:
                        adapter.notifyDataSetChanged()
        except Exception:
            pass


def _get_item_view_type(item) -> int:
    if item is None:
        return -1
    try:
        val = getattr(item, "viewType", None)
        if val is not None:
            return int(val)
    except Exception:
        pass
    try:
        cls = item.getClass()
        while cls is not None:
            try:
                field = cls.getDeclaredField("viewType")
                field.setAccessible(True)
                return int(field.getInt(item))
            except Exception:
                pass
            try:
                cls = cls.getSuperclass()
            except Exception:
                break
    except Exception:
        pass
    return -1


def _get_item_text(item) -> str:
    if item is None:
        return ""
    try:
        val = getattr(item, "text", None)
        if val is not None:
            return str(val)
    except Exception:
        pass
    try:
        cls = item.getClass()
        while cls is not None:
            try:
                field = cls.getDeclaredField("text")
                field.setAccessible(True)
                val = field.get(item)
                if val is not None:
                    return str(val)
            except Exception:
                pass
            try:
                cls = cls.getSuperclass()
            except Exception:
                break
    except Exception:
        pass
    return ""


class FilterCreateActivityUpdateRowsHook(BaseHook):
    def after_hooked_method(self, param):
        if not self.plugin.get_setting(Keys.hide_premium_features, False):
            return
        instance = param.thisObject
        if not instance:
            return
        try:
            clazz = instance.getClass()
            items_field = None
            cls = clazz
            while cls is not None:
                try:
                    items_field = cls.getDeclaredField("items")
                    items_field.setAccessible(True)
                    break
                except Exception:
                    cls = cls.getSuperclass()

            if not items_field:
                return

            items = items_field.get(instance)
            if not items:
                return

            vt_preview = 9
            vt_color = 10
            try:
                f_preview = clazz.getDeclaredField("VIEW_TYPE_HEADER_COLOR_PREVIEW")
                f_preview.setAccessible(True)
                val = f_preview.get(None)
                if val is not None:
                    vt_preview = int(val)
            except Exception:
                pass
            try:
                f_color = clazz.getDeclaredField("VIEW_TYPE_COLOR")
                f_color.setAccessible(True)
                val = f_color.get(None)
                if val is not None:
                    vt_color = int(val)
            except Exception:
                pass

            LocaleController = find_class("org.telegram.messenger.LocaleController")
            R = find_class("org.telegram.messenger.R")
            info_str = ""
            if LocaleController is not None and R is not None:
                try:
                    info_str = str(LocaleController.getString("FolderTagColorInfo", R.string.FolderTagColorInfo))
                except Exception:
                    pass

            i = items.size() - 1
            while i >= 0:
                item = items.get(i)
                if item:
                    view_type = _get_item_view_type(item)
                    if view_type in (vt_preview, vt_color):
                        items.remove(i)
                    elif view_type in (0, 3, 6):  # VIEW_TYPE_HEADER = 0, SHADOW = 3, SHADOW_TEXT = 6
                        text_str = _get_item_text(item)
                        if text_str and (
                            (info_str and info_str in text_str)
                            or "цвет тега" in text_str.lower()
                            or "tag color" in text_str.lower()
                            or "folder tag" in text_str.lower()
                        ):
                            items.remove(i)
                i -= 1

            try:
                adapter_field = clazz.getDeclaredField("adapter")
                adapter_field.setAccessible(True)
                adapter = adapter_field.get(instance)
                if adapter:
                    adapter.notifyDataSetChanged()
            except Exception:
                pass
        except Exception:
            pass


class ListAdapterOnCreateViewHolderHook(BaseHook):
    def after_hooked_method(self, param):
        if not self.plugin.get_setting(Keys.hide_premium_features, False):
            return

        holder = param.getResult()
        if holder:
            try:
                view = holder.itemView
                if view is not None:
                    class_name = view.getClass().getName()
                    if "HeaderCellColorPreview" in class_name or "PeerColorGrid" in class_name:
                        view.setVisibility(8)
                        lp = view.getLayoutParams()
                        if lp is not None:
                            lp.height = 0
                            lp.width = 0
                            view.setLayoutParams(lp)
            except Exception:
                pass


class ListAdapterOnBindViewHolderHook(BaseHook):
    def after_hooked_method(self, param):
        if not self.plugin.get_setting(Keys.hide_premium_features, False):
            return

        holder = param.args[0]
        if not holder:
            return

        try:
            view = holder.itemView
            if view is not None:
                class_name = view.getClass().getName()
                view_type = holder.getItemViewType()
                if view_type in (9, 10) or "HeaderCellColorPreview" in class_name or "PeerColorGrid" in class_name:
                    view.setVisibility(8)
                    lp = view.getLayoutParams()
                    if lp is not None:
                        lp.height = 0
                        lp.width = 0
                        view.setLayoutParams(lp)
                    return

                if view_type in (0, 3, 6):
                    adapter_instance = param.thisObject
                    outer_field = adapter_instance.getClass().getDeclaredField("this$0")
                    outer_field.setAccessible(True)
                    outer_instance = outer_field.get(adapter_instance)
                    if outer_instance is not None:
                        items_field = outer_instance.getClass().getDeclaredField("items")
                        items_field.setAccessible(True)
                        items = items_field.get(outer_instance)

                        position = param.args[1]
                        if items and position < items.size():
                            item = items.get(position)
                            if item:
                                text_str = _get_item_text(item)
                                text_lower = text_str.lower() if text_str else ""
                                if text_lower and ("цвет тега" in text_lower or "tag color" in text_lower or "folder tag" in text_lower):
                                    view.setVisibility(8)
                                    lp = view.getLayoutParams()
                                    if lp is not None:
                                        lp.height = 0
                                        lp.width = 0
                                        view.setLayoutParams(lp)
        except Exception:
            pass


class MessagesControllerIsTranslationsAutoEnabledHook(BaseHook):
    def before_hooked_method(self, param):
        if self.plugin.get_setting(Keys.hide_premium_features, False):
            param.setResult(False)


class SettingsRegistryCreateEntriesHook(BaseHook):
    def after_hooked_method(self, param):
        if self.plugin.get_setting(Keys.hide_premium_features, False):
            remove_extera_setting_entry(param.thisObject, "showTranslateChatButton")


class MessagesControllerConstructorHook(BaseHook):
    def after_hooked_method(self, param):
        if self.plugin.get_setting(Keys.hide_premium_features, False):
            instance = param.thisObject
            if instance:
                try:
                    field = instance.getClass().getDeclaredField("folderTags")
                    field.setAccessible(True)
                    field.setBoolean(instance, False)
                except Exception:
                    pass


class MessagesControllerSetFolderTagsHook(BaseHook):
    def before_hooked_method(self, param):
        if self.plugin.get_setting(Keys.hide_premium_features, False):
            try:
                param.args[0] = False
            except Exception:
                pass
            instance = param.thisObject
            if instance:
                try:
                    field = instance.getClass().getDeclaredField("folderTags")
                    field.setAccessible(True)
                    field.setBoolean(instance, False)
                except Exception:
                    pass


class DialogCellTagsUpdateHook(BaseHook):
    def before_hooked_method(self, param):
        if not self.plugin.get_setting(Keys.hide_premium_features, False):
            return
        obj = param.thisObject
        if obj:
            try:
                tags = getattr(obj, "tags", None)
                if tags:
                    tags.clear()
            except Exception:
                pass
        param.setResult(False)


class FilterCreateActivityConstructorHook(BaseHook):
    def after_hooked_method(self, param):
        self.plugin.in_filter_create = True


class FilterCreateActivityOnFragmentDestroyHook(BaseHook):
    def before_hooked_method(self, param):
        self.plugin.in_filter_create = False


class UserConfigIsPremiumHook(BaseHook):
    def before_hooked_method(self, param):
        if not self.plugin.get_setting(Keys.hide_premium_features, False):
            return
        if getattr(self.plugin, "in_filter_create", False):
            param.setResult(True)


class GeneralPreferencesActivityFillItemsHook(BaseHook):
    def after_hooked_method(self, param):
        if self.plugin.get_setting(Keys.hide_premium_features, False):
            arrayList = param.args[0]
            if arrayList:
                i = arrayList.size() - 1
                while i >= 0:
                    uitem = arrayList.get(i)
                    if uitem:
                        try:
                            val = -1
                            try:
                                val = uitem.getClass().getField("id").getInt(uitem)
                            except Exception:
                                try:
                                    val = uitem.getClass().getField("f1708id").getInt(uitem)
                                except Exception:
                                    pass
                            if val == 2:  # GeneralItem.SHOW_TRANSLATE_CHAT_BUTTON.getId()
                                arrayList.remove(i)
                        except Exception:
                            pass
                    i -= 1


def is_matching_entry(entry, alias_to_remove):
    if not entry:
        return False
    try:
        clazz = entry.getClass()
        fields = clazz.getDeclaredFields()
        for field in fields:
            if field.getName() == "guid":
                field.setAccessible(True)
                val = field.get(entry)
                if val == alias_to_remove:
                    return True
    except Exception:
        pass
    return False


def remove_extera_setting_entry(registry, alias_to_remove):
    try:
        entries_field = registry.getClass().getDeclaredField("entriesStringAlias")
        entries_field.setAccessible(True)
        entries_map = entries_field.get(registry)
        if entries_map:
            entries_map.remove(alias_to_remove)
    except Exception:
        pass

    try:
        prepared_field = registry.getClass().getDeclaredField("preparedEntries")
        prepared_field.setAccessible(True)
        prepared = prepared_field.get(registry)
        if prepared:
            prepared_class = prepared.getClass()
            class_name = prepared_class.getName()

            if "Map" in class_name:
                keys = list(prepared.keySet().toArray())
                for key in keys:
                    val = prepared.get(key)
                    if val:
                        val_class = val.getClass()
                        val_class_name = val_class.getName()
                        if "List" in val_class_name:
                            i = val.size() - 1
                            while i >= 0:
                                entry = val.get(i)
                                if is_matching_entry(entry, alias_to_remove):
                                    val.remove(i)
                                i -= 1
                        elif is_matching_entry(val, alias_to_remove):
                            prepared.remove(key)
            elif "List" in class_name:
                i = prepared.size() - 1
                while i >= 0:
                    entry = prepared.get(i)
                    if is_matching_entry(entry, alias_to_remove):
                        prepared.remove(i)
                    i -= 1
    except Exception:
        pass


class TextInfoPrivacyCellSetTextHook(BaseHook):
    def before_hooked_method(self, param):
        if not self.plugin.get_setting(Keys.hide_premium_features, False):
            return
        text = param.args[0]
        if text is not None:
            text_str = str(text)
            if "Вы можете запретить входящие сообщения" in text_str or "You can restrict who can send you messages" in text_str:
                if "\n" in text_str:
                    text_str = text_str.split("\n")[0].strip()
                elif "**" in text_str:
                    text_str = text_str.split("**")[0].strip()
                elif "Premium" in text_str:
                    parts = text_str.split(".")
                    if len(parts) > 1:
                        text_str = parts[0].strip() + "."
                param.args[0] = text_str


def register_hide_premium_features(plugin) -> None:
    # 1. Privacy settings: voice messages
    try:
        PrivacySettingsActivity = find_class("org.telegram.ui.PrivacySettingsActivity")
        if PrivacySettingsActivity:
            plugin.hook_all_methods(PrivacySettingsActivity, "updateRows", PrivacySettingsActivityUpdateRowsHook(plugin))
            plugin.hook_all_methods(PrivacySettingsActivity, "addPremiumStar", PrivacySettingsActivityAddPremiumStarHook(plugin))
    except Exception:
        pass

    # 2. Privacy settings: paid messages
    try:
        PrivacyControlActivity = find_class("org.telegram.ui.PrivacyControlActivity")
        if PrivacyControlActivity:
            plugin.hook_all_methods(PrivacyControlActivity, "setMessageText", PrivacyControlActivitySetMessageTextHook(plugin))
    except Exception:
        pass

    # 2.1 TextInfoPrivacyCell hook to hide details links
    try:
        TextInfoPrivacyCell = find_class("org.telegram.ui.Cells.TextInfoPrivacyCell")
        if TextInfoPrivacyCell:
            plugin.hook_all_methods(TextInfoPrivacyCell, "setText", TextInfoPrivacyCellSetTextHook(plugin))
    except Exception:
        pass

    # 3. Folders setting: folder tags
    try:
        FiltersSetupActivity = find_class("org.telegram.ui.FiltersSetupActivity")
        if FiltersSetupActivity:
            plugin.hook_all_methods(FiltersSetupActivity, "updateRows", FiltersSetupActivityUpdateRowsHook(plugin))
    except Exception:
        pass

    # 4. Languages: translate chats
    try:
        MessagesController = find_class("org.telegram.messenger.MessagesController")
        if MessagesController:
            plugin.hook_all_methods(MessagesController, "isTranslationsAutoEnabled", MessagesControllerIsTranslationsAutoEnabledHook(plugin))
            plugin.hook_all_constructors(MessagesController, MessagesControllerConstructorHook(plugin))
            plugin.hook_all_methods(MessagesController, "setFolderTags", MessagesControllerSetFolderTagsHook(plugin))
            # Proactively update existing instances of MessagesController
            if plugin.get_setting(Keys.hide_premium_features, False):
                for i in range(4):  # Support up to 4 accounts
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

    # 4.1 UserConfig isPremium hook
    try:
        UserConfig = find_class("org.telegram.messenger.UserConfig")
        if UserConfig:
            plugin.hook_all_methods(UserConfig, "isPremium", UserConfigIsPremiumHook(plugin))
    except Exception:
        pass

    # 4.2 GeneralPreferencesActivity fillItems hook
    try:
        GeneralPreferencesActivity = find_class("com.exteragram.messenger.preferences.GeneralPreferencesActivity")
        if GeneralPreferencesActivity:
            plugin.hook_all_methods(GeneralPreferencesActivity, "fillItems", GeneralPreferencesActivityFillItemsHook(plugin))
    except Exception:
        pass

    # 5. Extera Settings registry: showTranslateChatButton
    try:
        SettingsRegistry = find_class("com.exteragram.messenger.preferences.utils.SettingsRegistry")
        if SettingsRegistry:
            plugin.hook_all_methods(SettingsRegistry, "createEntriesIfNeeded", SettingsRegistryCreateEntriesHook(plugin))
            # Proactively remove if registry is already initialized
            registry = SettingsRegistry.getInstance()
            if registry:
                remove_extera_setting_entry(registry, "showTranslateChatButton")
    except Exception:
        pass

    # 6. Folder editing: folder color tag
    try:
        FilterCreateActivity = find_class("org.telegram.ui.FilterCreateActivity")
        if FilterCreateActivity:
            plugin.hook_all_methods(FilterCreateActivity, "updateRows", FilterCreateActivityUpdateRowsHook(plugin))
            plugin.hook_all_constructors(FilterCreateActivity, FilterCreateActivityConstructorHook(plugin))
            plugin.hook_all_methods(FilterCreateActivity, "onFragmentDestroy", FilterCreateActivityOnFragmentDestroyHook(plugin))

        ListAdapter = find_class("org.telegram.ui.FilterCreateActivity$ListAdapter")
        if ListAdapter:
            plugin.hook_all_methods(ListAdapter, "onCreateViewHolder", ListAdapterOnCreateViewHolderHook(plugin))
            plugin.hook_all_methods(ListAdapter, "onBindViewHolder", ListAdapterOnBindViewHolderHook(plugin))
    except Exception:
        pass

    # 7. Folder tags rendering on chat cells: DialogCellTags
    try:
        DialogCellTags = find_class("org.telegram.ui.Components.DialogCellTags")
        if DialogCellTags:
            plugin.hook_all_methods(DialogCellTags, "update", DialogCellTagsUpdateHook(plugin))
    except Exception:
        pass
