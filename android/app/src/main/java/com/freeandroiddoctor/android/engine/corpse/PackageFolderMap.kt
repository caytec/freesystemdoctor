package com.freeandroiddoctor.android.engine.corpse

/**
 * Curated map of friendly-name public folders → owning package name.
 * Conservative hand-picked list — only well-known top-of-storage dirs created by
 * apps under the user-visible root. New entries should only be added when the
 * folder name is unambiguous (i.e. the app is the only known author of that name).
 *
 * Used by [CorpseFinderEngine] to detect corpses for apps that don't keep their
 * own data under `Android/data/<pkg>` or `Android/media/<pkg>`.
 */
internal object PackageFolderMap {

    data class Entry(
        val folderName: String,
        val packageName: String,
        val confidence: Confidence,
    )

    enum class Confidence { HIGH, MEDIUM, LOW }

    val entries: List<Entry> = listOf(
        Entry("WhatsApp", "com.whatsapp", Confidence.HIGH),
        Entry("WhatsApp Business", "com.whatsapp.w4b", Confidence.HIGH),
        Entry("Telegram", "org.telegram.messenger", Confidence.HIGH),
        Entry("Signal", "org.thoughtcrime.securesms", Confidence.HIGH),
        Entry("Viber", "com.viber.voip", Confidence.HIGH),
        Entry("Threema", "ch.threema.app", Confidence.MEDIUM),
        Entry("Line", "jp.naver.line.android", Confidence.MEDIUM),
        Entry("KakaoTalk", "com.kakao.talk", Confidence.MEDIUM),
        Entry("Instagram", "com.instagram.android", Confidence.MEDIUM),
        Entry("Snapchat", "com.snapchat.android", Confidence.MEDIUM),
        Entry("TikTok", "com.zhiliaoapp.musically", Confidence.MEDIUM),
        Entry("Facebook", "com.facebook.katana", Confidence.LOW),
        Entry("Messenger", "com.facebook.orca", Confidence.LOW),
        Entry("Spotify", "com.spotify.music", Confidence.MEDIUM),
        Entry("YouTube", "com.google.android.youtube", Confidence.LOW),
        Entry("Discord", "com.discord", Confidence.HIGH),
        Entry("Slack", "com.Slack", Confidence.HIGH),
        Entry("Zoom", "us.zoom.videomeetings", Confidence.MEDIUM),
        Entry("Skype", "com.skype.raider", Confidence.MEDIUM),
        Entry("Garmin", "com.garmin.android.apps.connectmobile", Confidence.LOW),
        Entry("Strava", "com.strava", Confidence.MEDIUM),
        Entry("MyFitnessPal", "com.myfitnesspal.android", Confidence.MEDIUM),
        Entry("Tinder", "com.tinder", Confidence.MEDIUM),
        Entry("Reddit", "com.reddit.frontpage", Confidence.LOW),
        Entry("Pinterest", "com.pinterest", Confidence.LOW),
        Entry("Audible", "com.audible.application", Confidence.HIGH),
        Entry("Kindle", "com.amazon.kindle", Confidence.MEDIUM),
        Entry("Brave", "com.brave.browser", Confidence.MEDIUM),
        Entry("Vivaldi", "com.vivaldi.browser", Confidence.MEDIUM),
        Entry("DCIM-Camera", "android.hardware.camera", Confidence.LOW),
    )

    private val byFolder: Map<String, Entry> = entries.associateBy { it.folderName.lowercase() }
    fun lookup(folderName: String): Entry? = byFolder[folderName.lowercase()]
}
