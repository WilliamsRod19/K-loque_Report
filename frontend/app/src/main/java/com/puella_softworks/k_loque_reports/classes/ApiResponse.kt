package com.puella_softworks.k_loque_reports.classes

data class ApiResponse(
    val status: String,
    val message: String,
    val token: String,
    val user: User
)

data class User(
    val id: Int,
    val username: String,
    val email: String,
    val first_name: String
)