package com.freeandroiddoctor.android.core.di

import android.app.Application
import android.content.Context
import com.freeandroiddoctor.android.ads.AdsController
import com.freeandroiddoctor.android.ads.AppOpenAdManager
import com.freeandroiddoctor.android.analytics.Analytics
import com.freeandroiddoctor.android.analytics.LogAnalytics
import com.freeandroiddoctor.android.ai.AiRepository
import com.freeandroiddoctor.android.billing.BillingManager
import com.freeandroiddoctor.android.core.media.MediaDeleteHelper
import com.freeandroiddoctor.android.core.permission.PermissionManager
import com.freeandroiddoctor.android.data.ai.AiKeyStore
import com.freeandroiddoctor.android.data.automation.AutoRuleStore
import com.freeandroiddoctor.android.data.billing.ProStore
import com.freeandroiddoctor.android.data.modes.ModeStore
import com.freeandroiddoctor.android.data.privacy.PrivacyProfileStore
import com.freeandroiddoctor.android.data.quota.DailyQuotaStore
import com.freeandroiddoctor.android.data.saf.SafTreeStore
import com.freeandroiddoctor.android.data.settings.SettingsRepository
import com.freeandroiddoctor.android.engine.files.FileShredderEngine
import com.freeandroiddoctor.android.engine.files.LogFilesEngine
import com.freeandroiddoctor.android.engine.files.SafTreeEngine
import com.freeandroiddoctor.android.engine.network.DataUsageEngine
import com.freeandroiddoctor.android.engine.system.SystemTweaksEngine
import com.freeandroiddoctor.android.engine.apps.AppInsightsEngine
import com.freeandroiddoctor.android.engine.apps.AppManagerEngine
import com.freeandroiddoctor.android.engine.apps.AppUsageEngine
import com.freeandroiddoctor.android.engine.apps.ApkExtractorEngine
import com.freeandroiddoctor.android.engine.apps.PermissionAuditEngine
import com.freeandroiddoctor.android.engine.apps.RarelyUsedEngine
import com.freeandroiddoctor.android.engine.battery.BatteryEngine
import com.freeandroiddoctor.android.engine.contacts.ContactsEngine
import com.freeandroiddoctor.android.engine.contacts.SmsBackupEngine
import com.freeandroiddoctor.android.data.cloudbackup.CloudBackupKeyStore
import com.freeandroiddoctor.android.engine.appcleaners.AppCleanersEngine
import com.freeandroiddoctor.android.engine.appdeep.AppDeepCleanEngine
import com.freeandroiddoctor.android.engine.battery.BatteryDrainEngine
import com.freeandroiddoctor.android.engine.battery.BatteryHealthEngine
import com.freeandroiddoctor.android.engine.battery.ChargingSessionEngine
import com.freeandroiddoctor.android.engine.cache.HiddenCacheEngine
import com.freeandroiddoctor.android.engine.cache.JunkScannerEngine
import com.freeandroiddoctor.android.engine.corpse.CorpseFinderEngine
import com.freeandroiddoctor.android.engine.notifications.NotificationStatsEngine
import com.freeandroiddoctor.android.engine.storage.StorageTreemapEngine
import com.freeandroiddoctor.android.core.shizuku.ShizukuManager
import com.freeandroiddoctor.android.engine.cloudbackup.BackupCryptoEngine
import com.freeandroiddoctor.android.engine.cloudbackup.CloudBackupEngine
import com.freeandroiddoctor.android.data.gameboost.GameProfileStore
import com.freeandroiddoctor.android.engine.focus.FocusEngine
import com.freeandroiddoctor.android.engine.gameboost.GameBoostEngine
import com.freeandroiddoctor.android.engine.forecast.StorageForecastEngine
import com.freeandroiddoctor.android.engine.history.CleaningHistoryEngine
import com.freeandroiddoctor.android.engine.lock.AppLockEngine
import com.freeandroiddoctor.android.engine.resource.AppResourceEngine
import com.freeandroiddoctor.android.engine.trash.TrashEngine
import com.freeandroiddoctor.android.engine.vault.AppVaultEngine
import com.freeandroiddoctor.android.engine.device.DeviceInfoEngine
import com.freeandroiddoctor.android.engine.duplicates.DuplicateFinderEngine
import com.freeandroiddoctor.android.engine.largefiles.LargeFilesEngine
import com.freeandroiddoctor.android.engine.media.BlurScreenshotEngine
import com.freeandroiddoctor.android.engine.media.ImageCompressionEngine
import com.freeandroiddoctor.android.engine.media.MediaStoreCategoryEngine
import com.freeandroiddoctor.android.engine.media.SimilarPhotoEngine
import com.freeandroiddoctor.android.engine.memory.MemoryEngine
import com.freeandroiddoctor.android.engine.network.SpeedTestEngine
import com.freeandroiddoctor.android.engine.network.WifiAnalyzerEngine
import com.freeandroiddoctor.android.engine.storage.StorageAnalyzerEngine
import com.freeandroiddoctor.android.engine.system.ClipboardCleanerEngine
import com.freeandroiddoctor.android.work.WorkScheduler

