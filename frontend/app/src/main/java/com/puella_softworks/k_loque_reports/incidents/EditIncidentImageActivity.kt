package com.puella_softworks.k_loque_reports.incidents

import android.app.Activity
import android.content.Intent
import android.graphics.Bitmap
import android.net.Uri
import android.os.Bundle
import android.provider.MediaStore
import android.widget.Button
import android.widget.ImageView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.puella_softworks.k_loque_reports.R
import com.puella_softworks.k_loque_reports.classes.RetrofitClient
import com.puella_softworks.k_loque_reports.models.IncidentResponse
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.io.File
import java.io.FileOutputStream

class EditIncidentImageActivity : AppCompatActivity() {

    private lateinit var ivIncidentImage: ImageView
    private var imageUri: Uri? = null
    private var incidentId: Int = -1
    private var cameraBitmap: Bitmap? = null

    companion object {
        private const val PICK_IMAGE_REQUEST = 1
        private const val REQUEST_IMAGE_CAPTURE = 2
        private const val TEMP_IMAGE_NAME = "temp_incident_image.jpg"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_edit_incident_image)

        incidentId = intent.getIntExtra("INCIDENT_ID", -1)
        if (incidentId == -1) {
            Toast.makeText(this, "ID de incidente no válido", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        ivIncidentImage = findViewById(R.id.ivIncidentImage)
        val btnSelectImage = findViewById<Button>(R.id.btnSelectImage)
        val btnSaveImage = findViewById<Button>(R.id.btnSaveImage)
        val btnCancel = findViewById<Button>(R.id.btnCancel)

        btnSelectImage.setOnClickListener {
            showImageSourceDialog()
        }

        btnSaveImage.setOnClickListener {
            if (imageUri != null || cameraBitmap != null) {
                uploadImage()
            } else {
                Toast.makeText(this, "Selecciona o toma una imagen primero", Toast.LENGTH_SHORT).show()
            }
        }

        btnCancel.setOnClickListener {
            finish()
        }
    }

    private fun showImageSourceDialog() {
        val options = arrayOf("Seleccionar de la galería", "Tomar foto con cámara")

        AlertDialog.Builder(this)
            .setTitle("Seleccionar imagen")
            .setItems(options) { _, which ->
                when (which) {
                    0 -> selectImageFromGallery()
                    1 -> takePhotoWithCamera()
                }
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun selectImageFromGallery() {
        val intent = Intent(Intent.ACTION_PICK, MediaStore.Images.Media.EXTERNAL_CONTENT_URI)
        startActivityForResult(intent, PICK_IMAGE_REQUEST)
    }

    private fun takePhotoWithCamera() {
        Intent(MediaStore.ACTION_IMAGE_CAPTURE).also { takePictureIntent ->
            takePictureIntent.resolveActivity(packageManager)?.also {
                startActivityForResult(takePictureIntent, REQUEST_IMAGE_CAPTURE)
            }
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)

        if (resultCode != Activity.RESULT_OK) return

        when (requestCode) {
            PICK_IMAGE_REQUEST -> {
                data?.data?.let { uri ->
                    imageUri = uri
                    cameraBitmap = null
                    ivIncidentImage.setImageURI(uri)
                }
            }
            REQUEST_IMAGE_CAPTURE -> {
                val imageBitmap = data?.extras?.get("data") as? Bitmap
                imageBitmap?.let {
                    cameraBitmap = it
                    imageUri = null
                    ivIncidentImage.setImageBitmap(it)
                }
            }
        }
    }

    private fun uploadImage() {
        try {
            val imagePart = if (cameraBitmap != null) {
                val file = createTempImageFile(cameraBitmap!!)
                val requestFile = RequestBody.create("image/*".toMediaTypeOrNull(), file)
                MultipartBody.Part.createFormData("incident_image", file.name, requestFile)
            } else if (imageUri != null) {
                val inputStream = contentResolver.openInputStream(imageUri!!)
                val bytes = inputStream?.readBytes()
                inputStream?.close()

                if (bytes != null) {
                    val requestFile = RequestBody.create("image/*".toMediaTypeOrNull(), bytes)
                    MultipartBody.Part.createFormData("incident_image", "incident_updated.jpg", requestFile)
                } else {
                    throw Exception("No se pudo leer la imagen")
                }
            } else {
                throw Exception("No hay imagen seleccionada")
            }

            val incidentIdPart = RequestBody.create("text/plain".toMediaTypeOrNull(), incidentId.toString())

            RetrofitClient.instance.editIncidentImage(incidentIdPart, imagePart)
                .enqueue(object : Callback<IncidentResponse> {
                    override fun onResponse(
                        call: Call<IncidentResponse>,
                        response: Response<IncidentResponse>
                    ) {
                        if (response.isSuccessful) {
                            Toast.makeText(
                                this@EditIncidentImageActivity,
                                "Imagen actualizada correctamente",
                                Toast.LENGTH_SHORT
                            ).show()
                            setResult(RESULT_OK)
                            finish()
                        } else {
                            Toast.makeText(
                                this@EditIncidentImageActivity,
                                "Error al actualizar la imagen: ${response.message()}",
                                Toast.LENGTH_SHORT
                            ).show()
                        }
                    }

                    override fun onFailure(call: Call<IncidentResponse>, t: Throwable) {
                        Toast.makeText(
                            this@EditIncidentImageActivity,
                            "Error de conexión: ${t.message}",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                })

        } catch (e: Exception) {
            Toast.makeText(this, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            e.printStackTrace()
        }
    }

    private fun createTempImageFile(bitmap: Bitmap): File {
        val file = File(cacheDir, TEMP_IMAGE_NAME)
        val outputStream = FileOutputStream(file)
        bitmap.compress(Bitmap.CompressFormat.JPEG, 90, outputStream)
        outputStream.flush()
        outputStream.close()
        return file
    }

    override fun onDestroy() {
        super.onDestroy()
        File(cacheDir, TEMP_IMAGE_NAME).takeIf { it.exists() }?.delete()
    }
}