package com.example.expense_tracker

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class ExpenseAdapter(private val expenses: MutableList<Expense>) : RecyclerView.Adapter<ExpenseAdapter.ExpenseViewHolder>() {

    class ExpenseViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val amountTextView: TextView = itemView.findViewById(R.id.amountTextView)
        val categoryTextView: TextView = itemView.findViewById(R.id.categoryTextView)
        val dateTextView: TextView = itemView.findViewById(R.id.dateTextView)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int):
            ExpenseViewHolder {
        val itemView = LayoutInflater.from(parent.context)
            .inflate(R.layout.expense_item, parent, false)
        return ExpenseViewHolder(itemView)
    }

    override fun onBindViewHolder(holder: ExpenseViewHolder, position: Int) {
        val currentExpense = expenses[position]
        holder.amountTextView.text = currentExpense.amount
        holder.categoryTextView.text = currentExpense.category
        holder.dateTextView.text = currentExpense.date
    }

    override fun getItemCount() = expenses.size

    fun addExpense(expense: Expense) {
        expenses.add(expense)
        notifyItemInserted(expenses.size - 1)
    }
}
