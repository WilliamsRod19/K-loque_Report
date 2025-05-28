package com.puella_softworks.k_loque_reports

import android.os.Bundle
import android.widget.ImageView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class WelcomeActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_welcome)

        val tvWelcome = findViewById<TextView>(R.id.tvWelcome)
        val ivIcon = findViewById<ImageView>(R.id.ivIcon)

        val isAdmin = intent.getBooleanExtra("isAdmin", false)

        if (isAdmin) {
            tvWelcome.text = "Esta es una vista de administrador"
            ivIcon.setImageResource(R.drawable.ic_admin)
        } else {
            tvWelcome.text = "Esta es una vista de usuario"
            ivIcon.setImageResource(R.drawable.ic_user)
        }
    }
}