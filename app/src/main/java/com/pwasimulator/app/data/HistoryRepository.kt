package com.pwasimulator.app.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringSetPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "pwa_history")

class HistoryRepository(private val context: Context) {

    companion object {
        private val HISTORY_KEY = stringSetPreferencesKey("history_urls")
    }

    val historyFlow: Flow<List<String>> = context.dataStore.data
        .map { preferences ->
            val set = preferences[HISTORY_KEY] ?: emptySet()
            set.toList().sorted() // or keep insertion order if stored differently, but set is unordered.
        }

    suspend fun addUrl(url: String) {
        val cleanedUrl = url.trim()
        if (cleanedUrl.isEmpty()) return
        context.dataStore.edit { preferences ->
            val currentSet = preferences[HISTORY_KEY] ?: emptySet()
            // Keep recent URLs, limit to e.g. 50 items
            val newSet = mutableSetOf(cleanedUrl)
            newSet.addAll(currentSet)
            if (newSet.size > 50) {
                // Drop oldest if needed, or take first 50
            }
            preferences[HISTORY_KEY] = newSet
        }
    }

    suspend fun removeUrl(url: String) {
        context.dataStore.edit { preferences ->
            val currentSet = preferences[HISTORY_KEY] ?: emptySet()
            val newSet = currentSet.toMutableSet()
            newSet.remove(url)
            preferences[HISTORY_KEY] = newSet
        }
    }

    suspend fun clearHistory() {
        context.dataStore.edit { preferences ->
            preferences.remove(HISTORY_KEY)
        }
    }
}
