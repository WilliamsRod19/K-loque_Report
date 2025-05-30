package com.puella_softworks.k_loque_reports.services

import com.puella_softworks.k_loque_reports.classes.ApiResponse
import com.puella_softworks.k_loque_reports.models.CreateUserRequest
import com.puella_softworks.k_loque_reports.models.IncidentDetailResponse
import com.puella_softworks.k_loque_reports.models.IncidentResponse
import com.puella_softworks.k_loque_reports.models.SoftDeleteRequest
import com.puella_softworks.k_loque_reports.models.UpdateIncidentRequest
import com.puella_softworks.k_loque_reports.models.UpdateUserRequest
import com.puella_softworks.k_loque_reports.models.UserDetailResponse
import com.puella_softworks.k_loque_reports.models.UserResponse
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Part
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

    //Métodos para incidentes
    @GET("api/v1/incident")
    fun getIncidents(): Call<IncidentResponse>

    @GET("api/v1/incident/{id}")
    fun getIncidentDetails(@Path("id") incidentId: Int): Call<IncidentDetailResponse>

    @Multipart
    @POST("api/v1/incident")
    fun createIncident(
        @Part("incident_type") incidentType: RequestBody,
        @Part("description") description: RequestBody,
        @Part("date") date: RequestBody,
        @Part image: MultipartBody.Part?
    ): Call<IncidentResponse>

    @Multipart
    @POST("api/v1/incident/edit-image")
    fun editIncidentImage(
        @Part("id") incidentId: RequestBody,
        @Part incident_image: MultipartBody.Part
    ): Call<IncidentResponse>

    @PUT("api/v1/incident/{id}")
    fun updateIncident(
        @Path("id") incidentId: Int,
        @Body updateRequest: UpdateIncidentRequest
    ): Call<IncidentDetailResponse>

    @DELETE("api/v1/incident/{id}")
    fun deleteIncident(@Path("id") incidentId: Int): Call<Void>

    @PATCH("api/v1/incident/sdelete/{id}")
    fun softDeleteIncident(
        @Path("id") incidentId: Int,
        @Body request: SoftDeleteRequest
    ): Call<Void>
}

data class LoginRequest(
    val email_or_username: String,
    val password: String
)