GITHUB_URL = "https://github.com/nonFeature/LiteGram"


# Even though camelCase isn't like python
# But it's looks overall better and etg uses the same format (consistency)
class Keys:
    # --- Settings Options ---
    switch_all = "switchAll"
    hide_premium_row = "hidePremiumRow"
    hide_stars_row = "hideStarsRow"
    hide_ton_row = "hideTonRow"
    hide_wallet_row = "hideWalletRow"
    hide_business_row = "hideBusinessRow"
    hide_send_a_gift_row = "hideSendAGiftRow"
    hide_help_section = "hideHelpSection"

    # --- Category Link Aliases (deep links) ---
    chatSettings = "chatSettings"
    profileSettings = "profileSettings"
    interfaceSettings = "interfaceSettings"
    aboutSettings = "aboutSettings"

    # --- Drawer Options ---
    drawer_options = "drawerSettings"  # ETG
    hide_profile_actions_stream_button = "hideProfileActionsStreamButton"

    # --- Chat List ---
    hide_stories = "hideStories"  # ETG
    hide_action_bar_status = "hideActionBarStatus"  # ETG
    hide_greeting_button = "hideGreetingButton"
    hide_group_stickers = "hideGroupStickers"

    # --- Profile Buttons ---
    hide_profile_actions_stories_button = "hideProfileActionsStoriesButton"
    hide_profile_actions_gift_button = "hideProfileActionsGiftButton"

    # --- Profile Tabs ---
    hide_stories_tab = "hideStoriesTab"
    hide_gifts_tab = "hideGiftsTab"

    # --- Profile Appearance ---
    reply_elements = "replyElements"  # ETG
    hide_profile_background_emoji = "hideProfileBackgroundEmoji"
    hide_profile_pinned_gifts = "hideProfilePinnedGifts"
    hide_profile_colorful_background = "hideProfileColorfulBackground"
    hide_boost_badge = "hideBoostBadge"
    hide_profile_music = "hideProfileMusic"
    hide_profile_business = "hideProfileBusiness"

    hide_premium_emoji_keyboard = "hidePremiumEmojiKeyboard"
    hide_premium_emoji_reactions = "hidePremiumEmojiReactions"
    hide_premium_search = "hidePremiumSearch"
    hide_premium_suggestions = "hidePremiumSuggestions"
    switch_all_premium_emoji = "switchAllPremiumEmoji"
    PREMIUM_EMOJI_ROWS = (
        (hide_premium_emoji_keyboard, "hide_premium_emoji_keyboard"),
        (hide_premium_emoji_reactions, "hide_premium_emoji_reactions"),
        (hide_premium_search, "hide_premium_search"),
        (hide_premium_suggestions, "hide_premium_suggestions"),
    )

    hide_premium_stickers_recent = "hidePremiumStickersRecent"
    hide_premium_stickers_search = "hidePremiumStickersSearch"
    hide_premium_stickers_grid = "hidePremiumStickersGrid"
    switch_all_premium_stickers = "switchAllPremiumStickers"
    PREMIUM_STICKERS_ROWS = (
        (hide_premium_stickers_recent, "hide_premium_stickers_recent"),
        (hide_premium_stickers_search, "hide_premium_stickers_search"),
        (hide_premium_stickers_grid, "hide_premium_stickers_grid"),
    )

    hide_premium_badge = "hidePremiumBadge"
    hide_bot_verification = "hideBotVerification"

    # --- Premium Features Hiding ---
    hide_premium_features = "hidePremiumFeatures"
    hide_articles_editor = "hideArticlesEditor"

    # --- AI Features ---
    hide_ai_button = "hideAiButton"
    hide_ai_summarize = "hideAiSummarize"

    # --- Action Bar ---
    hide_action_bar_live_stream = "hideActionBarLiveStream"
    hide_action_bar_archived_stories = "hideActionBarArchivedStories"
    hide_action_bar_send_gift = "hideActionBarSendGift"
    hide_action_bar_boost_group = "hideActionBarBoostGroup"
    hide_action_bar_add_shortcut = "hideActionBarAddShortcut"
    hide_action_bar_report = "hideActionBarReport"

    # --- Gifts ---
    hide_bottom_gift_button = "hideBottomGiftButton"
    hide_gift_cards = "hideGiftCards"
    hide_giveaway_cards = "hideGiveawayCards"
    hide_collectible_status = "hideCollectibleStatus"
    hide_stars_rating = "hideStarsRating"
    hide_star_reaction = "hideStarReaction"

    # --- Emoji Search Options ---
    hide_emoji_search = "hideEmojiSearch"

    # --- Settings Option Rows (shared between ui/settings and utils/settings_utils) ---
    SETTINGS_OPTION_ROWS = (
        (hide_premium_row, "hide_premium_row"),
        (hide_stars_row, "hide_stars_row"),
        (hide_ton_row, "hide_ton_row"),
        (hide_wallet_row, "hide_wallet_row"),
        (hide_business_row, "hide_business_row"),
        (hide_send_a_gift_row, "hide_send_a_gift_row"),
        (hide_help_section, "hide_help_section"),
    )
