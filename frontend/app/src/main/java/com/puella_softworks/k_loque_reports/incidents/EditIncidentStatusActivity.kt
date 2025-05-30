package com.puella_softworks.k_loque_reports.incidents

import android.os.Bundle
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.Spinner
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.auth0.android.jwt.JWT
import com.puella_softworks.k_loque_reports.R
import com.puella_softworks.k_loque_reports.classes.RetrofitClient
import com.puella_softworks.k_loque_reports.classes.SessionManager
import com.puella_softworks.k_loque_reports.models.IncidentDetailResponse
import com.puella_softworks.k_loque_reports.models.UpdateIncidentRequest
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class EditIncidentStatusActivity : AppCompatActivity() {

    private var incidentId: Int = -1

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_edit_incident_status)

        incidentId = intent.getIntExtra("INCIDENT_ID", -1)
        if (incidentId == -1) {
            Toast.makeText(this, "ID de incidente no válido", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        val spinnerStatus = findViewById<Spinner>(R.id.spinnerStatus)
        val etComment = findViewById<EditText>(R.id.etComment)
        val btnSave = findViewById<Button>(R.id.btnSave)
        val btnCancel = findViewById<Button>(R.id.btnCancel)

        val statusOptions = arrayOf("RESUELTO", "PENDIENTE", "ACTIVO", "CANCELADO")
        val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_item, statusOptions)
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        spinnerStatus.adapter = adapter

        btnSave.setOnClickListener {
            val comment = etComment.text.toString().trim()
            if (comment.isEmpty()) {
                etComment.error = "El comentario es obligatorio"
                return@setOnClickListener
            }

            val status = spinnerStatus.selectedItem.toString()
            updateIncident(comment, status)
        }

        btnCancel.setOnClickListener {
            finish()
        }
    }

    private fun updateIncident(comment: String, status: String) {
        val request = UpdateIncidentRequest(
            comment = comment,
            status = status.lowercase()
        )

        RetrofitClient.instance.updateIncident(incidentId, request)
            .enqueue(object : Callback<IncidentDetailResponse> {
                override fun onResponse(
                    call: Call<IncidentDetailResponse>,
                    response: Response<IncidentDetailResponse>
                ) {
                    if (response.isSuccessful) {
                        Toast.makeText(
                            this@EditIncidentStatusActivity,
                            "Incidente actualizado correctamente",
                            Toast.LENGTH_SHORT
                        ).show()
                        setResult(RESULT_OK)
                        finish()
                    } else {
                        Toast.makeText(
                            this@EditIncidentStatusActivity,
                            "Error al actualizar el incidente: ${response.message()}",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                }

                override fun onFailure(call: Call<IncidentDetailResponse>, t: Throwable) {
                    Toast.makeText(
                        this@EditIncidentStatusActivity,
                        "Error de conexión: ${t.message}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            })
    }
}