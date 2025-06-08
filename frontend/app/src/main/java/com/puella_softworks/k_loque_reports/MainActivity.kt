package com.puella_softworks.k_loque_reports

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.util.Log
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.FileProvider
import com.auth0.android.jwt.JWT
import com.puella_softworks.k_loque_reports.classes.RetrofitClient
import com.puella_softworks.k_loque_reports.classes.SessionManager
import com.puella_softworks.k_loque_reports.incidents.IncidentsActivity
import okhttp3.ResponseBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val token = SessionManager.getToken(this)
        if (token == null) {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
            return
        }

        try {
            val jwt = JWT(token)
            val isSuperuser = jwt.getClaim("is_superuser").asBoolean() ?: false
            val first_name = jwt.getClaim("first_name").asString() ?: "Usuario"
            val last_name = jwt.getClaim("last_name").asString() ?: "sin nombre"

            val tvWelcome = findViewById<TextView>(R.id.tvWelcome)
            val adminButtons = findViewById<LinearLayout>(R.id.adminButtons)
            val userButtons = findViewById<LinearLayout>(R.id.userButtons)

            if (isSuperuser) {
                tvWelcome.text = "Bienvenido $first_name $last_name al panel de administrador"
                adminButtons.visibility = LinearLayout.VISIBLE

                findViewById<Button>(R.id.btnUsersPanel).setOnClickListener {
                    startActivity(Intent(this, UsersActivity::class.java))
                }

                findViewById<Button>(R.id.btnAllTickets).setOnClickListener {
                    startActivity(Intent(this, IncidentsActivity::class.java))
                }

                findViewById<Button>(R.id.btnApiPanel).setOnClickListener {
                    try {
                        val intent = Intent(Intent.ACTION_VIEW, Uri.parse("http://GenshinImpact/admin/"))
                        startActivity(intent)
                    } catch (e: Exception) {
                        Toast.makeText(this, "No se pudo abrir el panel de administración", Toast.LENGTH_SHORT).show()
                        Log.e("MainActivity", "Error al abrir URL: ${e.message}")
                    }
                }
                findViewById<Button>(R.id.btnDownloadReports).setOnClickListener {
                    downloadReport()
                }

            } else {
                tvWelcome.text = "Bienvenido $first_name $last_name a tu app de reportes de incidentes"
                userButtons.visibility = LinearLayout.VISIBLE
                findViewById<Button>(R.id.btnTickets).setOnClickListener {
                    startActivity(Intent(this, IncidentsActivity::class.java))
                }
                findViewById<Button>(R.id.btnDownloadUserReports).setOnClickListener {
                    downloadReport()
                }
            }

            findViewById<Button>(R.id.btnLogout).setOnClickListener {
                SessionManager.clearSession(this)
                startActivity(Intent(this, LoginActivity::class.java))
                finish()
            }

        } catch (e: Exception) {
            Toast.makeText(this, "Error al cargar los datos del usuario", Toast.LENGTH_SHORT).show()
            Log.e("MainActivity", "Error en onCreate: ${e.message}")
            SessionManager.clearSession(this)
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
        }
    }
    private fun downloadReport() {
        val loadingToast = Toast.makeText(this, "Generando reporte...", Toast.LENGTH_SHORT)
        loadingToast.show()

        RetrofitClient.instance.getActiveReports().enqueue(object : Callback<ResponseBody> {
            override fun onResponse(call: Call<ResponseBody>, response: Response<ResponseBody>) {
                loadingToast.cancel()

                if (response.isSuccessful && response.body() != null) {
                    saveReportToFile(response.body()!!)
                    Toast.makeText(this@MainActivity, "Descargando reporte...", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this@MainActivity, "Error al generar el reporte", Toast.LENGTH_SHORT).show()
                    Log.e("MainActivity", "Error en la respuesta: ${response.code()}")
                }
            }

            override fun onFailure(call: Call<ResponseBody>, t: Throwable) {
                loadingToast.cancel()
                Toast.makeText(this@MainActivity, "Error de conexión: ${t.message}", Toast.LENGTH_SHORT).show()
                Log.e("MainActivity", "Error en la descarga: ${t.message}")
            }
        })
    }

    private fun saveReportToFile(body: ResponseBody) {
        try {
            val timeStamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
            val fileName = "Reporte_Incidentes_$timeStamp.pdf"

            val downloadsDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
            val file = File(downloadsDir, fileName)

            val inputStream = body.byteStream()
            val outputStream = FileOutputStream(file)

            inputStream.use { input ->
                outputStream.use { output ->
                    input.copyTo(output)
                }
            }

            val fileUri = FileProvider.getUriForFile(this, "com.puella_softworks.k_loque_reports.provider", file)
            val intent = Intent(Intent.ACTION_VIEW)
            intent.setDataAndType(fileUri, "application/pdf")
            intent.flags = Intent.FLAG_ACTIVITY_NO_HISTORY or Intent.FLAG_GRANT_READ_URI_PERMISSION
            try {
                startActivity(intent)
            } catch (e: Exception) {
                Toast.makeText(this, "No hay aplicación para ver PDFs", Toast.LENGTH_SHORT).show()
                Log.e("MainActivity", "Error al abrir PDF: ${e.message}")
            }

        } catch (e: Exception) {
            Toast.makeText(this, "Error al guardar el archivo", Toast.LENGTH_SHORT).show()
            Log.e("MainActivity", "Error al guardar PDF: ${e.message}")
        }
    }
}