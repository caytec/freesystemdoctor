package com.freesystemdoctor.android.service

import android.service.quicksettings.Tile
import android.service.quicksettings.TileService
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.core.util.ByteFormatter
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Quick Settings tile that clears this app's own cache with one tap. */
class QuickCleanTileService : TileService() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    override fun onStartListening() {
        super.onStartListening()
        qsTile?.apply {
            state = Tile.STATE_INACTIVE
            label = getString(R.string.tile_clean_label)
            updateTile()
        }
    }

    override fun onClick() {
        super.onClick()
        val tile = qsTile ?: return
        tile.state = Tile.STATE_ACTIVE
        tile.updateTile()
        scope.launch {
            val freed = runCatching {
                ServiceLocator.junkEngine.cleanAppCache().bytesFreed
            }.getOrDefault(0L)
            withContext(Dispatchers.Main) {
                tile.state = Tile.STATE_INACTIVE
                tile.label = getString(R.string.tile_clean_freed, ByteFormatter.format(freed))
                tile.updateTile()
            }
        }
    }
}
