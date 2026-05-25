package com.freesystemdoctor.android.ai

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

sealed interface AiResult {
    data class Success(val content: String) : AiResult
    data class Error(val message: String) : AiResult
}

class AiClient(
    private val client: OkHttpClient = defaultClient(),
    private val json: Json = Json { ignoreUnknownKeys = true },
) {

    suspend fun complete(
        provider: AiProvider,
        apiKey: String,
        systemPrompt: String,
        userPrompt: String,
        model: String = provider.defaultModel,
    ): AiResult = complete(
        endpointUrl = provider.chatCompletionsUrl,
        providerName = provider.displayName,
        apiKey = apiKey,
        systemPrompt = systemPrompt,
        userPrompt = userPrompt,
        model = model,
    )

    suspend fun complete(
        endpointUrl: String,
        providerName: String,
        apiKey: String,
        systemPrompt: String,
        userPrompt: String,
        model: String,
    ): AiResult = withContext(Dispatchers.IO) {
        val payload = ChatRequest(
            model = model,
            messages = listOf(
                ChatMessage("system", systemPrompt),
                ChatMessage("user", userPrompt),
            ),
        )
        val body = json.encodeToString(payload)
            .toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url(endpointUrl)
            .addHeader("Authorization", "Bearer $apiKey")
            .post(body)
            .build()

        runCatching {
            client.newCall(request).execute().use { response ->
                val text = response.body?.string().orEmpty()
                if (!response.isSuccessful) {
                    return@withContext AiResult.Error("HTTP ${response.code}: ${text.take(300)}")
                }
                val parsed = json.decodeFromString<ChatResponse>(text)
                val content = parsed.choices.firstOrNull()?.message?.content?.trim()
                if (content.isNullOrEmpty()) {
                    AiResult.Error("Empty response from $providerName")
                } else {
                    AiResult.Success(content)
                }
            }
        }.getOrElse { AiResult.Error(it.message ?: "Network error") }
    }

    @Serializable
    private data class ChatRequest(
        val model: String,
        val messages: List<ChatMessage>,
        val temperature: Double = 0.4,
    )

    @Serializable
    private data class ChatMessage(val role: String, val content: String)

    @Serializable
    private data class ChatResponse(val choices: List<Choice> = emptyList())

    @Serializable
    private data class Choice(@SerialName("message") val message: ChatMessage)

    companion object {
        fun defaultClient(): OkHttpClient = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .build()
    }
}
