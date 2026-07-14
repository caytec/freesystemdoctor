package com.freeandroiddoctor.android.core.shizuku

import android.content.Context

/**
 * Stub for Shizuku integration. The full dependency
 * (`dev.rikka.shizuku:api` / `:provider`) is intentionally NOT linked yet — we want a
 * Play-policy review pass before bundling it. Until then, [status] returns
 * [Status.Unavailable] and the rest of the app gracefully falls back to SAF +
 * `killBackgroundProcesses`. When we wire the real dep:
 *  1. Add the artifacts in `gradle/libs.versions.toml` + `app/build.gradle.kts`.
 *  2. Replace [status] with a real `Shizuku.pingBinder()` + permission check.
 *  3. Implement [execShell] via `Shizuku.newProcess(...)`.
 *
 * The rest of the app must not branch on whether Shizuku is "installed-but-stubbed"
 * vs "really linked" — it only branches on [Status].
 */
class ShizukuManager(@Suppress("UNUSED_PARAMETER") context: Context) {

    enum class Status { Unavailable, Denied, Granted }

    data class ShellResult(val exitCode: Int, val stdout: String, val stderr: String)

    /** Real availability check would call Shizuku.pingBinder() + checkSelfPermission. */
    fun status(): Status = Status.Unavailable

    /** No-op until the real dep is wired. Returns a non-zero exit code so callers fall back. */
    fun execShell(@Suppress("UNUSED_PARAMETER") command: String): ShellResult =
        ShellResult(exitCode = -1, stdout = "", stderr = "Shizuku not available")

    /** Idempotent — actual implementation would invoke Shizuku.requestPermission(...) */
    fun requestPermission() = Unit
}
