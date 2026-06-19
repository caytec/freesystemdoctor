package com.freeandroiddoctor.android.core.result

data class CleanResult(
    val itemsRemoved: Int,
    val bytesFreed: Long,
    val failures: Int = 0,
)
