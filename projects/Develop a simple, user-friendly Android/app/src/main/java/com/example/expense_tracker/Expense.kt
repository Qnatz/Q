package com.example.expense_tracker

data class Expense(
    val id: Int,
    val date: String,
    val category: String,
    val amount: Double,
    val description: String
)