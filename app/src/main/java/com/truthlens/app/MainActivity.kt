package com.truthlens.app

import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.Executors

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { TruthLensScreen() }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TruthLensScreen() {
    val context = LocalContext.current
    var selectedUri by remember { mutableStateOf<Uri?>(null) }
    var resultText by remember { mutableStateOf("Выбери изображение, чтобы начать проверку.") }
    var details by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) {
        selectedUri = it
        resultText = "Изображение выбрано. Нажми «Проверить»."
        details = ""
    }

    MaterialTheme(colorScheme = darkColorScheme()) {
        Scaffold { padding ->
            Column(
                modifier = Modifier.fillMaxSize().padding(padding).padding(24.dp).verticalScroll(rememberScrollState()),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(18.dp)
            ) {
                Text("TRUTHLENS", style = MaterialTheme.typography.headlineLarge)
                Text("Проверка происхождения изображения", style = MaterialTheme.typography.bodyLarge)
                OutlinedButton(onClick = { picker.launch("image/*") }, modifier = Modifier.fillMaxWidth()) {
                    Text(if (selectedUri == null) "Выбрать изображение" else "Выбрать другое изображение")
                }
                if (selectedUri != null) Text("Файл готов к отправке на сервер", color = MaterialTheme.colorScheme.primary)
                Button(
                    onClick = {
                        val uri = selectedUri ?: return@Button
                        if (BuildConfig.API_BASE_URL.contains("YOUR-SERVER")) {
                            resultText = "Сервер ещё не подключён."
                            details = "Сначала нужно развернуть backend и прописать его адрес в настройках сборки."
                        } else {
                            busy = true
                            resultText = "Анализируем изображение…"
                            Executors.newSingleThreadExecutor().execute {
                                try {
                                    val bytes = context.contentResolver.openInputStream(uri)!!.use { it.readBytes() }
                                    val body = MultipartBody.Builder().setType(MultipartBody.FORM)
                                        .addFormDataPart("file", "image.jpg", bytes.toRequestBody("application/octet-stream".toMediaType()))
                                        .build()
                                    val request = Request.Builder().url(BuildConfig.API_BASE_URL.trimEnd('/') + "/analyze").post(body).build()
                                    val response = OkHttpClient().newCall(request).execute()
                                    val responseText = response.body?.string().orEmpty()
                                    if (!response.isSuccessful) throw Exception("HTTP ${response.code}: $responseText")
                                    val json = JSONObject(responseText)
                                    val verdict = json.optString("verdict", "unknown")
                                    val confidence = json.optDouble("confidence", 0.0)
                                    val label = when (verdict) {
                                        "ai" -> "Вероятно, создано ИИ"
                                        "real" -> "Вероятно, реальная фотография"
                                        else -> "Недостаточно данных для вывода"
                                    }
                                    val extra = "Оценка модели: ${"%.1f".format(confidence * 100)}%\nМодель: ${json.optString("model", "не указана")}\n\nЭто вероятностная оценка, а не доказательство."
                                    Handler(Looper.getMainLooper()).post {
                                        resultText = label
                                        details = extra
                                        busy = false
                                    }
                                } catch (e: Exception) {
                                    Handler(Looper.getMainLooper()).post {
                                        resultText = "Не удалось выполнить проверку"
                                        details = e.message ?: "Ошибка соединения"
                                        busy = false
                                    }
                                }
                            }
                        }
                    },
                    enabled = selectedUri != null && !busy,
                    modifier = Modifier.fillMaxWidth()
                ) { Text(if (busy) "Проверяем…" else "Проверить изображение") }
                if (busy) CircularProgressIndicator()
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(resultText, style = MaterialTheme.typography.titleLarge)
                        if (details.isNotBlank()) Text(details, style = MaterialTheme.typography.bodyMedium)
                    }
                }
                Text("Важно: детекторы могут ошибаться. Результат нельзя считать абсолютным доказательством.", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
