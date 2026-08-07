package com.freeandroiddoctor.android.engine.privacy

/** What a tracking SDK is primarily used for. */
enum class TrackerCategory { ADVERTISING, ANALYTICS, ATTRIBUTION, CRASH_REPORTING, PROFILING }

/** One known tracking SDK and the class-name prefixes that give it away. */
data class TrackerSignature(
    val name: String,
    val category: TrackerCategory,
    val prefixes: List<String>,
)

/**
 * Offline signature list of common third-party tracking / ad SDKs, matched against the
 * components an app declares in its manifest. Bundled with the app — no network lookup,
 * nothing about your installed apps ever leaves the device.
 *
 * Detection is deliberately conservative: it only reports SDKs that register components
 * (activities/services/receivers/providers), which is how the vast majority of ad and
 * analytics SDKs integrate. An SDK that is purely library code with no declared component
 * will not be flagged, so "0 trackers" means "none detected", not a guarantee.
 */
object TrackerDb {

    val signatures: List<TrackerSignature> = listOf(
        // ── Advertising ────────────────────────────────────────────────
        TrackerSignature("Google AdMob", TrackerCategory.ADVERTISING, listOf("com.google.android.gms.ads")),
        TrackerSignature("Meta Audience Network", TrackerCategory.ADVERTISING, listOf("com.facebook.ads")),
        TrackerSignature("Unity Ads", TrackerCategory.ADVERTISING, listOf("com.unity3d.ads", "com.unity3d.services")),
        TrackerSignature("AppLovin", TrackerCategory.ADVERTISING, listOf("com.applovin")),
        TrackerSignature("ironSource", TrackerCategory.ADVERTISING, listOf("com.ironsource")),
        TrackerSignature("Vungle", TrackerCategory.ADVERTISING, listOf("com.vungle")),
        TrackerSignature("Chartboost", TrackerCategory.ADVERTISING, listOf("com.chartboost")),
        TrackerSignature("InMobi", TrackerCategory.ADVERTISING, listOf("com.inmobi")),
        TrackerSignature("Tapjoy", TrackerCategory.ADVERTISING, listOf("com.tapjoy")),
        TrackerSignature("MoPub", TrackerCategory.ADVERTISING, listOf("com.mopub")),
        TrackerSignature("Criteo", TrackerCategory.ADVERTISING, listOf("com.criteo")),
        TrackerSignature("Pangle / ByteDance", TrackerCategory.ADVERTISING, listOf("com.bytedance.sdk", "com.pangle")),
        TrackerSignature("Smaato", TrackerCategory.ADVERTISING, listOf("com.smaato")),
        TrackerSignature("Fyber", TrackerCategory.ADVERTISING, listOf("com.fyber")),
        TrackerSignature("Mintegral", TrackerCategory.ADVERTISING, listOf("com.mbridge", "com.mintegral")),

        // ── Analytics ──────────────────────────────────────────────────
        TrackerSignature("Firebase Analytics", TrackerCategory.ANALYTICS, listOf("com.google.firebase.analytics", "com.google.android.gms.measurement")),
        TrackerSignature("Meta Analytics", TrackerCategory.ANALYTICS, listOf("com.facebook.appevents")),
        TrackerSignature("Flurry", TrackerCategory.ANALYTICS, listOf("com.flurry")),
        TrackerSignature("Mixpanel", TrackerCategory.ANALYTICS, listOf("com.mixpanel")),
        TrackerSignature("Amplitude", TrackerCategory.ANALYTICS, listOf("com.amplitude")),
        TrackerSignature("Segment", TrackerCategory.ANALYTICS, listOf("com.segment.analytics")),
        TrackerSignature("Countly", TrackerCategory.ANALYTICS, listOf("ly.count")),
        TrackerSignature("Matomo", TrackerCategory.ANALYTICS, listOf("org.matomo")),
        TrackerSignature("Yandex AppMetrica", TrackerCategory.ANALYTICS, listOf("com.yandex.metrica")),
        TrackerSignature("Umeng", TrackerCategory.ANALYTICS, listOf("com.umeng")),
        TrackerSignature("Tencent Stat", TrackerCategory.ANALYTICS, listOf("com.tencent.stat", "com.tencent.mta")),
        TrackerSignature("Localytics", TrackerCategory.ANALYTICS, listOf("com.localytics")),

        // ── Attribution / marketing ────────────────────────────────────
        TrackerSignature("AppsFlyer", TrackerCategory.ATTRIBUTION, listOf("com.appsflyer")),
        TrackerSignature("Adjust", TrackerCategory.ATTRIBUTION, listOf("com.adjust.sdk")),
        TrackerSignature("Branch", TrackerCategory.ATTRIBUTION, listOf("io.branch")),
        TrackerSignature("Kochava", TrackerCategory.ATTRIBUTION, listOf("com.kochava")),
        TrackerSignature("Singular", TrackerCategory.ATTRIBUTION, listOf("com.singular.sdk")),
        TrackerSignature("Braze", TrackerCategory.ATTRIBUTION, listOf("com.braze", "com.appboy")),
        TrackerSignature("CleverTap", TrackerCategory.ATTRIBUTION, listOf("com.clevertap")),
        TrackerSignature("OneSignal", TrackerCategory.ATTRIBUTION, listOf("com.onesignal")),
        TrackerSignature("MoEngage", TrackerCategory.ATTRIBUTION, listOf("com.moengage")),

        // ── Crash reporting / performance ──────────────────────────────
        TrackerSignature("Firebase Crashlytics", TrackerCategory.CRASH_REPORTING, listOf("com.google.firebase.crashlytics", "com.crashlytics")),
        TrackerSignature("Sentry", TrackerCategory.CRASH_REPORTING, listOf("io.sentry")),
        TrackerSignature("Bugsnag", TrackerCategory.CRASH_REPORTING, listOf("com.bugsnag")),
        TrackerSignature("New Relic", TrackerCategory.CRASH_REPORTING, listOf("com.newrelic")),
        TrackerSignature("Instabug", TrackerCategory.CRASH_REPORTING, listOf("com.instabug")),

        // ── Session replay / user profiling ────────────────────────────
        TrackerSignature("UXCam", TrackerCategory.PROFILING, listOf("com.uxcam")),
        TrackerSignature("Smartlook", TrackerCategory.PROFILING, listOf("com.smartlook")),
        TrackerSignature("FullStory", TrackerCategory.PROFILING, listOf("com.fullstory")),
        TrackerSignature("Contentsquare", TrackerCategory.PROFILING, listOf("com.contentsquare")),
    )

    /** Flat prefix → signature index, built once for fast matching. */
    val byPrefix: List<Pair<String, TrackerSignature>> =
        signatures.flatMap { sig -> sig.prefixes.map { it to sig } }
}
