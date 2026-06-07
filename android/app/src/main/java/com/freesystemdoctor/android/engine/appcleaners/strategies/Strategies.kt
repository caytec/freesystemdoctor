package com.freesystemdoctor.android.engine.appcleaners.strategies

import com.freesystemdoctor.android.engine.appcleaners.AppCleanerStrategy
import com.freesystemdoctor.android.engine.appcleaners.CleanerTarget
import com.freesystemdoctor.android.engine.appdeep.Safety
import com.freesystemdoctor.android.engine.history.CleanSource

object WhatsAppCleaner : AppCleanerStrategy {
    override val packageName = "com.whatsapp"
    override val historySource = CleanSource.WHATSAPP_DEEP
    override val targets = listOf(
        CleanerTarget("cache", "Cache", "Android/data/com.whatsapp/cache", Safety.SAFE),
        CleanerTarget("logs", "Logs", "Android/data/com.whatsapp/files/Logs", Safety.SAFE),
        CleanerTarget("shared", "Shared cache", "WhatsApp/.Shared", Safety.SAFE),
        CleanerTarget("statuses", "Status backups", "WhatsApp/Media/.Statuses", Safety.OPT_IN),
        CleanerTarget("sent_voice", "Sent voice notes", "WhatsApp/Media/WhatsApp Voice Notes/.Sent", Safety.OPT_IN),
        CleanerTarget("sent_images", "Sent images", "WhatsApp/Media/WhatsApp Images/.Sent", Safety.OPT_IN),
        CleanerTarget("sent_videos", "Sent videos", "WhatsApp/Media/WhatsApp Video/.Sent", Safety.OPT_IN),
    )
}

object TelegramCleaner : AppCleanerStrategy {
    override val packageName = "org.telegram.messenger"
    override val historySource = CleanSource.TELEGRAM_DEEP
    override val targets = listOf(
        CleanerTarget("cache", "Cache", "Android/data/org.telegram.messenger/cache", Safety.SAFE),
        CleanerTarget("docs", "Cached documents", "Telegram/Telegram Documents", Safety.OPT_IN),
        CleanerTarget("video", "Cached video", "Telegram/Telegram Video", Safety.OPT_IN),
        CleanerTarget("audio", "Cached audio", "Telegram/Telegram Audio", Safety.OPT_IN),
    )
}

object DiscordCleaner : AppCleanerStrategy {
    override val packageName = "com.discord"
    override val historySource = CleanSource.DISCORD_DEEP
    override val targets = listOf(
        CleanerTarget("cache", "Cache", "Android/data/com.discord/cache", Safety.SAFE),
        CleanerTarget("logs", "Logs", "Android/data/com.discord/files/Logs", Safety.SAFE),
    )
}

object TikTokCleaner : AppCleanerStrategy {
    override val packageName = "com.zhiliaoapp.musically"
    override val historySource = CleanSource.TIKTOK_DEEP
    override val targets = listOf(
        CleanerTarget("cache", "Cache", "Android/data/com.zhiliaoapp.musically/cache", Safety.SAFE),
        CleanerTarget("awemecache", "awemecache", "Android/data/com.zhiliaoapp.musically/files/awemecache", Safety.CAUTIOUS),
        CleanerTarget("logs", "Logs", "Android/data/com.zhiliaoapp.musically/files/Log", Safety.SAFE),
    )
}
