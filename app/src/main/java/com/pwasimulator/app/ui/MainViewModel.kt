package com.pwasimulator.app.ui

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.pwasimulator.app.data.HistoryRepository
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class MainViewModel(application: Application) : AndroidViewModel(application) {

    private val repository = HistoryRepository(application)

    var urlInput by mutableStateOf("")
        private set

    val history: StateFlow<List<String>> = repository.historyFlow
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )

    fun updateUrl(newUrl: String) {
        urlInput = newUrl
    }

    fun sanitizeAndFormatUrl(input: String): String {
        var trimmed = input.trim()
        if (trimmed.isEmpty()) return ""
        if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) {
            trimmed = "https://$trimmed"
        }
        return trimmed
    }

    fun saveAndGetUrl(): String {
        val formatted = sanitizeAndFormatUrl(urlInput)
        if (formatted.isNotEmpty()) {
            viewModelScope.launch {
                repository.addUrl(formatted)
            }
        }
        return formatted
    }

    fun installPwa(context: android.content.Context, targetUrl: String? = null, title: String? = null) {
        val raw = if (!targetUrl.isNullOrBlank()) targetUrl else urlInput
        val formatted = sanitizeAndFormatUrl(raw)
        if (formatted.isNotEmpty()) {
            viewModelScope.launch {
                repository.addUrl(formatted)
            }
            com.pwasimulator.app.utils.PwaInstaller.installPwaShortcut(context, formatted, title)
        }
    }

    fun deleteHistoryItem(url: String) {
        viewModelScope.launch {
            repository.removeUrl(url)
        }
    }

    fun clearHistory() {
        viewModelScope.launch {
            repository.clearHistory()
        }
    }
}
