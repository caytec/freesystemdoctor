package com.freeandroiddoctor.android.ai

import com.freeandroiddoctor.android.data.ai.AiKeyStore
import java.util.Locale

class AiRepository(
    private val keyStore: AiKeyStore,
    private val client: AiClient = AiClient(),
) {

    fun hasKey(): Boolean = keyStore.hasKey()

    suspend fun analyze(provider: AiProvider, snapshot: DeviceHealthSnapshot): AiResult {
        val key = keyStore.getApiKey()
            ?: return AiResult.Error("missing_key")
        val polish = snapshot.locale.startsWith("pl")
        val system = if (polish) SYSTEM_PL else SYSTEM_EN
        val user = buildString {
            appendLine(if (polish) "Dane urządzenia:" else "Device data:")
            append(snapshot.toPromptText())
        }
        return client.complete(provider, key, system, user)
    }

    private companion object {
        const val SYSTEM_EN =
            "You are a concise Android maintenance assistant. Given a device-health snapshot, " +
                "give 3-5 specific, safe, no-root recommendations to free space, improve battery " +
                "and performance. Use short bullet points. Do not invent data you were not given."
        const val SYSTEM_PL =
            "Jesteś zwięzłym asystentem konserwacji Androida. Na podstawie obrazu kondycji urządzenia " +
                "podaj 3-5 konkretnych, bezpiecznych rekomendacji bez roota, aby zwolnić miejsce, " +
                "poprawić baterię i wydajność. Użyj krótkich punktów. Nie wymyślaj danych."
    }
}

fun currentLocaleTag(): String = Locale.getDefault().language
