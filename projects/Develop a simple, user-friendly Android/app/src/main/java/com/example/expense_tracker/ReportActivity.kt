package com.example.expense_tracker

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.github.mikephil.charting.charts.PieChart
import com.github.mikephil.charting.data.PieData
import com.github.mikephil.charting.data.PieDataSet
import com.github.mikephil.charting.data.PieEntry
import com.github.mikephil.charting.utils.ColorTemplate

class ReportActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.report_view)

        val expenses = DataStorage.expenses // Retrieve expenses from DataStorage
        generateExpenseReport(expenses)
    }

    private fun generateExpenseReport(expenses: List<Expense>) {
        val categoryAmounts = mutableMapOf<String, Double>()
        for (expense in expenses) {
            categoryAmounts[expense.category] = categoryAmounts.getOrDefault(expense.category, 0.0) + expense.amount
        }

        val pieEntries = mutableListOf<PieEntry>()
        for ((category, amount) in categoryAmounts) {
            pieEntries.add(PieEntry(amount.toFloat(), category))
        }

        val dataSet = PieDataSet(pieEntries, "Expense Categories")
        dataSet.colors = ColorTemplate.COLORFUL_COLORS.toList()

        val pieData = PieData(dataSet)

        val pieChart = findViewById<PieChart>(R.id.expense_pie_chart)
        pieChart.data = pieData
        pieChart.description.isEnabled = false
        pieChart.invalidate() // Refresh the chart
    }
}