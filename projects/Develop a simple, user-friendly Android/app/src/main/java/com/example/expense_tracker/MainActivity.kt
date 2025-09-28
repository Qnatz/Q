package com.example.expense_tracker

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView

class MainActivity : AppCompatActivity() {

    private lateinit var expenseAdapter: ExpenseAdapter
    private lateinit var expenseRecyclerView: RecyclerView
    private lateinit var totalExpenseTextView: TextView
    private lateinit var budgetTextView: TextView
    private lateinit var addExpenseButton: Button
    private lateinit var expenseDescriptionEditText: EditText
    private lateinit var expenseAmountEditText: EditText
    private lateinit var expenseCategoryEditText: EditText
    private lateinit var setBudgetButton: Button
    private lateinit var budgetAmountEditText: EditText
    private lateinit var viewReportButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Initialize UI elements
        expenseRecyclerView = findViewById(R.id.expenseRecyclerView)
        totalExpenseTextView = findViewById(R.id.totalExpenseTextView)
        budgetTextView = findViewById(R.id.budgetTextView)
        addExpenseButton = findViewById(R.id.addExpenseButton)
        expenseDescriptionEditText = findViewById(R.id.expenseDescriptionEditText)
        expenseAmountEditText = findViewById(R.id.expenseAmountEditText)
        expenseCategoryEditText = findViewById(R.id.expenseCategoryEditText)
        setBudgetButton = findViewById(R.id.setBudgetButton)
        budgetAmountEditText = findViewById(R.id.budgetAmountEditText)
        viewReportButton = findViewById(R.id.viewReportButton)

        // Set up RecyclerView
        expenseRecyclerView.layoutManager = LinearLayoutManager(this)
        expenseAdapter = ExpenseAdapter(DataStorage.expenses)
        expenseRecyclerView.adapter = expenseAdapter

        // Load data
        updateUI()

        // Set listeners
        addExpenseButton.setOnClickListener { addExpense() }
        setBudgetButton.setOnClickListener { setBudget() }
        viewReportButton.setOnClickListener { viewReport() }
    }

    private fun addExpense() {
        val description = expenseDescriptionEditText.text.toString()
        val amount = expenseAmountEditText.text.toString().toDoubleOrNull() ?: 0.0
        val category = expenseCategoryEditText.text.toString()

        if (description.isNotEmpty() && amount > 0) {
            val newExpense = Expense(description, amount, category)
            DataStorage.addExpense(newExpense)
            updateUI()
            clearInputFields()
        }
    }

    private fun setBudget() {
        val amount = budgetAmountEditText.text.toString().toDoubleOrNull() ?: 0.0
        DataStorage.setBudget(amount)
        updateUI()
    }

    private fun viewReport() {
        val intent = Intent(this, ReportActivity::class.java)
        startActivity(intent)
    }

    private fun updateUI() {
        expenseAdapter.notifyDataSetChanged()
        totalExpenseTextView.text = "Total Expenses: $${DataStorage.getTotalExpenses()}"
        budgetTextView.text = "Budget: $${DataStorage.budget.amount}"
    }

    private fun clearInputFields() {
        expenseDescriptionEditText.text.clear()
        expenseAmountEditText.text.clear()
        expenseCategoryEditText.text.clear()
    }
}