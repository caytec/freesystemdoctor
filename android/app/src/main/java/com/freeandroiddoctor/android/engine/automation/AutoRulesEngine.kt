package com.freeandroiddoctor.android.engine.automation

import android.content.Context
import android.os.StatFs
import com.freeandroiddoctor.android.data.automation.AutoRule
import com.freeandroiddoctor.android.data.automation.AutoRuleAction
import com.freeandroiddoctor.android.data.automation.AutoRuleStore
import com.freeandroiddoctor.android.data.automation.AutoRuleTrigger
import com.freeandroiddoctor.android.data.modes.ModeStore
import com.freeandroiddoctor.android.engine.cache.JunkScannerEngine
import com.freeandroiddoctor.android.engine.modes.AppModesEngine
import com.freeandroiddoctor.android.engine.privacy.ApkStaticScannerEngine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** What the engine *intends* to do — surfaced as a notification or a worker job. */
sealed class AutoRuleFiring(val ruleId: String, val title: String, val body: String) {
    class NotifyDeepScan(ruleId: String, body: String) :
        AutoRuleFiring(ruleId, "Storage low", body)
    class NotifyInstallRisk(ruleId: String, pkg: String) :
        AutoRuleFiring(ruleId, "App may be risky", pkg)
    class CleanCacheRequested(ruleId: String, bytes: Long) :
        AutoRuleFiring(ruleId, "Cache cleaned", "${bytes / 1024 / 1024} MB freed")
    class ModeActivated(ruleId: String, modeId: String) :
        AutoRuleFiring(ruleId, "Mode activated", modeId)
}

/**
 * Stateless evaluator: given the current trigger event, returns the actions to take.
 * Worker / receiver code invokes this on every relevant event.
 */
class AutoRulesEngine(
    private val context: Context,
    private val store: AutoRuleStore,
    private val modeStore: ModeStore,
    private val modesEngine: AppModesEngine,
    private val junkEngine: JunkScannerEngine,
    private val apkScanner: ApkStaticScannerEngine,
) {

    suspend fun evaluate(trigger: AutoRuleTrigger, extra: Map<String, String> = emptyMap()): List<AutoRuleFiring> {
        val rules = store.enabledOnce().filter { it.trigger == trigger }
        if (rules.isEmpty()) return emptyList()
        val firings = ArrayList<AutoRuleFiring>()
        for (rule in rules) {
            val firing = runRule(rule, extra) ?: continue
            firings += firing
            store.markFired(rule.id)
        }
        return firings
    }

    private suspend fun runRule(rule: AutoRule, extra: Map<String, String>): AutoRuleFiring? =
        withContext(Dispatchers.IO) {
            when (rule.action) {
                AutoRuleAction.NOTIFY_DEEP_SCAN -> {
                    val pct = freeStoragePercent()
                    if (rule.trigger == AutoRuleTrigger.LOW_STORAGE && pct > rule.triggerThreshold) {
                        null
                    } else {
                        AutoRuleFiring.NotifyDeepScan(rule.id, "Free space ${pct}%")
                    }
                }
                AutoRuleAction.RUN_CACHE_CLEAN -> {
                    val result = runCatching { junkEngine.cleanAppCache() }.getOrNull()
                    AutoRuleFiring.CleanCacheRequested(rule.id, result?.bytesFreed ?: 0L)
                }
                AutoRuleAction.ACTIVATE_MODE -> {
                    val modeId = rule.modeIdParam ?: return@withContext null
                    val mode = modeStore.allModesOnce().firstOrNull { it.id == modeId }
                        ?: return@withContext null
                    modesEngine.activate(mode)
                    AutoRuleFiring.ModeActivated(rule.id, modeId)
                }
                AutoRuleAction.NOTIFY_INSTALL_RISK -> {
                    val pkg = extra["package"] ?: return@withContext null
                    val report = apkScanner.scan(includeSystem = false)
                    val app = report.apps.firstOrNull { it.packageName == pkg } ?: return@withContext null
                    if (app.riskScore < rule.triggerThreshold.coerceAtLeast(40)) {
                        null
                    } else {
                        AutoRuleFiring.NotifyInstallRisk(rule.id, app.label)
                    }
                }
            }
        }

    private fun freeStoragePercent(): Int {
        val path = context.filesDir
        val stat = StatFs(path.absolutePath)
        val free = stat.availableBytes.toDouble()
        val total = stat.totalBytes.toDouble().coerceAtLeast(1.0)
        return ((free / total) * 100).toInt()
    }
}
