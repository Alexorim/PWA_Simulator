package com.pwasimulator.app

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.pwasimulator.app.ui.MainViewModel
import com.pwasimulator.app.ui.screens.HomeScreen
import com.pwasimulator.app.ui.screens.PwaRunnerScreen
import java.net.URLDecoder
import java.net.URLEncoder
import java.nio.charset.StandardCharsets

class MainActivity : ComponentActivity() {

    private val viewModel: MainViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val targetUrl = intent?.getStringExtra("url")

        setContent {
            MaterialTheme(
                colorScheme = androidx.compose.material3.darkColorScheme()
            ) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val navController = rememberNavController()

                    val startDestination = if (!targetUrl.isNullOrEmpty()) {
                        val encoded = URLEncoder.encode(targetUrl, StandardCharsets.UTF_8.toString())
                        "pwa_runner/$encoded"
                    } else {
                        "home"
                    }

                    NavHost(navController = navController, startDestination = startDestination) {
                        composable("home") {
                            HomeScreen(
                                viewModel = viewModel,
                                onOpenPwa = { url ->
                                    val encodedUrl = URLEncoder.encode(url, StandardCharsets.UTF_8.toString())
                                    navController.navigate("pwa_runner/$encodedUrl")
                                }
                            )
                        }
                        composable(
                            route = "pwa_runner/{url}",
                            arguments = listOf(navArgument("url") { type = NavType.StringType })
                        ) { backStackEntry ->
                            val encodedUrl = backStackEntry.arguments?.getString("url") ?: ""
                            val url = URLDecoder.decode(encodedUrl, StandardCharsets.UTF_8.toString())
                            PwaRunnerScreen(
                                url = url,
                                onBack = {
                                    navController.popBackStack()
                                }
                            )
                        }
                    }
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        val url = intent.getStringExtra("url")
        if (!url.isNullOrEmpty()) {
            val intentToLaunch = Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                putExtra("url", url)
            }
            startActivity(intentToLaunch)
            finish()
        }
    }
}
