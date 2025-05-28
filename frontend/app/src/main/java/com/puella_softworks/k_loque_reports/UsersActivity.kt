package com.puella_softworks.k_loque_reports

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.SearchView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.floatingactionbutton.FloatingActionButton
import com.google.android.material.snackbar.Snackbar
import com.puella_softworks.k_loque_reports.adapters.UsersAdapter
import com.puella_softworks.k_loque_reports.classes.RetrofitClient
import com.puella_softworks.k_loque_reports.models.UserResponse
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class UsersActivity : AppCompatActivity() {

    private lateinit var adapter: UsersAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_users)

        val addUser = findViewById<FloatingActionButton>(R.id.addUser)
        addUser.setOnClickListener {
            startActivity(Intent(this, CreateUserActivity::class.java))
        }

        val rvUsers = findViewById<RecyclerView>(R.id.rvUsers)
        adapter = UsersAdapter(emptyList())
        rvUsers.adapter = adapter

        val searchView = findViewById<SearchView>(R.id.searchView)
        searchView.setOnQueryTextListener(object : SearchView.OnQueryTextListener {
            override fun onQueryTextSubmit(query: String?): Boolean = false

            override fun onQueryTextChange(newText: String?): Boolean {
                adapter.filter(newText ?: "")
                return true
            }
        })

        adapter.onItemClick = { user ->
            val intent = Intent(this, UserDetailsActivity::class.java)
            intent.putExtra("USER_ID", user.id)
            startActivityForResult(intent, 1)
        }

        findViewById<Button>(R.id.btnBack).setOnClickListener {
            finish()
        }
        loadUsers()
    }

    private fun loadUsers() {
        RetrofitClient.instance.getUsers().enqueue(object : Callback<UserResponse> {
            override fun onResponse(call: Call<UserResponse>, response: Response<UserResponse>) {
                if (response.isSuccessful) {
                    response.body()?.data?.let { users ->
                        adapter.updateData(users)
                    }
                }
            }

            override fun onFailure(call: Call<UserResponse>, t: Throwable) {
            }
        })
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (resultCode == RESULT_OK) {
            loadUsers()
        }
    }
}