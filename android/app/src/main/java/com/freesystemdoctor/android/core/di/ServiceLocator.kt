package com.freesystemdoctor.android.core.di

import android.content.Context
import com.freesystemdoctor.android.ai.AiRepository
import com.freesystemdoctor.android.core.permission.PermissionManager
import com.freesystemdoctor.android.data.ai.AiKeyStore
import com.freesystemdoctor.android.data.settings.SettingsRepository
import com.freesystemdoctor.android.engine.apps.AppManagerEngine
import com.freesystemdoctor.android.engine.battery.BatteryEngine
import com.freesystemdoctor.android.engine.cache.JunkScannerEngine
import com.freesystemdoctor.android.engine.device.DeviceInfoEngine
import com.freesystemdoctor.android.engine.duplicates.DuplicateFinderEngine
import com.freesystemdoctor.android.engine.largefiles.LargeFilesEngine
import com.freesystemdoctor.android.engine.memory.MemoryEngine
import com.freesystemdoctor.android.engine.storage.StorageAnalyzerEngine

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
}
