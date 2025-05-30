package com.puella_softworks.k_loque_reports.models

data class UserResponse(
    val data: List<UserData>
)

data class UserData(
    val id: Int,
    val username: String,
    val first_name: String,
    val last_name: String,
    val email: String,
    val is_active: Boolean,
    val is_admin: Boolean,
    val last_login: String,
    val date_joined: String
)

data class UserDetailResponse(
    val data: UserData
)

data class CreateUserRequest(
    val first_name: String,
    val last_name: String,
    val username: String,
    val email: String,
    val password: String
)

data class UpdateUserRequest(
    val first_name: String,
    val last_name: String,
    val username: String,
    val email: String,
    val password: String?,
    val is_admin: Boolean,
    val is_active: Boolean
)

data class DeleteUserRequest(
    val id: Int
)
