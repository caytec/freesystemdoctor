package com.freeandroiddoctor.android.engine.appdeep

enum class Safety { SAFE, CAUTIOUS, OPT_IN }

data class ExpendableRule(
    val packageName: String,
    /** Path relative to the granted SAF root (e.g. `Android/data/com.foo/cache`). */
    val relPath: String,
    val label: String,
    val safety: Safety,
)

/**
 * Hand-picked expendable subfolders inside each app's data dir. Conservative — we only
 * include paths that the app itself treats as cache or regenerable. `OPT_IN` paths must
 * start unchecked in the UI.
 *
 * If a rule turns out to be wrong (deletes content the user wants), move it to OPT_IN
 * or remove the entry — never lower the bar on SAFE.
 */
internal object AppExpendablePathsDb {

    val rules: List<ExpendableRule> = listOf(
        // WhatsApp
        rule("com.whatsapp", "WhatsApp/Media/.Statuses", "Status backups", Safety.OPT_IN),
        rule("com.whatsapp", "WhatsApp/.Shared", "Shared cache", Safety.SAFE),
        rule("com.whatsapp", "WhatsApp/Media/WhatsApp Voice Notes/.Sent", "Sent voice notes", Safety.OPT_IN),
        rule("com.whatsapp", "WhatsApp/Media/WhatsApp Images/.Sent", "Sent images", Safety.OPT_IN),
        rule("com.whatsapp", "WhatsApp/Media/WhatsApp Video/.Sent", "Sent videos", Safety.OPT_IN),
        rule("com.whatsapp", "Android/data/com.whatsapp/cache", "Cache", Safety.SAFE),
        rule("com.whatsapp", "Android/data/com.whatsapp/files/Logs", "Logs", Safety.SAFE),

        // Telegram
        rule("org.telegram.messenger", "Android/data/org.telegram.messenger/cache", "Cache", Safety.SAFE),
        rule("org.telegram.messenger", "Telegram/Telegram Documents", "Cached documents", Safety.OPT_IN),
        rule("org.telegram.messenger", "Telegram/Telegram Video", "Cached videos", Safety.OPT_IN),
        rule("org.telegram.messenger", "Telegram/Telegram Audio", "Cached audio", Safety.OPT_IN),

        // Discord
        rule("com.discord", "Android/data/com.discord/cache", "Cache", Safety.SAFE),
        rule("com.discord", "Android/data/com.discord/files/Logs", "Logs", Safety.SAFE),

        // TikTok
        rule("com.zhiliaoapp.musically", "Android/data/com.zhiliaoapp.musically/cache", "Cache", Safety.SAFE),
        rule("com.zhiliaoapp.musically", "Android/data/com.zhiliaoapp.musically/files/awemecache", "awemecache", Safety.CAUTIOUS),
        rule("com.zhiliaoapp.musically", "Android/data/com.zhiliaoapp.musically/files/Log", "Logs", Safety.SAFE),

        // Instagram
        rule("com.instagram.android", "Android/data/com.instagram.android/cache", "Cache", Safety.SAFE),
        rule("com.instagram.android", "Android/data/com.instagram.android/files/rs_log", "Logs", Safety.SAFE),

        // Snapchat
        rule("com.snapchat.android", "Android/data/com.snapchat.android/cache", "Cache", Safety.SAFE),

        // Facebook
        rule("com.facebook.katana", "Android/data/com.facebook.katana/cache", "Cache", Safety.SAFE),
        rule("com.facebook.katana", "Android/data/com.facebook.katana/files/video-cache", "Video cache", Safety.CAUTIOUS),

        // Messenger
        rule("com.facebook.orca", "Android/data/com.facebook.orca/cache", "Cache", Safety.SAFE),

        // Spotify
        rule("com.spotify.music", "Android/data/com.spotify.music/cache", "Cache", Safety.SAFE),
        rule("com.spotify.music", "Android/data/com.spotify.music/files/spotifycache", "Downloaded audio cache", Safety.OPT_IN),

        // YouTube
        rule("com.google.android.youtube", "Android/data/com.google.android.youtube/cache", "Cache", Safety.SAFE),

        // Chrome
        rule("com.android.chrome", "Android/data/com.android.chrome/cache", "Cache", Safety.SAFE),

        // Reddit
        rule("com.reddit.frontpage", "Android/data/com.reddit.frontpage/cache", "Cache", Safety.SAFE),

        // Brave / Vivaldi
        rule("com.brave.browser", "Android/data/com.brave.browser/cache", "Cache", Safety.SAFE),
        rule("com.vivaldi.browser", "Android/data/com.vivaldi.browser/cache", "Cache", Safety.SAFE),

        // Slack / Zoom / Teams
        rule("com.Slack", "Android/data/com.Slack/cache", "Cache", Safety.SAFE),
        rule("us.zoom.videomeetings", "Android/data/us.zoom.videomeetings/cache", "Cache", Safety.SAFE),
        rule("com.microsoft.teams", "Android/data/com.microsoft.teams/cache", "Cache", Safety.SAFE),

        // Kindle / Audible
        rule("com.amazon.kindle", "Android/data/com.amazon.kindle/cache", "Cache", Safety.SAFE),
        rule("com.audible.application", "Android/data/com.audible.application/cache", "Cache", Safety.SAFE),

        // Generic Pictures/Movies/.thumbnails — usually safe to wipe.
        rule("media.thumbs", "DCIM/.thumbnails", ".thumbnails", Safety.SAFE),
        rule("media.thumbs", "Pictures/.thumbnails", "Picture thumbnails", Safety.SAFE),
        rule("media.thumbs", "Movies/.thumbnails", "Movie thumbnails", Safety.SAFE),
    )

    val byPackage: Map<String, List<ExpendableRule>> = rules.groupBy { it.packageName }

    private fun rule(pkg: String, path: String, label: String, safety: Safety) =
        ExpendableRule(pkg, path, label, safety)
}
