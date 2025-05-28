package com.puella_softworks.k_loque_reports

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class LoginActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_login)

        val etUsername = findViewById<EditText>(R.id.etUsername)
        val etPassword = findViewById<EditText>(R.id.etPassword)
        val btnLogin = findViewById<Button>(R.id.btnLogin)

        btnLogin.setOnClickListener {
            val username = etUsername.text.toString()
            val password = etPassword.text.toString()

            if (username == "Usuario" && password == "123") {
                openWelcomeScreen(isAdmin = false)
            } else if (username == "Administrador" && password == "123") {
                openWelcomeScreen(isAdmin = true)
            } else {
                Toast.makeText(this, "Credenciales incorrectas", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun openWelcomeScreen(isAdmin: Boolean) {
        val intent = Intent(this, WelcomeActivity::class.java)
        intent.putExtra("isAdmin", isAdmin)
        startActivity(intent)
    }
}