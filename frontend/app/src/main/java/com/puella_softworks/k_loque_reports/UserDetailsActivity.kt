package com.puella_softworks.k_loque_reports

import android.app.AlertDialog
import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.widget.Button
import android.widget.CheckBox
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.auth0.android.jwt.JWT
import com.puella_softworks.k_loque_reports.classes.RetrofitClient
import com.puella_softworks.k_loque_reports.classes.SessionManager
import com.puella_softworks.k_loque_reports.models.UserData
import com.puella_softworks.k_loque_reports.models.UserDetailResponse
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class UserDetailsActivity : AppCompatActivity() {

    private var userId: Int = -1
    private var isCurrentUser = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_user_details)

        userId = intent.getIntExtra("USER_ID", -1)
        if (userId == -1) {
            Toast.makeText(this, "ID de usuario no válido", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        val token = SessionManager.getToken(this)
        val jwt = JWT(token!!)
        val currentUserId = jwt.getClaim("id").asInt() ?: 0
        isCurrentUser = userId == currentUserId

        val btnEditUser = findViewById<Button>(R.id.btnEditUser)
        btnEditUser.setOnClickListener {
            val intent = Intent(this, EditUserActivity::class.java)
            intent.putExtra("USER_ID", userId)
            startActivity(intent)
        }

        val btnDeleteUser = findViewById<Button>(R.id.btnDeleteUser)
        btnDeleteUser.setOnClickListener {
            if (isCurrentUser) {
                Toast.makeText(this, "No puedes eliminar tu propio usuario", Toast.LENGTH_LONG).show()
            } else {
                showDeleteConfirmationDialog()
            }
        }

        if (isCurrentUser) {
            btnDeleteUser.visibility = View.GONE
        }

        loadUserDetails(userId)

        findViewById<Button>(R.id.btnBack).setOnClickListener {
            finish()
        }
    }

    private fun showDeleteConfirmationDialog() {
        val dialogView = LayoutInflater.from(this).inflate(R.layout.dialog_confirm_delete, null)
        val cbConfirmDelete = dialogView.findViewById<CheckBox>(R.id.cbConfirmDelete)
        val btnConfirmDelete = dialogView.findViewById<Button>(R.id.btnConfirmDelete)
        val btnCancelDelete = dialogView.findViewById<Button>(R.id.btnCancelDelete)

        val dialog = AlertDialog.Builder(this)
            .setView(dialogView)
            .setCancelable(false)
            .create()

        btnConfirmDelete.setOnClickListener {
            if (cbConfirmDelete.isChecked) {
                deleteUser()
                dialog.dismiss()
            } else {
                Toast.makeText(this, "Debes aceptar la confirmación para continuar", Toast.LENGTH_SHORT).show()
            }
        }

        btnCancelDelete.setOnClickListener {
            dialog.dismiss()
        }

        dialog.show()
    }

    private fun deleteUser() {
        RetrofitClient.instance.deleteUser(userId).enqueue(object : Callback<Void> {
            override fun onResponse(call: Call<Void>, response: Response<Void>) {
                if (response.isSuccessful) {
                    Toast.makeText(
                        this@UserDetailsActivity,
                        "Usuario eliminado exitosamente",
                        Toast.LENGTH_SHORT
                    ).show()

                    setResult(RESULT_OK)
                    finish()
                } else {
                    Toast.makeText(
                        this@UserDetailsActivity,
                        "Error al eliminar usuario: ${response.message()}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }

            override fun onFailure(call: Call<Void>, t: Throwable) {
                Toast.makeText(
                    this@UserDetailsActivity,
                    "Error de conexión: ${t.message}",
                    Toast.LENGTH_SHORT
                ).show()
            }
        })
    }

    private fun loadUserDetails(userId: Int) {
        RetrofitClient.instance.getUserDetails(userId).enqueue(object : Callback<UserDetailResponse> {
            override fun onResponse(
                call: Call<UserDetailResponse>,
                response: Response<UserDetailResponse>
            ) {
                if (response.isSuccessful) {
                    response.body()?.data?.let { user ->
                        displayUserDetails(user)
                    }
                } else {
                    Toast.makeText(this@UserDetailsActivity,
                        "Error al cargar detalles", Toast.LENGTH_SHORT).show()
                }
            }

            override fun onFailure(call: Call<UserDetailResponse>, t: Throwable) {
                Toast.makeText(this@UserDetailsActivity,
                    "Error de conexión", Toast.LENGTH_SHORT).show()
            }
        })
    }

    private fun displayUserDetails(user: UserData) {
        val ivUser = findViewById<ImageView>(R.id.ivUser)
        ivUser.setImageResource(if (user.is_admin) R.drawable.ic_admin else R.drawable.ic_user)
        findViewById<TextView>(R.id.tvUsername).text = "@${user.username}"
        findViewById<TextView>(R.id.tvFullName).text = "${user.first_name} ${user.last_name}"
        findViewById<TextView>(R.id.tvEmail).text = user.email
        findViewById<TextView>(R.id.tvStatus).text = if (user.is_active) "Activo" else "Inactivo"
        findViewById<TextView>(R.id.tvRole).text = if (user.is_admin) "Administrador" else "Usuario"
        findViewById<TextView>(R.id.tvLastLogin).text = user.last_login
        findViewById<TextView>(R.id.tvDateJoined).text = user.date_joined
    }
}