/** Minimal manual dependency container; initialized once from the Application. */
object ServiceLocator {

    private lateinit var appContext: Context

    fun init(context: Context) {
        appContext = context.applicationContext
    }

    val analytics: Analytics by lazy { LogAnalytics() }

    val permissionManager: PermissionManager by lazy { PermissionManager(appContext) }
    val settingsRepository: SettingsRepository by lazy { SettingsRepository(appContext) }
    private val aiKeyStore: AiKeyStore by lazy { AiKeyStore(appContext) }
    val aiRepository: AiRepository by lazy { AiRepository(aiKeyStore) }
    fun aiKeyStore(): AiKeyStore = aiKeyStore

    val batteryEngine: BatteryEngine by lazy { BatteryEngine(appContext) }
    val memoryEngine: MemoryEngine by lazy { MemoryEngine(appContext) }
    val deviceInfoEngine: DeviceInfoEngine by lazy { DeviceInfoEngine(appContext) }
    val storageEngine: StorageAnalyzerEngine by lazy {
        StorageAnalyzerEngine(appContext, permissionManager)
    }
    val appManagerEngine: AppManagerEngine by lazy {
        AppManagerEngine(appContext, permissionManager)
    }
    val junkEngine: JunkScannerEngine by lazy { JunkScannerEngine(appContext) }
    val trashEngine: TrashEngine by lazy { TrashEngine(appContext) }
    val hiddenCacheEngine: HiddenCacheEngine by lazy { HiddenCacheEngine(appContext) }
    val appVaultEngine: AppVaultEngine by lazy { AppVaultEngine(appContext) }
    val appInsightsEngine: AppInsightsEngine by lazy {
        AppInsightsEngine(appContext, permissionManager)
    }
    val storageForecastEngine: StorageForecastEngine by lazy {
        StorageForecastEngine(appContext, storageEngine)
    }
    val cleaningHistoryEngine: CleaningHistoryEngine by lazy { CleaningHistoryEngine(appContext) }
    val appResourceEngine: AppResourceEngine by lazy {
        AppResourceEngine(
            appContext, permissionManager, appManagerEngine, storageEngine, appUsageEngine, dataUsageEngine,
        )
    }
    val focusEngine: FocusEngine by lazy { FocusEngine(appContext) }
    val gameProfileStore: GameProfileStore by lazy { GameProfileStore(appContext) }
    val gameBoostEngine: GameBoostEngine by lazy {
        GameBoostEngine(appContext, memoryEngine, junkEngine)
    }
    val appLockEngine: AppLockEngine by lazy { AppLockEngine(appContext) }
    private val backupCryptoEngine: BackupCryptoEngine by lazy { BackupCryptoEngine() }
    val cloudBackupEngine: CloudBackupEngine by lazy {
        CloudBackupEngine(appContext, backupCryptoEngine)
    }
    val cloudBackupKeyStore: CloudBackupKeyStore by lazy { CloudBackupKeyStore(appContext) }
    val largeFilesEngine: LargeFilesEngine by lazy { LargeFilesEngine(appContext) }
    val duplicateEngine: DuplicateFinderEngine by lazy { DuplicateFinderEngine(appContext) }
    val mediaCategoryEngine: MediaStoreCategoryEngine by lazy { MediaStoreCategoryEngine(appContext) }
    val appUsageEngine: AppUsageEngine by lazy { AppUsageEngine(appContext, permissionManager) }
    val rarelyUsedEngine: RarelyUsedEngine by lazy { RarelyUsedEngine(appContext, permissionManager) }
    val permissionAuditEngine: PermissionAuditEngine by lazy { PermissionAuditEngine(appContext) }
    val apkExtractorEngine: ApkExtractorEngine by lazy { ApkExtractorEngine(appContext) }
    val clipboardEngine: ClipboardCleanerEngine by lazy { ClipboardCleanerEngine(appContext) }
    val mediaDeleteHelper: MediaDeleteHelper by lazy { MediaDeleteHelper(appContext) }
    val workScheduler: WorkScheduler by lazy { WorkScheduler(appContext) }

