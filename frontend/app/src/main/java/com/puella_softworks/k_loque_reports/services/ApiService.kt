package com.puella_softworks.k_loque_reports.services

import com.puella_softworks.k_loque_reports.classes.ApiResponse
import com.puella_softworks.k_loque_reports.models.CreateUserRequest
import com.puella_softworks.k_loque_reports.models.UpdateUserRequest
import com.puella_softworks.k_loque_reports.models.UserDetailResponse
import com.puella_softworks.k_loque_reports.models.UserResponse
import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path

interface ApiService {
    //Métodos para crud de usuario
    @POST("api/v1/user-control/login")
    fun login(@Body loginRequest: LoginRequest): Call<ApiResponse>

    @GET("api/v1/user-control")
    fun getUsers(): Call<UserResponse>

    @GET("api/v1/user-control/{id}")
    fun getUserDetails(@Path("id") userId: Int): Call<UserDetailResponse>

    @POST("api/v1/user-control")
    fun createUser(@Body createUserRequest: CreateUserRequest): Call<UserResponse>

    @PUT("api/v1/user-control/{id}")
    fun updateUser(@Path("id") userId: Int, @Body updateUserRequest: UpdateUserRequest): Call<UserDetailResponse>

    @DELETE("api/v1/user-control/{id}")
    fun deleteUser(@Path("id") userId: Int): Call<Void>
}

data class LoginRequest(
    val email_or_username: String,
    val password: String
)