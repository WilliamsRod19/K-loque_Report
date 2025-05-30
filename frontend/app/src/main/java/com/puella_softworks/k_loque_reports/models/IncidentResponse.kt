package com.puella_softworks.k_loque_reports.models

data class IncidentResponse(
    val status: String,
    val data: List<Incident>
)

data class Incident(
    val id: Int,
    val incident_type: String,
    val description: String,
    val date: String,
    val image_url: String?,
    val comment: String?,
    val status: String,
    val status_display: String,
    val active: Boolean,
    val created_by_id: Int,
    val created_by_name: String,
    val created_at: String,
    val modified_by_id: Int,
    val modified_by_name: String,
    val updated_at: String
)
data class IncidentDetailResponse(
    val status: String,
    val data: Incident
)

data class UpdateIncidentRequest(
    val comment: String,
    val status: String
)

data class SoftDeleteRequest(
    val active: Boolean
)
