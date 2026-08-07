package com.freeandroiddoctor.android.core.shizuku

import android.content.Context
import android.content.pm.PackageManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import rikka.shizuku.Shizuku

/**
 * Optional privileged layer. Shizuku runs a service with shell (UID 2000) identity after
 * the user pairs it over ADB, which lets us do a handful of things no ordinary app can —
 * clearing other apps' caches, restricting background execution, changing animation
 * scales, disabling bloatware.
 *
 * Three deliberate constraints:
 *  1. **Never load-bearing.** Every feature must degrade gracefully to the no-Shizuku
 *     path. AOSP is considering restricting on-device ADB (after CVE-2026-0073), which
 *     would disable Shizuku entirely; the app must keep working if that lands.
 *  2. **No privileged permissions in our manifest.** WRITE_SECURE_SETTINGS and friends are
 *     signature|privileged — declaring them would never grant them and would draw Play
 *     review attention. Everything goes through the Shizuku binder instead.
 *  3. **No arbitrary shell.** Commands are built here from a fixed vocabulary and all
 *     interpolated arguments are validated. A raw string passed through to a shell running
 *     as UID 2000 would be a command-injection hole.
 */
class ShizukuManager(@Suppress("UNUSED_PARAMETER") context: Context) {

    enum class Status {
        /** Shizuku isn't installed, or its service isn't running. */
        Unavailable,

        /** Service is up but the user hasn't granted us permission. */
        Denied,

        /** Ready to use. */
        Granted,
    }

    data class ShellResult(val exitCode: Int, val stdout: String, val stderr: String) {
        val ok: Boolean get() = exitCode == 0
    }

    fun status(): Status = runCatching {
        if (!Shizuku.pingBinder()) return@runCatching Status.Unavailable
        // Pre-v11 Shizuku had a different permission model we don't support.
        if (Shizuku.isPreV11()) return@runCatching Status.Unavailable
        if (Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED) {
            Status.Granted
        } else {
            Status.Denied
        }
    }.getOrDefault(Status.Unavailable)

    fun requestPermission(requestCode: Int = PERMISSION_REQUEST_CODE) {
        runCatching {
            if (Shizuku.pingBinder() && !Shizuku.isPreV11()) {
                Shizuku.requestPermission(requestCode)
            }
        }
    }

    /**
     * Runs one command from [ShizukuCommand]. This is the only entry point — there is
     * intentionally no overload taking a free-form string.
     */
    suspend fun run(command: ShizukuCommand): ShellResult = withContext(Dispatchers.IO) {
        if (status() != Status.Granted) {
            return@withContext ShellResult(-1, "", "Shizuku not granted")
        }
        exec(command.argv())
    }

    /**
     * Shizuku exposes no public API for running a command; `Shizuku.newProcess` is private
     * in the published artifact, so — as other Shizuku-based apps do — we reach it by
     * reflection. It returns a `ShizukuRemoteProcess`, which extends [Process].
     *
     * If a future Shizuku release renames or removes it, this degrades to a failed
     * ShellResult and every caller falls back to its no-Shizuku path; nothing crashes.
     */
    private fun exec(argv: Array<String>): ShellResult = runCatching {
        val method = Shizuku::class.java.getDeclaredMethod(
            "newProcess",
            Array<String>::class.java,
            Array<String>::class.java,
            String::class.java,
        ).apply { isAccessible = true }

        // argv is passed as an array, so the arguments are never re-parsed by a shell.
        val process = method.invoke(null, argv, null, null) as Process
        val stdout = process.inputStream.bufferedReader().use { it.readText() }
        val stderr = process.errorStream.bufferedReader().use { it.readText() }
        val exit = process.waitFor()
        ShellResult(exit, stdout, stderr)
    }.getOrElse { ShellResult(-1, "", it.message.orEmpty()) }

    companion object {
        const val PERMISSION_REQUEST_CODE = 4711
    }
}

/**
 * The complete, closed set of privileged operations this app will perform.
 *
 * Every package argument is validated against [PACKAGE_PATTERN] at construction, so a
 * malformed or hostile package name cannot reach the shell. Commands are passed to
 * `Shizuku.newProcess` as an argv array rather than a single string, so there is no shell
 * to inject into in the first place — the validation is defence in depth.
 */
sealed class ShizukuCommand {

    abstract fun argv(): Array<String>

    /** Trims every app's cache until [gigabytes] of free space would be available. */
    data class TrimCaches(val gigabytes: Int = 999) : ShizukuCommand() {
        override fun argv() = arrayOf("pm", "trim-caches", "${gigabytes.coerceIn(1, 9999)}G")
    }

    /** Halves (or restores) the three animation scales. */
    data class SetAnimationScale(val scale: Float) : ShizukuCommand() {
        private val safe = scale.coerceIn(0f, 10f).toString()
        override fun argv() = arrayOf(
            "sh", "-c",
            // Fixed template; `safe` is a clamped float, never user text.
            "settings put global window_animation_scale $safe && " +
                "settings put global transition_animation_scale $safe && " +
                "settings put global animator_duration_scale $safe",
        )
    }

    data class ForceStop(val packageName: String) : ShizukuCommand() {
        init { requireValidPackage(packageName) }
        override fun argv() = arrayOf("am", "force-stop", packageName)
    }

    /** Stops an app running in the background and keeps it stopped. */
    data class RestrictBackground(val packageName: String) : ShizukuCommand() {
        init { requireValidPackage(packageName) }
        override fun argv() =
            arrayOf("cmd", "appops", "set", packageName, "RUN_ANY_IN_BACKGROUND", "ignore")
    }

    data class AllowBackground(val packageName: String) : ShizukuCommand() {
        init { requireValidPackage(packageName) }
        override fun argv() =
            arrayOf("cmd", "appops", "set", packageName, "RUN_ANY_IN_BACKGROUND", "allow")
    }

    /** Disables an app for the current user without deleting its data. Reversible. */
    data class DisableApp(val packageName: String) : ShizukuCommand() {
        init { requireValidPackage(packageName) }
        override fun argv() = arrayOf("pm", "disable-user", "--user", "0", packageName)
    }

    data class EnableApp(val packageName: String) : ShizukuCommand() {
        init { requireValidPackage(packageName) }
        override fun argv() = arrayOf("pm", "enable", packageName)
    }

    /** Profile-guided recompile — modest, one-off startup gain. */
    data class Recompile(val packageName: String) : ShizukuCommand() {
        init { requireValidPackage(packageName) }
        override fun argv() =
            arrayOf("pm", "compile", "-m", "speed-profile", "-f", packageName)
    }

    companion object {
        private val PACKAGE_PATTERN = Regex("^[a-zA-Z0-9._]+$")

        private fun requireValidPackage(pkg: String) {
            require(pkg.isNotBlank() && pkg.length <= 255 && PACKAGE_PATTERN.matches(pkg)) {
                "Refusing to build a privileged command for an invalid package name"
            }
        }
    }
}
