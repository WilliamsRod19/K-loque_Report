package com.puella_softworks.k_loque_reports.incidents

import android.app.Activity
import android.app.AlertDialog
import android.app.DatePickerDialog
import android.content.Intent
import android.graphics.Bitmap
import android.net.Uri
import android.os.Bundle
import android.provider.MediaStore
import android.widget.*
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
import java.io.ByteArrayOutputStream
import java.text.SimpleDateFormat
import java.util.*

class CreateIncidentActivity : AppCompatActivity() {

    private lateinit var spinnerIncidentType: Spinner
    private lateinit var etDescription: EditText
    private lateinit var etDate: EditText
    private lateinit var ivIncidentImage: ImageView
    private lateinit var btnSelectImage: Button
    private var selectedImageUri: Uri? = null

    companion object {
        private const val PICK_IMAGE_REQUEST = 1
        private const val CAMERA_REQUEST = 2
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_create_incident)

        initViews()
        setupSpinner()
        setupDatePicker()
        setupButtons()
    }

    private fun initViews() {
        spinnerIncidentType = findViewById(R.id.spinnerIncidentType)
        etDescription = findViewById(R.id.etDescription)
        etDate = findViewById(R.id.etDate)
        ivIncidentImage = findViewById(R.id.ivIncidentImage)
        btnSelectImage = findViewById(R.id.btnSelectImage)
    }

    private fun setupSpinner() {
        val incidentTypes = arrayOf("SOLICITUD", "PROBLEMA", "SOPORTE", "SUGERENCIA")

        val adapter = ArrayAdapter(
            this,
            R.layout.item_spinner,
            incidentTypes
        ).also {
            it.setDropDownViewResource(R.layout.item_spinner_dropdown)
        }

        spinnerIncidentType.adapter = adapter
    }

    private fun setupDatePicker() {
        val calendar = Calendar.getInstance()
        val dateFormat = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())

        val dateListener = DatePickerDialog.OnDateSetListener { _, year, month, day ->
            calendar.set(Calendar.YEAR, year)
            calendar.set(Calendar.MONTH, month)
            calendar.set(Calendar.DAY_OF_MONTH, day)
            etDate.setText(dateFormat.format(calendar.time))
        }

        etDate.setOnClickListener {
            val dialog = DatePickerDialog(
                this,
                dateListener,
                calendar.get(Calendar.YEAR),
                calendar.get(Calendar.MONTH),
                calendar.get(Calendar.DAY_OF_MONTH)
            )
            dialog.datePicker.maxDate = System.currentTimeMillis()
            dialog.show()
        }
    }

    private fun setupButtons() {
        btnSelectImage.setOnClickListener {
            showImageSelectionDialog()
        }

        findViewById<Button>(R.id.btnCreateIncident).setOnClickListener {
            createIncident()
        }

        findViewById<Button>(R.id.btnCancel).setOnClickListener {
            finish()
        }
    }

    private fun showImageSelectionDialog() {
        val options = arrayOf("Tomar foto", "Seleccionar de galería", "Cancelar")
        AlertDialog.Builder(this)
            .setTitle("Seleccionar imagen")
            .setItems(options) { _, which ->
                when (which) {
                    0 -> openCamera()
                    1 -> openGallery()
                    2 -> {}
                }
            }
            .show()
    }

    private fun openCamera() {
        val intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
        startActivityForResult(intent, CAMERA_REQUEST)
    }

    private fun openGallery() {
        val intent = Intent(Intent.ACTION_PICK, MediaStore.Images.Media.EXTERNAL_CONTENT_URI)
        startActivityForResult(intent, PICK_IMAGE_REQUEST)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (resultCode == Activity.RESULT_OK) {
            when (requestCode) {
                PICK_IMAGE_REQUEST -> {
                    selectedImageUri = data?.data
                    ivIncidentImage.setImageURI(selectedImageUri)
                }
                CAMERA_REQUEST -> {
                    val imageBitmap = data?.extras?.get("data") as? Bitmap
                    imageBitmap?.let {
                        ivIncidentImage.setImageBitmap(it)
                        selectedImageUri = getImageUriFromBitmap(it)
                    }
                }
            }
        }
    }

    private fun getImageUriFromBitmap(bitmap: Bitmap): Uri {
        val bytes = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.JPEG, 100, bytes)
        val path = MediaStore.Images.Media.insertImage(contentResolver, bitmap, "Title", null)
        return Uri.parse(path)
    }

    private fun createIncident() {
        try {


        val incidentType = spinnerIncidentType.selectedItem.toString()
        val description = etDescription.text.toString().trim()
        val date = etDate.text.toString().trim()

        if (description.isEmpty() || date.isEmpty()) {
            Toast.makeText(this, "Por favor complete todos los campos requeridos", Toast.LENGTH_SHORT).show()
            return
        }

        val incidentTypePart = RequestBody.create("text/plain".toMediaTypeOrNull(), incidentType)
        val descriptionPart = RequestBody.create("text/plain".toMediaTypeOrNull(), description)
        val datePart = RequestBody.create("text/plain".toMediaTypeOrNull(), date)

        var imagePart: MultipartBody.Part? = null
        selectedImageUri?.let { uri ->
            val inputStream = contentResolver.openInputStream(uri)
            val bytes = inputStream?.readBytes()

            bytes?.let {
                val requestFile = RequestBody.create("image/*".toMediaTypeOrNull(), it)
                imagePart = MultipartBody.Part.createFormData("image", "incident.jpg", requestFile)
            }
        }

        RetrofitClient.instance.createIncident(
            incidentTypePart,
            descriptionPart,
            datePart,
            imagePart
        ).enqueue(object : Callback<IncidentResponse> {
            override fun onResponse(call: Call<IncidentResponse>, response: Response<IncidentResponse>) {
                if (response.isSuccessful) {
                    Toast.makeText(this@CreateIncidentActivity, "Incidente creado exitosamente", Toast.LENGTH_SHORT).show()
                    setResult(RESULT_OK)
                    finish()
                } else {
                    Toast.makeText(this@CreateIncidentActivity, "Error al crear incidente: ${response.message()}", Toast.LENGTH_SHORT).show()
                }
            }

            override fun onFailure(call: Call<IncidentResponse>, t: Throwable) {
                Toast.makeText(this@CreateIncidentActivity, "Error de conexión: ${t.message}", Toast.LENGTH_SHORT).show()
                println("Error en onFailure: ${t.message}")
                print("Error en onFailure: ${t.message}")
            }
        })
        } catch (e: Exception) {println("Error en onCreate: ${e.message}")}
    }


}