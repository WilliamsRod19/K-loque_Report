package com.puella_softworks.k_loque_reports.incidents

import android.content.ContentValues
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.drawable.Drawable
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.view.View
import android.widget.*
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.auth0.android.jwt.JWT
import com.bumptech.glide.Glide
import com.bumptech.glide.request.target.CustomTarget
import com.bumptech.glide.request.transition.Transition
import com.puella_softworks.k_loque_reports.R
import com.puella_softworks.k_loque_reports.classes.RetrofitClient
import com.puella_softworks.k_loque_reports.classes.SessionManager
import com.puella_softworks.k_loque_reports.models.Incident
import com.puella_softworks.k_loque_reports.models.IncidentDetailResponse
import com.puella_softworks.k_loque_reports.models.SoftDeleteRequest
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.io.OutputStream

class IncidentDetailsActivity : AppCompatActivity() {

    private var incidentId: Int = -1
    private var imageUrl: String? = null
    private var isAdmin: Boolean = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_incident_details)

        val token = SessionManager.getToken(this)
        val jwt = token?.let { JWT(it) }
        isAdmin = jwt?.getClaim("is_superuser")?.asBoolean() ?: false

        incidentId = intent.getIntExtra("INCIDENT_ID", -1)
        if (incidentId == -1) {
            Toast.makeText(this, "ID de incidente no válido", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        configureButtons()
        loadIncidentDetails()
    }

    private fun configureButtons() {
        val btnEdit = findViewById<Button>(R.id.btnEdit)
        val btnSoftDelete = findViewById<Button>(R.id.btnSoftDeleteIncident)
        val btnDeleteIncident = findViewById<Button>(R.id.btnDeleteIncident)

        btnEdit.setOnClickListener {
            showEditOptionsDialog()
        }

        btnSoftDelete.visibility = if (isAdmin) View.VISIBLE else View.GONE
        btnDeleteIncident.visibility = if (isAdmin) View.VISIBLE else View.GONE

        btnSoftDelete.setOnClickListener {
            showSoftDeleteConfirmationDialog()
        }

        btnDeleteIncident.setOnClickListener {
            showDeleteConfirmationDialog()
        }

        findViewById<Button>(R.id.btnBack).setOnClickListener {
            finish()
        }
    }

    private fun showEditOptionsDialog() {
        val options = mutableListOf("Cambiar imagen")

        if (isAdmin) {
            options.add("Cambiar estado y comentario")
        }

        AlertDialog.Builder(this)
            .setTitle("Opciones de edición")
            .setItems(options.toTypedArray()) { _, which ->
                when (which) {
                    0 -> openImageEditor()
                    1 -> if (isAdmin) openStatusEditor()
                }
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun openImageEditor() {
        val intent = Intent(this, EditIncidentImageActivity::class.java)
        intent.putExtra("INCIDENT_ID", incidentId)
        startActivityForResult(intent, EDIT_IMAGE_REQUEST_CODE)
    }

    private fun openStatusEditor() {
        val intent = Intent(this, EditIncidentStatusActivity::class.java)
        intent.putExtra("INCIDENT_ID", incidentId)
        startActivityForResult(intent, EDIT_STATUS_REQUEST_CODE)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (resultCode == RESULT_OK) {
            loadIncidentDetails()
        }
    }

    private fun loadIncidentDetails() {
        RetrofitClient.instance.getIncidentDetails(incidentId).enqueue(object : Callback<IncidentDetailResponse> {
            override fun onResponse(call: Call<IncidentDetailResponse>, response: Response<IncidentDetailResponse>) {
                if (response.isSuccessful && response.body() != null) {
                    val incident = response.body()!!.data
                    displayIncidentDetails(incident)
                } else {
                    Toast.makeText(this@IncidentDetailsActivity, "Error al cargar detalles del incidente", Toast.LENGTH_SHORT).show()
                }
            }

            override fun onFailure(call: Call<IncidentDetailResponse>, t: Throwable) {
                Toast.makeText(this@IncidentDetailsActivity, "Error de conexión: ${t.message}", Toast.LENGTH_SHORT).show()
            }
        })
    }

    private fun displayIncidentDetails(incident: Incident) {
        findViewById<TextView>(R.id.tvIncidentType).text = incident.incident_type
        findViewById<TextView>(R.id.tvDescription).text = incident.description
        findViewById<TextView>(R.id.tvDate).text = incident.date
        findViewById<TextView>(R.id.tvStatus).text = incident.status_display
        findViewById<TextView>(R.id.tvCreatedBy).text = incident.created_by_name
        findViewById<TextView>(R.id.tvCreatedAt).text = incident.created_at
        findViewById<TextView>(R.id.tvUpdatedAt).text = incident.updated_at

        val commentTextView = findViewById<TextView>(R.id.tvComment)
        commentTextView.text = incident.comment ?: "Sin comentarios"
        commentTextView.visibility = if (incident.comment.isNullOrEmpty()) View.GONE else View.VISIBLE

        val ivIncident = findViewById<ImageView>(R.id.ivIncidentImage)

        if (!incident.image_url.isNullOrEmpty()) {
            imageUrl = incident.image_url
            Glide.with(this)
                .load(incident.image_url)
                .into(ivIncident)

            ivIncident.setOnClickListener {
                showImageDialog(incident.image_url)
            }
        } else {
            ivIncident.setImageResource(R.drawable.ic_placeholder)
        }

        updateStatusColor(incident.status)
    }

    private fun updateStatusColor(status: String) {
        val tvStatus = findViewById<TextView>(R.id.tvStatus)
        val colorRes = when (status.lowercase()) {
            "activo" -> R.color.green_500
            "pendiente" -> R.color.orange_500
            "resuelto" -> R.color.blue_500
            "cancelado" -> R.color.red_500
            else -> R.color.gray_500
        }
        tvStatus.setBackgroundColor(ContextCompat.getColor(this, colorRes))
    }

    private fun showImageDialog(imageUrl: String) {
        Glide.with(this)
            .asBitmap()
            .load(imageUrl)
            .into(object : CustomTarget<Bitmap>() {
                override fun onResourceReady(bitmap: Bitmap, transition: Transition<in Bitmap>?) {
                    val imageView = ImageView(this@IncidentDetailsActivity).apply {
                        setImageBitmap(bitmap)
                        scaleType = ImageView.ScaleType.FIT_CENTER
                        adjustViewBounds = true
                    }

                    AlertDialog.Builder(this@IncidentDetailsActivity)
                        .setView(imageView)
                        .setPositiveButton("Descargar") { _, _ ->
                            saveBitmapToGallery(bitmap)
                        }
                        .setNegativeButton("Cerrar", null)
                        .create()
                        .show()
                }

                override fun onLoadCleared(placeholder: Drawable?) {}
            })
    }

    private fun saveBitmapToGallery(bitmap: Bitmap) {
        val filename = "incident_${System.currentTimeMillis()}.jpg"
        val contentValues = ContentValues().apply {
            put(MediaStore.Images.Media.DISPLAY_NAME, filename)
            put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
            put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES)
            put(MediaStore.Images.Media.IS_PENDING, 1)
        }

        val uri: Uri? = contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, contentValues)

        uri?.let {
            val outputStream: OutputStream? = contentResolver.openOutputStream(it)
            outputStream.use { stream ->
                if (stream != null) {
                    bitmap.compress(Bitmap.CompressFormat.JPEG, 100, stream)
                }
            }
            contentValues.clear()
            contentValues.put(MediaStore.Images.Media.IS_PENDING, 0)
            contentResolver.update(uri, contentValues, null, null)
            Toast.makeText(this, "Imagen guardada en galería", Toast.LENGTH_SHORT).show()
        } ?: run {
            Toast.makeText(this, "No se pudo guardar la imagen", Toast.LENGTH_SHORT).show()
        }
    }

    private fun showDeleteConfirmationDialog() {
        AlertDialog.Builder(this)
            .setTitle("Confirmar eliminación")
            .setMessage("¿Estás seguro de que deseas eliminar este incidente esto lo hará desaparecer totalmente?")
            .setPositiveButton("Eliminar") { dialog, _ ->
                deleteIncident()
                dialog.dismiss()
            }
            .setNegativeButton("Cancelar") { dialog, _ ->
                dialog.dismiss()
            }
            .create()
            .show()
    }

    private fun showSoftDeleteConfirmationDialog() {
        AlertDialog.Builder(this)
            .setTitle("Ocultar incidente")
            .setMessage("¿Estás seguro de que deseas ocultar este incidente? Podrás recuperarlo más tarde.")
            .setPositiveButton("Ocultar") { dialog, _ ->
                softDeleteIncident(false)
                dialog.dismiss()
            }
            .setNegativeButton("Cancelar") { dialog, _ ->
                dialog.dismiss()
            }
            .create()
            .show()
    }
    //Para después
    private fun showReactivateConfirmationDialog() {
        AlertDialog.Builder(this)
            .setTitle("Mostrar incidente")
            .setMessage("¿Deseas volver a mostrar este incidente?")
            .setPositiveButton("Mostrar") { dialog, _ ->
                softDeleteIncident(true)
                dialog.dismiss()
            }
            .setNegativeButton("Cancelar") { dialog, _ ->
                dialog.dismiss()
            }
            .create()
            .show()
    }

    private fun softDeleteIncident(active: Boolean) {
        val request = SoftDeleteRequest(active = active)

        RetrofitClient.instance.softDeleteIncident(incidentId, request)
            .enqueue(object : Callback<Void> {
                override fun onResponse(call: Call<Void>, response: Response<Void>) {
                    if (response.isSuccessful) {
                        val message = if (active) {
                            "Incidente visible nuevamente"
                        } else {
                            "Incidente ocultado correctamente"
                        }
                        Toast.makeText(
                            this@IncidentDetailsActivity,
                            message,
                            Toast.LENGTH_SHORT
                        ).show()
                        setResult(RESULT_OK)
                        finish()
                    } else {
                        Toast.makeText(
                            this@IncidentDetailsActivity,
                            "Error: ${response.message()}",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                }

                override fun onFailure(call: Call<Void>, t: Throwable) {
                    Toast.makeText(
                        this@IncidentDetailsActivity,
                        "Error de conexión: ${t.message}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            })
    }
    private fun deleteIncident() {
        RetrofitClient.instance.deleteIncident(incidentId).enqueue(object : Callback<Void> {
            override fun onResponse(call: Call<Void>, response: Response<Void>) {
                if (response.isSuccessful) {
                    Toast.makeText(this@IncidentDetailsActivity, "Incidente eliminado exitosamente", Toast.LENGTH_SHORT).show()
                    setResult(RESULT_OK)
                    finish()
                } else {
                    Toast.makeText(this@IncidentDetailsActivity, "Error al eliminar incidente: ${response.message()}", Toast.LENGTH_SHORT).show()
                }
            }

            override fun onFailure(call: Call<Void>, t: Throwable) {
                Toast.makeText(this@IncidentDetailsActivity, "Error de conexión: ${t.message}", Toast.LENGTH_SHORT).show()
            }
        })
    }

    companion object {
        private const val EDIT_IMAGE_REQUEST_CODE = 1001
        private const val EDIT_STATUS_REQUEST_CODE = 1002
    }
}