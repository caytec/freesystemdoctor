package com.freesystemdoctor.android.core.result

data class CleanResult(
    val itemsRemoved: Int,
    val bytesFreed: Long,
    val failures: Int = 0,
)
