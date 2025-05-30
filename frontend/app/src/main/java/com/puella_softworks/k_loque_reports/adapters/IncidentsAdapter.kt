package com.puella_softworks.k_loque_reports.adapters

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.RecyclerView
import com.puella_softworks.k_loque_reports.R
import com.puella_softworks.k_loque_reports.models.Incident

class IncidentsAdapter(private var incidents: List<Incident>) : RecyclerView.Adapter<IncidentsAdapter.IncidentViewHolder>() {

    private var filteredList: List<Incident> = incidents
    var onItemClick: ((Incident) -> Unit)? = null


    inner class IncidentViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val tvType: TextView = itemView.findViewById(R.id.tvType)
        val tvStatus: TextView = itemView.findViewById(R.id.tvStatus)
        val tvDescription: TextView = itemView.findViewById(R.id.tvDescription)
        val tvDate: TextView = itemView.findViewById(R.id.tvDate)
        val tvCreatedBy: TextView = itemView.findViewById(R.id.tvCreatedBy)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): IncidentViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_incident, parent, false)
        return IncidentViewHolder(view)
    }

    override fun onBindViewHolder(holder: IncidentViewHolder, position: Int) {
        val incident = filteredList[position]

        try {
            holder.tvType.text = incident.incident_type
            holder.tvStatus.text = incident.status_display
            holder.tvDescription.text = incident.description
            holder.tvDate.text = incident.date
            holder.tvCreatedBy.text = "Por: ${incident.created_by_name}"

            val statusColor = when (incident.status) {
                "activo" -> R.color.green_500
                "pendiente" -> R.color.orange_500
                "resuelto" -> R.color.blue_500
                "cancelado" -> R.color.red_500
                else -> R.color.gray_500
            }

            holder.tvStatus.background = ContextCompat.getDrawable(holder.itemView.context, R.drawable.bg_status_tag)
            holder.tvStatus.setBackgroundColor(
                ContextCompat.getColor(holder.itemView.context, statusColor)
            )

            holder.itemView.setOnClickListener {
                onItemClick?.invoke(incident)
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    override fun getItemCount(): Int = filteredList.size

    fun filter(query: String) {
        filteredList = if (query.isEmpty()) {
            incidents
        } else {
            incidents.filter {
                it.incident_type.contains(query, true) ||
                        it.description.contains(query, true) ||
                        it.created_by_name.contains(query, true) ||
                        it.status_display.contains(query, true)
            }
        }
        notifyDataSetChanged()
    }

    fun updateData(newIncidents: List<Incident>) {
        incidents = newIncidents
        filteredList = newIncidents
        notifyDataSetChanged()
    }


}