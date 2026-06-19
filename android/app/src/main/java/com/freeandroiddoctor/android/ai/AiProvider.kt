package com.freeandroiddoctor.android.ai

/** OpenAI-compatible chat-completions providers, in fallback priority order. */
enum class AiProvider(
    val displayName: String,
    val baseUrl: String,
    val defaultModel: String,
) {
    CEREBRAS(
        displayName = "Cerebras",
        baseUrl = "https://api.cerebras.ai/v1",
        defaultModel = "llama-3.3-70b",
    ),
    GROQ(
        displayName = "Groq",
        baseUrl = "https://api.groq.com/openai/v1",
        defaultModel = "llama-3.3-70b-versatile",
    ),
    OPENROUTER(
        displayName = "OpenRouter",
        baseUrl = "https://openrouter.ai/api/v1",
        defaultModel = "meta-llama/llama-3.3-70b-instruct",
    );

    val chatCompletionsUrl: String get() = "$baseUrl/chat/completions"
}
