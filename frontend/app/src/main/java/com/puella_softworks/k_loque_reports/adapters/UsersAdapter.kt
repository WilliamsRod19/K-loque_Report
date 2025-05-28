package com.puella_softworks.k_loque_reports.adapters

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.puella_softworks.k_loque_reports.R
import com.puella_softworks.k_loque_reports.models.UserData

class UsersAdapter(private var users: List<UserData>) : RecyclerView.Adapter<UsersAdapter.UserViewHolder>() {

    private var filteredList: List<UserData> = users
    var onItemClick: ((UserData) -> Unit)? = null

    inner class UserViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val tvUsername: TextView = itemView.findViewById(R.id.tvUsername)
        val tvFullName: TextView = itemView.findViewById(R.id.tvFullName)
        val tvEmail: TextView = itemView.findViewById(R.id.tvEmail)
        val tvIsAdmin: TextView = itemView.findViewById(R.id.tvIsAdmin)
        val ivIsAdmin: ImageView = itemView.findViewById(R.id.ivIsAdmin)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): UserViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_user, parent, false)
        return UserViewHolder(view)
    }

    override fun onBindViewHolder(holder: UserViewHolder, position: Int) {
        val user = filteredList[position]
        holder.tvUsername.text = "@${user.username}"
        holder.tvFullName.text = "${user.first_name} ${user.last_name}"
        holder.tvEmail.text = user.email
        holder.tvIsAdmin.text = if (user.is_admin) "Administrador" else "Usuario normal"
        holder.ivIsAdmin.setImageResource( if (user.is_admin) R.drawable.ic_admin else R.drawable.ic_user)

        holder.itemView.setOnClickListener {
            onItemClick?.invoke(user)
        }
    }

    override fun getItemCount(): Int = filteredList.size

    fun filter(query: String) {
        filteredList = if (query.isEmpty()) {
            users
        } else {
            users.filter {
                it.username.contains(query, true) ||
                        it.first_name.contains(query, true) ||
                        it.last_name.contains(query, true) ||
                        it.email.contains(query, true)
            }
        }
        notifyDataSetChanged()
    }

    fun updateData(newUsers: List<UserData>) {
        users = newUsers
        filteredList = newUsers
        notifyDataSetChanged()
    }
}