    val safTreeStore: SafTreeStore by lazy { SafTreeStore(appContext) }
    val safTreeEngine: SafTreeEngine by lazy { SafTreeEngine(appContext) }
    val fileShredderEngine: FileShredderEngine by lazy { FileShredderEngine(appContext) }
    val dataUsageEngine: DataUsageEngine by lazy { DataUsageEngine(appContext, permissionManager) }
    val systemTweaksEngine: SystemTweaksEngine by lazy { SystemTweaksEngine(appContext) }
    val similarPhotoEngine: SimilarPhotoEngine by lazy { SimilarPhotoEngine(appContext) }
    val blurScreenshotEngine: BlurScreenshotEngine by lazy { BlurScreenshotEngine(appContext) }
    val imageCompressionEngine: ImageCompressionEngine by lazy { ImageCompressionEngine(appContext) }
    val wifiAnalyzerEngine: WifiAnalyzerEngine by lazy { WifiAnalyzerEngine(appContext) }
    val speedTestEngine: SpeedTestEngine by lazy { SpeedTestEngine() }
    val contactsEngine: ContactsEngine by lazy { ContactsEngine(appContext) }
    val smsBackupEngine: SmsBackupEngine by lazy { SmsBackupEngine(appContext) }

    val proStore: ProStore by lazy { ProStore(appContext) }
    val billingManager: BillingManager by lazy { BillingManager(appContext, proStore) }
    val adsController: AdsController by lazy {
        AdsController(appContext).also { it.proProvider = { billingManager.isPro.value } }
    }
    val appOpenAdManager: AppOpenAdManager by lazy {
        AppOpenAdManager(appContext as Application)
    }

    // Update 12: Competitor Parity Pack
    val corpseFinderEngine: CorpseFinderEngine by lazy { CorpseFinderEngine(appContext) }
    val appDeepCleanEngine: AppDeepCleanEngine by lazy { AppDeepCleanEngine(appContext) }
    val appCleanersEngine: AppCleanersEngine by lazy { AppCleanersEngine(appContext) }
    val chargingSessionEngine: ChargingSessionEngine by lazy { ChargingSessionEngine(appContext) }
    val batteryHealthEngine: BatteryHealthEngine by lazy {
        BatteryHealthEngine(chargingSessionEngine, batteryEngine)
    }
    val batteryDrainEngine: BatteryDrainEngine by lazy {
        BatteryDrainEngine(appContext, permissionManager)
    }
    val storageTreemapEngine: StorageTreemapEngine by lazy { StorageTreemapEngine(appContext) }
    val notificationStatsEngine: NotificationStatsEngine by lazy {
        NotificationStatsEngine(appContext)
    }
    val shizukuManager: ShizukuManager by lazy { ShizukuManager(appContext) }

    // Update 13: Deep Clean Pack
    val logFilesEngine: LogFilesEngine by lazy { LogFilesEngine(appContext) }

    // Update 14: Privacy, Modes & Auto-Rules
    val dailyQuotaStore: DailyQuotaStore by lazy { DailyQuotaStore(appContext) }
    val privacyProfileStore: PrivacyProfileStore by lazy { PrivacyProfileStore(appContext) }
    val modeStore: ModeStore by lazy { ModeStore(appContext) }
    val autoRuleStore: AutoRuleStore by lazy { AutoRuleStore(appContext) }
    val apkStaticScannerEngine: com.freeandroiddoctor.android.engine.privacy.ApkStaticScannerEngine by lazy {
        com.freeandroiddoctor.android.engine.privacy.ApkStaticScannerEngine(appContext)
    }
    val networkPrivacyEngine: com.freeandroiddoctor.android.engine.privacy.NetworkPrivacyEngine by lazy {
        com.freeandroiddoctor.android.engine.privacy.NetworkPrivacyEngine(appContext)
    }
    val privacyProfileEngine: com.freeandroiddoctor.android.engine.privacy.PrivacyProfileEngine by lazy {
        com.freeandroiddoctor.android.engine.privacy.PrivacyProfileEngine(
            appContext, permissionAuditEngine, clipboardEngine,
        )
    }
    val browserDataEngine: com.freeandroiddoctor.android.engine.privacy.BrowserDataEngine by lazy {
        com.freeandroiddoctor.android.engine.privacy.BrowserDataEngine(appContext)
    }
    val appModesEngine: com.freeandroiddoctor.android.engine.modes.AppModesEngine by lazy {
        com.freeandroiddoctor.android.engine.modes.AppModesEngine(
            modeStore, privacyProfileStore, settingsRepository, workScheduler,
        )
    }
    val autoRulesEngine: com.freeandroiddoctor.android.engine.automation.AutoRulesEngine by lazy {
        com.freeandroiddoctor.android.engine.automation.AutoRulesEngine(
            appContext, autoRuleStore, modeStore, appModesEngine, junkEngine, apkStaticScannerEngine,
        )
    }
}
