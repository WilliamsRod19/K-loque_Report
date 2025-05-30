package com.puella_softworks.k_loque_reports

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.auth0.android.jwt.JWT
import com.puella_softworks.k_loque_reports.classes.SessionManager
import com.puella_softworks.k_loque_reports.incidents.IncidentsActivity

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
                        val intent = Intent(Intent.ACTION_VIEW, Uri.parse("http://192.168.0.10:8000/admin/"))
                        startActivity(intent)
                    } catch (e: Exception) {
                        Toast.makeText(this, "No se pudo abrir el panel de administración", Toast.LENGTH_SHORT).show()
                        Log.e("MainActivity", "Error al abrir URL: ${e.message}")
                    }
                }
            } else {
                tvWelcome.text = "Bienvenido $first_name $last_name a tu app de reportes de incidentes"
                userButtons.visibility = LinearLayout.VISIBLE
                findViewById<Button>(R.id.btnTickets).setOnClickListener {
                    startActivity(Intent(this, IncidentsActivity::class.java))
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
}