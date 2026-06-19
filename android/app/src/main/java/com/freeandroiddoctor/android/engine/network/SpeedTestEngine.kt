package com.freeandroiddoctor.android.engine.network

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit

data class SpeedResult(
    val success: Boolean,
    val mbps: Double = 0.0,
    val bytes: Long = 0,
    val millis: Long = 0,
    val error: String? = null,
)

/**
 * Simple download throughput test: streams a fixed-size payload from a public test
 * endpoint and measures wall-clock time. Requires only INTERNET.
 */
class SpeedTestEngine {

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    suspend fun run(): SpeedResult = withContext(Dispatchers.IO) {
        runCatching {
            val request = Request.Builder().url(TEST_URL).build()
            val start = System.nanoTime()
            var total = 0L
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) error("http_${response.code}")
                val source = response.body?.source() ?: error("empty_body")
                val buffer = ByteArray(64 * 1024)
                val stream = source.inputStream()
                var read = stream.read(buffer)
                while (read >= 0) {
                    total += read
                    read = stream.read(buffer)
                }
            }
            val millis = (System.nanoTime() - start) / 1_000_000
            val mbps = if (millis > 0) (total * 8.0 / 1_000_000.0) / (millis / 1000.0) else 0.0
            SpeedResult(success = true, mbps = mbps, bytes = total, millis = millis)
        }.getOrElse { SpeedResult(success = false, error = it.message) }
    }

    private companion object {
        // 10 MB Cloudflare speed-test payload.
        const val TEST_URL = "https://speed.cloudflare.com/__down?bytes=10000000"
    }
}
