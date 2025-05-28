package com.puella_softworks.k_loque_reports

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.SwitchCompat
import com.auth0.android.jwt.JWT
import com.puella_softworks.k_loque_reports.classes.RetrofitClient
import com.puella_softworks.k_loque_reports.classes.SessionManager
import com.puella_softworks.k_loque_reports.models.UpdateUserRequest
import com.puella_softworks.k_loque_reports.models.UserData
import com.puella_softworks.k_loque_reports.models.UserDetailResponse
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.util.regex.Pattern

class EditUserActivity : AppCompatActivity() {

    private lateinit var currentUser: UserData
    private var isCurrentUser = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_edit_user)

        val userId = intent.getIntExtra("USER_ID", -1)
        if (userId == -1) {
            Toast.makeText(this, "ID de usuario no válido", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        // Verificar si es el usuario actual
        val token = SessionManager.getToken(this)
        val jwt = JWT(token!!)
        val currentUserId = jwt.getClaim("id").asInt() ?: 0
        isCurrentUser = userId == currentUserId

        loadUserDetails(userId)

        findViewById<Button>(R.id.btnSave).setOnClickListener {
            if (validateInputs()) {
                updateUser(userId)
            }
        }

        findViewById<Button>(R.id.btnCancel).setOnClickListener {
            finish()
        }
    }

    private fun loadUserDetails(userId: Int) {
        RetrofitClient.instance.getUserDetails(userId).enqueue(object : Callback<UserDetailResponse> {
            override fun onResponse(
                call: Call<UserDetailResponse>,
                response: Response<UserDetailResponse>
            ) {
                if (response.isSuccessful) {
                    response.body()?.data?.let { user ->
                        currentUser = user
                        displayUserDetails(user)
                    }
                } else {
                    Toast.makeText(this@EditUserActivity,
                        "Error al cargar detalles", Toast.LENGTH_SHORT).show()
                }
            }

            override fun onFailure(call: Call<UserDetailResponse>, t: Throwable) {
                Toast.makeText(this@EditUserActivity,
                    "Error de conexión", Toast.LENGTH_SHORT).show()
            }
        })
    }

    private fun displayUserDetails(user: UserData) {
        findViewById<EditText>(R.id.etFirstName).setText(user.first_name)
        findViewById<EditText>(R.id.etLastName).setText(user.last_name)
        findViewById<EditText>(R.id.etUsername).setText(user.username)
        findViewById<EditText>(R.id.etEmail).setText(user.email)

        val switchIsAdmin = findViewById<SwitchCompat>(R.id.switchIsAdmin)
        switchIsAdmin.isChecked = user.is_admin
        if (isCurrentUser) {
            switchIsAdmin.isEnabled = false
        }

        val switchIsActive = findViewById<SwitchCompat>(R.id.switchIsActive)
        switchIsActive.isChecked = user.is_active
        if (isCurrentUser) {
            switchIsActive.isEnabled = false
        }
    }

    private fun validateInputs(): Boolean {
        val etFirstName = findViewById<EditText>(R.id.etFirstName)
        val etLastName = findViewById<EditText>(R.id.etLastName)
        val etUsername = findViewById<EditText>(R.id.etUsername)
        val etEmail = findViewById<EditText>(R.id.etEmail)
        val etPassword = findViewById<EditText>(R.id.etPassword)
        val etConfirmPassword = findViewById<EditText>(R.id.etConfirmPassword)

        // Validar nombre (no números)
        if (etFirstName.text.toString().trim().isEmpty()) {
            etFirstName.error = "El nombre es requerido"
            return false
        } else if (containsNumbers(etFirstName.text.toString())) {
            etFirstName.error = "El nombre no puede contener números"
            return false
        }

        // Validar apellido (no números)
        if (etLastName.text.toString().trim().isEmpty()) {
            etLastName.error = "El apellido es requerido"
            return false
        } else if (containsNumbers(etLastName.text.toString())) {
            etLastName.error = "El apellido no puede contener números"
            return false
        }

        // Validar username (no espacios)
        if (etUsername.text.toString().trim().isEmpty()) {
            etUsername.error = "El nombre de usuario es requerido"
            return false
        } else if (etUsername.text.toString().contains(" ")) {
            etUsername.error = "El usuario no puede contener espacios"
            return false
        }

        // Validar email
        if (etEmail.text.toString().trim().isEmpty()) {
            etEmail.error = "El email es requerido"
            return false
        } else if (!android.util.Patterns.EMAIL_ADDRESS.matcher(etEmail.text.toString()).matches()) {
            etEmail.error = "Ingrese un email válido"
            return false
        }

        // Validar contraseña solo si se quiere cambiar
        val password = etPassword.text.toString()
        if (password.isNotEmpty()) {
            if (!isValidPassword(password)) {
                etPassword.error = "La contraseña debe tener al menos 8 caracteres, una mayúscula y un carácter especial"
                return false
            }

            if (password != etConfirmPassword.text.toString()) {
                etConfirmPassword.error = "Las contraseñas no coinciden"
                return false
            }
        }

        return true
    }

    private fun containsNumbers(text: String): Boolean {
        return text.matches(".*\\d.*".toRegex())
    }

    private fun isValidPassword(password: String): Boolean {
        val passwordPattern = "^(?=.*[A-Z])(?=.*[!@#\$&*]).{8,}\$"
        val pattern = Pattern.compile(passwordPattern)
        return pattern.matcher(password).matches()
    }

    private fun updateUser(userId: Int) {
        val etFirstName = findViewById<EditText>(R.id.etFirstName)
        val etLastName = findViewById<EditText>(R.id.etLastName)
        val etUsername = findViewById<EditText>(R.id.etUsername)
        val etEmail = findViewById<EditText>(R.id.etEmail)
        val etPassword = findViewById<EditText>(R.id.etPassword)
        val switchIsAdmin = findViewById<SwitchCompat>(R.id.switchIsAdmin)
        val switchIsActive = findViewById<SwitchCompat>(R.id.switchIsActive)

        val request = UpdateUserRequest(
            first_name = etFirstName.text.toString().trim(),
            last_name = etLastName.text.toString().trim(),
            username = etUsername.text.toString().trim(),
            email = etEmail.text.toString().trim(),
            password = if (etPassword.text.isNotEmpty()) etPassword.text.toString() else null,
            is_admin = switchIsAdmin.isChecked,
            is_active = switchIsActive.isChecked
        )

        RetrofitClient.instance.updateUser(userId, request).enqueue(object : Callback<UserDetailResponse> {
            override fun onResponse(
                call: Call<UserDetailResponse>,
                response: Response<UserDetailResponse>
            ) {
                if (response.isSuccessful) {
                    Toast.makeText(
                        this@EditUserActivity,
                        "Usuario actualizado exitosamente",
                        Toast.LENGTH_SHORT
                    ).show()
                    finish()
                } else {
                    Toast.makeText(
                        this@EditUserActivity,
                        "Error al actualizar usuario: ${response.message()}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }

            override fun onFailure(call: Call<UserDetailResponse>, t: Throwable) {
                Toast.makeText(
                    this@EditUserActivity,
                    "Error de conexión: ${t.message}",
                    Toast.LENGTH_SHORT
                ).show()
            }
        })
    }
}