package com.freeandroiddoctor.android.core.shizuku

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

/**
 * The privileged command surface runs as shell (UID 2000), so these are guardrails
 * against a future change quietly reopening a command-injection hole.
 */
class ShizukuCommandTest {

    private val allCommands: List<ShizukuCommand> = listOf(
        ShizukuCommand.TrimCaches(),
        ShizukuCommand.SetAnimationScale(ShizukuCommand.SetAnimationScale.Key.WINDOW, 0.5f),
        ShizukuCommand.ForceStop("com.example.app"),
        ShizukuCommand.RestrictBackground("com.example.app"),
        ShizukuCommand.AllowBackground("com.example.app"),
        ShizukuCommand.DisableApp("com.example.app"),
        ShizukuCommand.EnableApp("com.example.app"),
        ShizukuCommand.Recompile("com.example.app"),
    )

    @Test
    fun `no command ever invokes a shell interpreter`() {
        val interpreters = setOf("sh", "bash", "su", "toybox", "toolbox", "zsh")
        allCommands.forEach { command ->
            val argv = command.argv()
            assertTrue("empty argv for $command", argv.isNotEmpty())
            assertTrue(
                "${argv[0]} is a shell interpreter — commands must stay shell-free",
                argv[0] !in interpreters,
            )
        }
    }

    @Test
    fun `malformed package names are rejected before reaching the shell`() {
        val hostile = listOf(
            "com.example; rm -rf /",
            "com.example && reboot",
            "com.example\$(id)",
            "com.example`id`",
            "com.example app",
            "com.example|cat",
            "",
        )
        hostile.forEach { pkg ->
            runCatching { ShizukuCommand.ForceStop(pkg) }
                .onSuccess { fail("ForceStop accepted a hostile package name: $pkg") }
        }
    }

    @Test
    fun `NaN animation scale falls back to normal speed instead of writing NaN`() {
        val argv = ShizukuCommand
            .SetAnimationScale(ShizukuCommand.SetAnimationScale.Key.WINDOW, Float.NaN)
            .argv()
        assertEquals("1.0", argv.last())
    }

    @Test
    fun `animation scale is clamped to a sane range`() {
        val argv = ShizukuCommand
            .SetAnimationScale(ShizukuCommand.SetAnimationScale.Key.ANIMATOR, 9999f)
            .argv()
        assertEquals("10.0", argv.last())
    }
}
