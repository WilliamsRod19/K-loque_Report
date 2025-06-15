package com.puella_softworks.k_loque_reports

import android.app.Activity
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.puella_softworks.k_loque_reports.classes.RetrofitClient
import com.puella_softworks.k_loque_reports.models.CreateUserRequest
import com.puella_softworks.k_loque_reports.models.UserResponse
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.util.regex.Pattern

class CreateUserActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_create_user)

        val etFirstName = findViewById<EditText>(R.id.etFirstName)
        val etLastName = findViewById<EditText>(R.id.etLastName)
        val etUsername = findViewById<EditText>(R.id.etUsername)
        val etEmail = findViewById<EditText>(R.id.etEmail)
        val etPassword = findViewById<EditText>(R.id.etPassword)
        val etConfirmPassword = findViewById<EditText>(R.id.etConfirmPassword)

        findViewById<Button>(R.id.btnCreateUser).setOnClickListener {
            if (validateInputs(
                    etFirstName,
                    etLastName,
                    etUsername,
                    etEmail,
                    etPassword,
                    etConfirmPassword
                )
            ) {
                createUser(
                    etFirstName.text.toString().trim(),
                    etLastName.text.toString().trim(),
                    etUsername.text.toString().trim(),
                    etEmail.text.toString().trim(),
                    etPassword.text.toString()
                )
            }
        }

        findViewById<Button>(R.id.btnCancel).setOnClickListener {
            finish()
        }
    }

    private fun validateInputs(
        etFirstName: EditText,
        etLastName: EditText,
        etUsername: EditText,
        etEmail: EditText,
        etPassword: EditText,
        etConfirmPassword: EditText
    ): Boolean {
        if (etFirstName.text.toString().trim().isEmpty()) {
            etFirstName.error = "El nombre es requerido"
            return false
        } else if (containsNumbers(etFirstName.text.toString())) {
            etFirstName.error = "El nombre no puede contener números"
            return false
        }

        if (etLastName.text.toString().trim().isEmpty()) {
            etLastName.error = "El apellido es requerido"
            return false
        } else if (containsNumbers(etLastName.text.toString())) {
            etLastName.error = "El apellido no puede contener números"
            return false
        }

        if (etUsername.text.toString().trim().isEmpty()) {
            etUsername.error = "El nombre de usuario es requerido"
            return false
        } else if (etUsername.text.toString().contains(" ")) {
            etUsername.error = "El usuario no puede contener espacios"
            return false
        }

        if (etEmail.text.toString().trim().isEmpty()) {
            etEmail.error = "El email es requerido"
            return false
        } else if (!android.util.Patterns.EMAIL_ADDRESS.matcher(etEmail.text.toString()).matches()) {
            etEmail.error = "Ingrese un email válido"
            return false
        }

        if (etPassword.text.toString().isEmpty()) {
            etPassword.error = "La contraseña es requerida"
            return false
        } else if (!isValidPassword(etPassword.text.toString())) {
            etPassword.error = "La contraseña debe tener al menos 8 caracteres, una mayúscula y un carácter especial"
            return false
        }

        if (etConfirmPassword.text.toString() != etPassword.text.toString()) {
            etConfirmPassword.error = "Las contraseñas no coinciden"
            return false
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

    private fun createUser(
        firstName: String,
        lastName: String,
        username: String,
        email: String,
        password: String
    ) {
        val request = CreateUserRequest(
            first_name = firstName,
            last_name = lastName,
            username = username,
            email = email,
            password = password
        )

        RetrofitClient.instance.createUser(request).enqueue(object : Callback<UserResponse> {
            override fun onResponse(call: Call<UserResponse>, response: Response<UserResponse>) {
                if (response.isSuccessful) {
                    Toast.makeText(
                        this@CreateUserActivity,
                        "Usuario creado exitosamente",
                        Toast.LENGTH_SHORT
                    ).show()
                    setResult(Activity.RESULT_OK)
                    finish()
                } else {
                    Toast.makeText(
                        this@CreateUserActivity,
                        "Error al crear usuario: ${response.message()}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }

            override fun onFailure(call: Call<UserResponse>, t: Throwable) {
                Toast.makeText(
                    this@CreateUserActivity,
                    "Error de conexión: ${t.message}",
                    Toast.LENGTH_SHORT
                ).show()
            }
        })
    }
}