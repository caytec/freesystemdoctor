package com.freesystemdoctor.android.core.di

import android.content.Context
import com.freesystemdoctor.android.ai.AiRepository
import com.freesystemdoctor.android.core.media.MediaDeleteHelper
import com.freesystemdoctor.android.core.permission.PermissionManager
import com.freesystemdoctor.android.data.ai.AiKeyStore
import com.freesystemdoctor.android.data.saf.SafTreeStore
import com.freesystemdoctor.android.data.settings.SettingsRepository
import com.freesystemdoctor.android.engine.files.FileShredderEngine
import com.freesystemdoctor.android.engine.files.SafTreeEngine
import com.freesystemdoctor.android.engine.network.DataUsageEngine
import com.freesystemdoctor.android.engine.system.SystemTweaksEngine
import com.freesystemdoctor.android.engine.apps.AppManagerEngine
import com.freesystemdoctor.android.engine.apps.AppUsageEngine
import com.freesystemdoctor.android.engine.apps.ApkExtractorEngine
import com.freesystemdoctor.android.engine.apps.PermissionAuditEngine
import com.freesystemdoctor.android.engine.apps.RarelyUsedEngine
import com.freesystemdoctor.android.engine.battery.BatteryEngine
import com.freesystemdoctor.android.engine.cache.JunkScannerEngine
import com.freesystemdoctor.android.engine.device.DeviceInfoEngine
import com.freesystemdoctor.android.engine.duplicates.DuplicateFinderEngine
import com.freesystemdoctor.android.engine.largefiles.LargeFilesEngine
import com.freesystemdoctor.android.engine.media.BlurScreenshotEngine
import com.freesystemdoctor.android.engine.media.ImageCompressionEngine
import com.freesystemdoctor.android.engine.media.MediaStoreCategoryEngine
import com.freesystemdoctor.android.engine.media.SimilarPhotoEngine
import com.freesystemdoctor.android.engine.memory.MemoryEngine
import com.freesystemdoctor.android.engine.network.WifiAnalyzerEngine
import com.freesystemdoctor.android.engine.storage.StorageAnalyzerEngine
import com.freesystemdoctor.android.engine.system.ClipboardCleanerEngine
import com.freesystemdoctor.android.work.WorkScheduler

/** Minimal manual dependency container; initialized once from the Application. */
object ServiceLocator {

    private lateinit var appContext: Context

    fun init(context: Context) {
        appContext = context.applicationContext
    }

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
}
