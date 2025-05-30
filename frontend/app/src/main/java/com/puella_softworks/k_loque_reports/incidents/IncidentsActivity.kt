package com.puella_softworks.k_loque_reports.incidents

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.SearchView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.floatingactionbutton.FloatingActionButton
import com.puella_softworks.k_loque_reports.LoginActivity
import com.puella_softworks.k_loque_reports.R
import com.puella_softworks.k_loque_reports.adapters.IncidentsAdapter
import com.puella_softworks.k_loque_reports.classes.RetrofitClient
import com.puella_softworks.k_loque_reports.classes.SessionManager
import com.puella_softworks.k_loque_reports.models.IncidentResponse
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class IncidentsActivity : AppCompatActivity() {

    private lateinit var adapter: IncidentsAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_incidents)

        if (SessionManager.getToken(this) == null) {
            redirectToLogin()
            return
        }

        try {
            val rvIncidents = findViewById<RecyclerView>(R.id.rvIncidents).apply {
                layoutManager = LinearLayoutManager(this@IncidentsActivity)
                setHasFixedSize(true)
                adapter = IncidentsAdapter(emptyList()).also {
                    this@IncidentsActivity.adapter = it
                }
            }

            findViewById<SearchView>(R.id.searchView).setOnQueryTextListener(
                object : SearchView.OnQueryTextListener {
                    override fun onQueryTextSubmit(query: String?) = false
                    override fun onQueryTextChange(newText: String?): Boolean {
                        adapter.filter(newText ?: "")
                        return true
                    }
                }
            )

            val addIncident = findViewById<FloatingActionButton>(R.id.addIncident)
            addIncident.setOnClickListener {
                startActivity(Intent(this, CreateIncidentActivity::class.java))
            }

            findViewById<Button>(R.id.btnBack).setOnClickListener { finish() }


            loadIncidents()
        } catch (e: Exception) {
            Log.e("IncidentsActivity", "Error en onCreate", e)
            Toast.makeText(this, "Error al inicializar la actividad", Toast.LENGTH_SHORT).show()
            println("Error en onCreate: ${e.message}")
            finish()
        }

        adapter.onItemClick = { incident ->
            val intent = Intent(this, IncidentDetailsActivity::class.java)
            intent.putExtra("INCIDENT_ID", incident.id)
            startActivity(intent)
        }

    }

    private fun loadIncidents() {
        RetrofitClient.instance.getIncidents().enqueue(object : Callback<IncidentResponse> {
            override fun onResponse(call: Call<IncidentResponse>, response: Response<IncidentResponse>) {
                if (response.isSuccessful && response.body() != null) {
                    adapter.updateData(response.body()!!.data)
                } else {
                    Toast.makeText(this@IncidentsActivity,
                        "Error al cargar incidentes: ${response.message()}",
                        Toast.LENGTH_SHORT).show()
                }
            }
            override fun onFailure(call: Call<IncidentResponse>, t: Throwable) {
                Toast.makeText(this@IncidentsActivity,
                    "Error de conexión: ${t.message}",
                    Toast.LENGTH_SHORT).show()
                Log.e("IncidentsActivity", "API Error", t)
            }
        })
    }
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == 1 && resultCode == RESULT_OK) {
        }
    }
    private fun redirectToLogin() {
        startActivity(Intent(this, LoginActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        })
        finish()
    }
}