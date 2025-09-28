package com.example.expense_tracker

import android.content.Context
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken

class DataStorage(private val context: Context) {

    private val gson = Gson()
    private val expensesKey = "expenses"
    private val budgetsKey = "budgets"

    fun saveExpenses(expenses: List<Expense>) {
        val json = gson.toJson(expenses)
        context.getSharedPreferences("expenses_prefs", Context.MODE_PRIVATE)
            .edit()
            .putString(expensesKey, json)
            .apply()
    }

    fun loadExpenses(): List<Expense> {
        val json = context.getSharedPreferences("expenses_prefs", Context.MODE_PRIVATE)
            .getString(expensesKey, null)

        return if (json != null) {
            val typeToken = object : TypeToken<List<Expense>>() {}.type
            gson.fromJson(json, typeToken)
        } else {
            emptyList()
        }
    }

    fun saveBudgets(budgets: List<Budget>) {
        val json = gson.toJson(budgets)
        context.getSharedPreferences("budgets_prefs", Context.MODE_PRIVATE)
            .edit()
            .putString(budgetsKey, json)
            .apply()
    }

    fun loadBudgets(): List<Budget> {
        val json = context.getSharedPreferences("budgets_prefs", Context.MODE_PRIVATE)
            .getString(budgetsKey, null)

        return if (json != null) {
            val typeToken = object : TypeToken<List<Budget>>() {}.type
            gson.fromJson(json, typeToken)
        } else {
            emptyList()
        }
    }
}