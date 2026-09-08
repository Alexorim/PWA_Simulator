package com.pwasimulator.app.utils

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.core.content.pm.ShortcutInfoCompat
import androidx.core.content.pm.ShortcutManagerCompat
import androidx.core.graphics.drawable.IconCompat
import com.pwasimulator.app.MainActivity

object PwaInstaller {

    fun installPwaShortcut(context: Context, url: String, title: String? = null) {
        var trimmedUrl = url.trim()
        if (trimmedUrl.isEmpty()) return

        if (!trimmedUrl.startsWith("http://") && !trimmedUrl.startsWith("https://")) {
            trimmedUrl = "https://$trimmedUrl"
        }

        val label = if (!title.isNullOrBlank()) {
            title
        } else {
            try {
                val uri = Uri.parse(trimmedUrl)
                uri.host?.removePrefix("www.") ?: trimmedUrl
            } catch (e: Exception) {
                trimmedUrl
            }
        }

        val shortcutIntent = Intent(context, MainActivity::class.java).apply {
            action = Intent.ACTION_VIEW
            putExtra("url", trimmedUrl)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }

        val shortcutId = "pwa_${trimmedUrl.hashCode()}"

        val shortcutInfo = ShortcutInfoCompat.Builder(context, shortcutId)
            .setShortLabel(label)
            .setLongLabel(trimmedUrl)
            .setIcon(IconCompat.createWithResource(context, android.R.drawable.sym_def_app_icon))
            .setIntent(shortcutIntent)
            .build()

        if (ShortcutManagerCompat.isRequestPinShortcutSupported(context)) {
            val pinned = ShortcutManagerCompat.requestPinShortcut(context, shortcutInfo, null)
            if (pinned) {
                Toast.makeText(context, "Solicitud para instalar \"$label\" enviada", Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(context, "No se pudo solicitar la instalación de la PWA", Toast.LENGTH_SHORT).show()
            }
        } else {
            Toast.makeText(context, "La instalación de accesos directos no está soportada en tu dispositivo", Toast.LENGTH_LONG).show()
        }
    }
}
