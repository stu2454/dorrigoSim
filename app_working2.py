# --- START OF FILE DorrigoSimClaude/app.py ---
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import calendar
import base64
from io import BytesIO
import json
import math # Needed for ceiling function

# Set page config
st.set_page_config(
    page_title="Rural Property Financial Simulator - Dorrigo NSW",
    page_icon="🏡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom CSS (No changes needed here)
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E5631;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #1E5631;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .stProgress > div > div > div > div {
        background-color: #1E5631;
    }
    .highlight {
        background-color: #E6F2E9;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .warning {
        background-color: #FFF3CD;
        color: #856404;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .positive {
        color: #1E5631;
        font-weight: bold;
    }
    .negative {
        color: #CA3433;
        font-weight: bold;
    }
    .streamlit-expanderHeader {
        font-size: 1.2rem;
        font-weight: 600;
    }
    /* Footer styling */
    .footer {
        position: relative;
        margin-top: 4rem;
        padding-top: 2rem;
        text-align: center;
        color: #666;
        font-size: 0.8rem;
    }
    /* Button styling */
    .stButton>button {
        background-color: #1E5631;
        color: white;
        border-radius: 0.3rem;
    }
    .stButton>button:hover {
        background-color: #2E7041;
        color: white;
    }
    /* Add a divider line */
    .divider {
        border-top: 1px solid #e0e0e0;
        margin-top: 2rem;
        margin-bottom: 2rem;
    }
    .upfront-summary {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1.5rem;
        border: 1px solid #d1d9e1;
    }
    .upfront-summary h3 {
        color: #1E5631;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Header (No changes needed here)
st.markdown("<h1 class='main-header'>Rural Property Financial Simulator</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 1.2rem;'>For Dorrigo, NSW Property Purchase Analysis</p>", unsafe_allow_html=True)

# --- Helper Functions ---

def calculate_nsw_stamp_duty(property_value):
    """Calculates approximate NSW Transfer Duty based on value."""
    # Rates as of late 2023/early 2024 - check Revenue NSW for current rates
    if property_value <= 16000:
        duty = property_value * 0.0125
    elif property_value <= 35000:
        duty = 200 + (property_value - 16000) * 0.015
    elif property_value <= 93000:
        duty = 485 + (property_value - 35000) * 0.0175
    elif property_value <= 351000:
        duty = 1500 + (property_value - 93000) * 0.035
    elif property_value <= 1168000:
        duty = 10530 + (property_value - 351000) * 0.045
    elif property_value <= 3504000: # Premium threshold starts here
         duty = 47295 + (property_value - 1168000) * 0.055
    else: # Above premium threshold
         duty = 175775 + (property_value - 3504000) * 0.07

    # Round up to nearest dollar
    return math.ceil(duty)

def estimate_lmi(property_price, loan_amount):
    """Estimates LMI cost if LVR > 80%. Returns LMI amount and LVR."""
    if property_price <= 0:
        return 0, 0
    lvr = (loan_amount / property_price) * 100
    lmi_cost = 0
    if lvr > 80:
        # Simplified LMI estimation - this varies significantly by lender!
        # Using a rough tiered percentage of the loan amount.
        if lvr <= 85:
            lmi_cost = loan_amount * 0.010 # Rough estimate: 1.0%
        elif lvr <= 90:
            lmi_cost = loan_amount * 0.018 # Rough estimate: 1.8%
        elif lvr <= 95:
            lmi_cost = loan_amount * 0.035 # Rough estimate: 3.5%
        else: # LVR > 95%
            lmi_cost = loan_amount * 0.045 # Rough estimate: 4.5%
        
        # Add stamp duty on LMI premium (approx 9-10% in NSW, let's use 9.5%)
        lmi_cost *= 1.095 
            
    return math.ceil(lmi_cost), lvr

def calculate_monthly_mortgage_payment(loan_amount, annual_interest_rate, loan_term_years):
    """Calculate the monthly mortgage payment."""
    if loan_amount <= 0 or annual_interest_rate <= 0 or loan_term_years <=0:
        return 0
    monthly_interest_rate = annual_interest_rate / 100 / 12
    num_payments = loan_term_years * 12
    if (1 + monthly_interest_rate)**num_payments == 1: # Avoid division by zero if rate is tiny
        return loan_amount / num_payments if num_payments > 0 else 0
    monthly_payment = loan_amount * (monthly_interest_rate * (1 + monthly_interest_rate)**num_payments) / ((1 + monthly_interest_rate)**num_payments - 1)
    return monthly_payment

def calculate_loan_balance_over_time(loan_amount, annual_interest_rate, monthly_payment, loan_term_years):
    """Calculate the loan balance over time."""
    if loan_amount <= 0 or monthly_payment <= 0:
         return [0] * (loan_term_years * 12 + 1)
         
    monthly_interest_rate = annual_interest_rate / 100 / 12
    num_payments = loan_term_years * 12
    loan_balance = [loan_amount]
    current_balance = loan_amount

    for i in range(1, num_payments + 1):
        interest = current_balance * monthly_interest_rate
        # Ensure payment doesn't exceed balance + interest
        actual_payment = min(monthly_payment, current_balance + interest)
        principal = actual_payment - interest
        current_balance -= principal
        # Ensure balance doesn't go below zero
        current_balance = max(0, current_balance)
        loan_balance.append(current_balance)

    return loan_balance

# --- START: Replace calculate_annual_totals function ---
def calculate_annual_totals(loan_balance, monthly_payment, loan_term_years, projection_years, annual_interest_rate):
    """
    Calculate annual loan statistics, ensuring length matches projection.
    Calculates annual payment based on principal reduction + interest paid.
    """
    if not loan_balance or loan_term_years <= 0: # Handle empty list or zero term
         # Return a DataFrame with zeros matching the projection period
         num_years_df = projection_years + 1
         return pd.DataFrame({
             'Year': range(num_years_df),
             'Loan_Balance': [0] * num_years_df,
             'Annual_Mortgage_Payment': [0] * num_years_df
         })

    # --- Get Annual Balances ---
    full_term_payments = loan_term_years * 12
    full_term_length_indices = full_term_payments + 1 # Indices 0 to num_payments

    # Pad loan_balance if it's shorter than expected (e.g., paid off very early due to rounding/large payments?)
    if len(loan_balance) < full_term_length_indices:
        loan_balance.extend([0] * (full_term_length_indices - len(loan_balance)))
    # Trim if somehow longer (shouldn't happen with current logic)
    elif len(loan_balance) > full_term_length_indices:
        loan_balance = loan_balance[:full_term_length_indices]

    # Get annual balance snapshots (balance at the *end* of year 0, year 1, etc.)
    # Index 0 = Start, Index 12 = End Year 1, Index 24 = End Year 2 ...
    annual_balance_indices = range(0, len(loan_balance), 12)
    annual_balance_snapshots = [loan_balance[i] for i in annual_balance_indices]

    # --- Calculate Annual Payments (Principal + Interest Method) ---
    annual_payments_list = []
    monthly_rate = annual_interest_rate / 100 / 12

    for year in range(projection_years + 1):
        payment_this_year = 0
        year_start_month_index = year * 12 # Month index at start of year (e.g., 0 for Year 1)
        year_end_month_index = (year + 1) * 12 # Month index at end of year (e.g., 12 for Year 1)

        # Check if any part of this year falls within the actual loan payment period
        if year_start_month_index < full_term_payments:
            # Calculate total interest paid during the months of this year
            interest_paid_this_year = 0
            # Iterate through months that fall *within* this projection year AND *within* the loan term
            for month_idx in range(year_start_month_index, min(year_end_month_index, full_term_payments)):
                 balance_before_payment = loan_balance[month_idx] # Balance at start of month idx
                 interest_this_month = max(0, balance_before_payment * monthly_rate) # Ensure non-negative
                 interest_paid_this_year += interest_this_month

            # Calculate principal paid this year by looking at balance change
            # Balance at start of year (use index year * 12)
            start_bal_idx = min(year_start_month_index, len(loan_balance) - 1)
            # Balance at end of year (use index (year + 1) * 12, capped at list length)
            end_bal_idx = min(year_end_month_index, len(loan_balance) - 1)

            balance_at_start_of_year = loan_balance[start_bal_idx]
            balance_at_end_of_year = loan_balance[end_bal_idx]
            principal_paid_this_year = max(0, balance_at_start_of_year - balance_at_end_of_year)

            # Total payment = principal reduction + interest paid
            payment_this_year = principal_paid_this_year + interest_paid_this_year

        annual_payments_list.append(payment_this_year)

    # --- Create DataFrame ---
    years_to_report = projection_years + 1

    # Pad annual_balance_snapshots if projection > loan term
    if len(annual_balance_snapshots) < years_to_report:
        annual_balance_snapshots.extend([0] * (years_to_report - len(annual_balance_snapshots)))

    # Ensure payments list matches projection years (should already, but safety check)
    if len(annual_payments_list) < years_to_report:
         annual_payments_list.extend([0] * (years_to_report - len(annual_payments_list)))

    df = pd.DataFrame({
        'Year': range(years_to_report),
        # Use snapshots which represent balance *after* payments for that year (or start for year 0)
        'Loan_Balance': annual_balance_snapshots[:years_to_report],
        'Annual_Mortgage_Payment': annual_payments_list[:years_to_report]
    })
    # Set Year 0 payment explicitly to 0
    df.loc[df['Year'] == 0, 'Annual_Mortgage_Payment'] = 0

    return df
# --- END: Replace calculate_annual_totals function ---

def project_income_expenses(annual_employment_income, annual_rental_income, annual_agistment_income,
                           annual_living_expenses, annual_boarding_expenses, annual_council_rates,
                           annual_insurance, annual_maintenance, annual_agistment_costs,
                           annual_additional_property_expenses, loan_data_df, # Pass the loan dataframe
                           income_growth_rate, inflation_rate, rental_growth_rate, projection_years):
    """Project income and expenses over time, using mortgage payments from loan_data_df."""
    years = list(range(projection_years + 1))

    # Initialize dataframe
    df = pd.DataFrame({'Year': years})

    # Project income
    df['Employment_Income'] = [annual_employment_income * ((1 + income_growth_rate/100) ** year) for year in years]
    df['Rental_Income'] = [annual_rental_income * ((1 + rental_growth_rate/100) ** year) for year in years]
    df['Agistment_Income'] = [annual_agistment_income * ((1 + inflation_rate/100) ** year) for year in years] # Assume agistment grows with inflation
    df['Total_Income'] = df['Employment_Income'] + df['Rental_Income'] + df['Agistment_Income']

    # Project expenses (excluding mortgage, which comes from loan_data_df)
    df['Living_Expenses'] = [annual_living_expenses * ((1 + inflation_rate/100) ** year) for year in years]
    df['Boarding_Expenses'] = [annual_boarding_expenses * ((1 + inflation_rate/100) ** year) for year in years]
    df['Council_Rates'] = [annual_council_rates * ((1 + inflation_rate/100) ** year) for year in years]
    df['Insurance'] = [annual_insurance * ((1 + inflation_rate/100) ** year) for year in years]
    df['Maintenance'] = [annual_maintenance * ((1 + inflation_rate/100) ** year) for year in years]
    df['Agistment_Costs'] = [annual_agistment_costs * ((1 + inflation_rate/100) ** year) for year in years]
    df['Additional_Property_Expenses'] = [annual_additional_property_expenses * ((1 + inflation_rate/100) ** year) for year in years]

    # Merge mortgage payments from loan_data_df
    df = pd.merge(df, loan_data_df[['Year', 'Annual_Mortgage_Payment']], on='Year', how='left')
    # Fill potential NaN if projection_years > loan_term (already handled in calculate_annual_totals)
    df['Annual_Mortgage_Payment'] = df['Annual_Mortgage_Payment'].fillna(0) 


    df['Total_Expenses_Excl_Mortgage'] = (df['Living_Expenses'] + df['Boarding_Expenses'] + df['Council_Rates'] +
                                        df['Insurance'] + df['Maintenance'] + df['Agistment_Costs'] +
                                        df['Additional_Property_Expenses'])
    df['Total_Expenses'] = df['Total_Expenses_Excl_Mortgage'] + df['Annual_Mortgage_Payment']


    # Calculate net cashflow
    df['Net_Cashflow'] = df['Total_Income'] - df['Total_Expenses']
    # Set Year 0 Net Cashflow to 0 (it's the starting point)
    df.loc[0, 'Net_Cashflow'] = 0 
    df['Cumulative_Cashflow'] = df['Net_Cashflow'].cumsum()

    return df

# --- Sidebar Inputs ---
try:
    st.sidebar.image("dorrigo.jpg", caption="Dorrigo, NSW", use_column_width=True)
except FileNotFoundError:
    st.sidebar.warning("dorrigo.jpg not found. Displaying placeholder.")
    st.sidebar.image("https://via.placeholder.com/300x100?text=Dorrigo+NSW", use_column_width=True)
st.sidebar.markdown("## Property & Upfront Costs")

# Property Information
property_price = st.sidebar.slider("Property Purchase Price (AUD$)", min_value=1000000, max_value=3000000, value=1700000, step=10000, format="%d", key="property_price")
current_home_value = st.sidebar.number_input("Current Home Value (Equity Source) (AUD$)", min_value=0, max_value=5000000, value=1300000, step=10000, format="%d", key="current_home_value")
other_upfront_costs = st.sidebar.number_input("Other Upfront Costs (Legal, Inspections etc.) (AUD$)", min_value=0, max_value=50000, value=5000, step=500, format="%d", key="other_upfront_costs")


# Financing Parameters
st.sidebar.markdown("## Financing")
with st.sidebar.expander("Loan & Deposit Details", expanded=True):
    use_equity = st.checkbox("Use equity from current home?", value=True, key="use_equity")

    equity_amount = 0
    additional_deposit = 0
    deposit_percentage_input = 20 # Default if not using equity

    if use_equity:
        equity_percentage = st.slider("Equity Percentage to Use (%)", min_value=0, max_value=100, value=80, step=5, key="equity_percentage")
        equity_amount = current_home_value * (equity_percentage / 100)
        additional_deposit = st.number_input("Additional Cash Deposit (AUD$)", min_value=0, max_value=1000000, value=50000, step=10000, format="%d", key="deposit_amount") # Renamed key
        total_available_deposit_funds = equity_amount + additional_deposit
        st.info(f"Available Deposit Funds: ${total_available_deposit_funds:,.2f}\n(${equity_amount:,.2f} equity + ${additional_deposit:,.2f} cash)")
    else:
        deposit_percentage_input = st.slider("Deposit Percentage (%)", min_value=10, max_value=100, value=20, step=5, key="deposit_percentage")
        total_available_deposit_funds = property_price * (deposit_percentage_input / 100)
        st.info(f"Available Deposit Funds: ${total_available_deposit_funds:,.2f}")

    # Calculate base loan amount BEFORE LMI consideration
    base_loan_amount = max(0, property_price - total_available_deposit_funds)

    # LMI Calculation
    estimated_lmi, initial_lvr = estimate_lmi(property_price, base_loan_amount)
    st.write(f"Initial Loan-to-Value Ratio (LVR): {initial_lvr:.2f}%")

    lmi_payable = 0
    if initial_lvr > 80:
        st.warning(f"LVR > 80%. Estimated LMI: ${estimated_lmi:,.0f}")
        capitalize_lmi = st.checkbox("Add LMI to Loan Amount?", value=True, key="capitalize_lmi")
        if capitalize_lmi:
            loan_amount_final = base_loan_amount + estimated_lmi
            lmi_payable = 0 # Included in loan
            st.info(f"LMI Capitalized. Final Loan Amount: ${loan_amount_final:,.0f}")
        else:
            loan_amount_final = base_loan_amount
            lmi_payable = estimated_lmi # Needs to be paid upfront
            st.info(f"LMI Payable Upfront: ${lmi_payable:,.0f}. Loan Amount: ${loan_amount_final:,.0f}")
    else:
        st.success("LVR is 80% or below. No LMI typically required.")
        loan_amount_final = base_loan_amount
        capitalize_lmi = False # Ensure this is False if no LMI

    # Allow manual override of final loan amount
    loan_amount_final = st.number_input("Final Loan Amount (AUD$) *", min_value=0, max_value=int(property_price * 1.1), value=int(loan_amount_final), step=1000, format="%d", key="loan_amount", help="Auto-calculated based on deposit and LMI settings. You can override.")

    # Recalculate LVR based on final loan amount for display consistency
    _, final_lvr = estimate_lmi(property_price, loan_amount_final)

    interest_rate = st.slider("Interest Rate (%)", min_value=3.0, max_value=10.0, value=6.0, step=0.1, key="interest_rate") # Increased max rate
    loan_term = st.slider("Loan Term (Years)", min_value=10, max_value=30, value=25, step=1, key="loan_term") # Step 1 year

# Income Sources
st.sidebar.markdown("## Income Sources (Annualized)")
# Employment Income
with st.sidebar.expander("Employment Income", expanded=True):
    combined_fortnightly_income = st.number_input("Combined Fortnightly After-Tax Income (AUD$)", min_value=0, max_value=20000, value=5000, step=100, format="%d", key="combined_fortnightly_income")
    annual_employment_income = combined_fortnightly_income * 26
    st.write(f"Annual: ${annual_employment_income:,.2f}")

# Rental Income
with st.sidebar.expander("Rental Income", expanded=False):
    include_rental = st.checkbox("Include Rental Income", value=True, key="include_rental")
    if include_rental:
        weekly_rental = st.slider("Weekly Rental Income (AUD$)", min_value=0, max_value=1000, value=450, step=10, format="%d", key="weekly_rental")
        occupancy_rate = st.slider("Occupancy Rate (%)", min_value=0, max_value=100, value=90, step=5, key="occupancy_rate")
        annual_rental_income = weekly_rental * 52 * (occupancy_rate / 100)
        st.write(f"Annual: ${annual_rental_income:,.2f}")
    else:
        annual_rental_income = 0
        weekly_rental = 0 # ensure defined
        occupancy_rate = 0 # ensure defined

# Agistment Income
with st.sidebar.expander("Agistment Income", expanded=False):
    include_agistment = st.checkbox("Include Agistment Income", value=True, key="include_agistment")
    if include_agistment:
        num_cattle = st.slider("Number of Cattle for Agistment", min_value=0, max_value=100, value=20, step=5, key="num_cattle")
        agistment_rate = st.slider("Agistment Rate (AUD$/head/week)", min_value=0.0, max_value=20.0, value=8.0, step=0.5, key="agistment_rate")
        annual_agistment_income = num_cattle * agistment_rate * 52
        st.write(f"Annual: ${annual_agistment_income:,.2f}")
    else:
        annual_agistment_income = 0
        num_cattle = 0 # ensure defined
        agistment_rate = 0 # ensure defined


# Expenses
st.sidebar.markdown("## Expenses (Annualized)")
with st.sidebar.expander("Living & Education Expenses", expanded=True):
    fortnightly_living_expenses = st.number_input("Fortnightly Living Expenses (AUD$)", min_value=0, max_value=10000, value=3000, step=100, format="%d", key="fortnightly_living_expenses")
    annual_living_expenses = fortnightly_living_expenses * 26
    st.write(f"Annual Living: ${annual_living_expenses:,.2f}")

    num_children_boarding = st.number_input("Number of Children in Boarding School", min_value=0, max_value=10, value=2, step=1, key="num_children_boarding")
    annual_boarding_fee_per_child = st.number_input("Annual Boarding School Fee per Child (AUD$)", min_value=0, max_value=100000, value=30000, step=1000, format="%d", key="annual_boarding_fee_per_child")
    annual_boarding_expenses = num_children_boarding * annual_boarding_fee_per_child
    st.write(f"Annual Boarding: ${annual_boarding_expenses:,.2f}")

with st.sidebar.expander("Property Running Costs", expanded=True):
    annual_council_rates = st.number_input("Annual Council Rates (AUD$)", min_value=0, max_value=10000, value=2500, step=100, format="%d", key="annual_council_rates")
    annual_insurance = st.number_input("Annual Insurance (Building/Contents/Liability) (AUD$)", min_value=0, max_value=10000, value=2000, step=100, format="%d", key="annual_insurance")
    annual_maintenance = st.number_input("Annual Property Maintenance (AUD$)", min_value=0, max_value=30000, value=6000, step=500, format="%d", key="annual_maintenance")

    # Only show if agistment is included
    if include_agistment:
        annual_agistment_costs = st.number_input("Annual Agistment Costs (Fencing, Water etc.) (AUD$)", min_value=0, max_value=20000, value=2000, step=500, format="%d", key="annual_agistment_costs")
    else:
        annual_agistment_costs = 0

    annual_additional_property_expenses = st.number_input("Other Annual Property Expenses (AUD$)", min_value=0, max_value=20000, value=1000, step=500, format="%d", key="annual_additional_property_expenses")
    total_annual_prop_running_costs = annual_council_rates + annual_insurance + annual_maintenance + annual_agistment_costs + annual_additional_property_expenses
    st.write(f"Total Annual Property Running Costs: ${total_annual_prop_running_costs:,.2f}")


# Advanced Settings
with st.sidebar.expander("Advanced Settings & Projections", expanded=False):
    inflation_rate = st.slider("Annual Inflation Rate (Expenses Growth) (%)", min_value=0.0, max_value=10.0, value=2.5, step=0.1, key="inflation_rate")
    property_growth_rate = st.slider("Annual Property Value Growth Rate (%)", min_value=-5.0, max_value=10.0, value=4.0, step=0.1, key="property_growth_rate") # Allow negative growth
    income_growth_rate = st.slider("Annual Employment Income Growth Rate (%)", min_value=0.0, max_value=10.0, value=3.0, step=0.1, key="income_growth_rate")
    rental_growth_rate = st.slider("Annual Rental Income Growth Rate (%)", min_value=0.0, max_value=10.0, value=3.5, step=0.1, key="rental_growth_rate")
    projection_years = st.slider("Projection Years", min_value=1, max_value=40, value=loan_term, step=1, key="projection_years") # Default to loan term
    risk_analysis = st.checkbox("Include Risk Analysis Section", value=True, key="risk_analysis")


# --- Main Calculation Section ---

# Calculate Stamp Duty
stamp_duty = calculate_nsw_stamp_duty(property_price)

# Calculate total upfront funds needed
total_upfront_costs = total_available_deposit_funds + stamp_duty + lmi_payable + other_upfront_costs
funds_needed_for_deposit_and_costs = (property_price - loan_amount_final) + stamp_duty + lmi_payable + other_upfront_costs

# Calculate monthly mortgage payment using final loan amount
monthly_mortgage_payment = calculate_monthly_mortgage_payment(loan_amount_final, interest_rate, loan_term)
# annual_mortgage_payment_yr1 = monthly_mortgage_payment * 12 # Remove this, get from loan_data later

# Calculate loan balance over time
loan_balance = calculate_loan_balance_over_time(loan_amount_final, interest_rate, monthly_mortgage_payment, loan_term)

# Calculate annual loan data matching projection years
# *** MODIFIED CALL HERE - Added interest_rate ***
loan_data = calculate_annual_totals(loan_balance, monthly_mortgage_payment, loan_term, projection_years, interest_rate)

# Project income and expenses
projection_data = project_income_expenses(
    annual_employment_income, annual_rental_income, annual_agistment_income,
    annual_living_expenses, annual_boarding_expenses, annual_council_rates,
    annual_insurance, annual_maintenance, annual_agistment_costs,
    annual_additional_property_expenses, loan_data, # Pass the calculated loan data
    income_growth_rate, inflation_rate, rental_growth_rate, projection_years
)

# Merge loan balance into projection data
merged_data = pd.merge(projection_data, loan_data[['Year', 'Loan_Balance']], on='Year', how='left')

# Calculate property value and LVR over time
merged_data['Property_Value'] = [property_price * ((1 + property_growth_rate/100) ** year) for year in merged_data['Year']]
# Avoid division by zero if property value becomes zero or negative (unlikely but safe)
merged_data['LVR_Percent'] = (merged_data['Loan_Balance'] / merged_data['Property_Value'].replace(0, np.nan)) * 100
merged_data['LVR_Percent'] = merged_data['LVR_Percent'].fillna(0).clip(lower=0) # Handle NaN and ensure non-negative


# --- Main Content Area - Results ---

# Upfront Costs Summary
st.markdown("<div class='upfront-summary'>", unsafe_allow_html=True)
st.markdown("### Upfront Funds Required & Summary")
col1, col2 = st.columns(2)
with col1:
    st.metric("Property Price", f"${property_price:,.0f}")
    st.metric("Stamp Duty (NSW Est.)", f"${stamp_duty:,.0f}")
    st.metric("LMI (Payable Upfront)", f"${lmi_payable:,.0f}")
    st.metric("Other Upfront Costs", f"${other_upfront_costs:,.0f}")
with col2:
    # Calculate deposit actually used = Property Price - Final Loan Amount
    actual_deposit_paid = max(0, property_price - loan_amount_final) 
    st.metric("Deposit Paid", f"${actual_deposit_paid:,.0f}")
    st.metric("Total Funds Required at Settlement", f"${funds_needed_for_deposit_and_costs:,.0f}")
    st.metric("Available Deposit Funds", f"${total_available_deposit_funds:,.0f}")

    # Compare available funds vs required
    shortfall_surplus = total_available_deposit_funds - funds_needed_for_deposit_and_costs
    if shortfall_surplus >= 0:
        st.success(f"Funds Surplus: ${shortfall_surplus:,.0f}")
    else:
        st.error(f"Funds Shortfall: ${abs(shortfall_surplus):,.0f}")
st.markdown("</div>", unsafe_allow_html=True)


st.markdown("<h2 class='sub-header'>Financial Summary (Year 1)</h2>", unsafe_allow_html=True)

# Key metrics for Year 1
col1, col2, col3 = st.columns(3)

# Total income (Year 1 - from merged_data row 1, as row 0 is start)
total_income_yr1 = merged_data.loc[1, 'Total_Income'] if projection_years >=1 else merged_data.loc[0, 'Total_Income']
with col1:
    st.markdown(f"### Total Annual Income (Yr 1)")
    st.markdown(f"<h3 class='positive'>${total_income_yr1:,.2f}</h3>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"Employment: ${merged_data.loc[1, 'Employment_Income'] if projection_years >=1 else merged_data.loc[0, 'Employment_Income']:,.2f}")
    if include_rental:
        st.markdown(f"Rental: ${merged_data.loc[1, 'Rental_Income'] if projection_years >=1 else merged_data.loc[0, 'Rental_Income']:,.2f}")
    if include_agistment:
        st.markdown(f"Agistment: ${merged_data.loc[1, 'Agistment_Income'] if projection_years >=1 else merged_data.loc[0, 'Agistment_Income']:,.2f}")

# Total expenses (Year 1 - from merged_data row 1)
total_expenses_yr1 = merged_data.loc[1, 'Total_Expenses'] if projection_years >=1 else merged_data.loc[0, 'Total_Expenses']
annual_mortgage_payment_yr1 = merged_data.loc[1, 'Annual_Mortgage_Payment'] if projection_years >=1 else 0 # Get actual yr 1 payment
prop_running_costs_yr1 = merged_data.loc[1, ['Council_Rates', 'Insurance', 'Maintenance', 'Agistment_Costs', 'Additional_Property_Expenses']].sum() if projection_years >=1 else 0
living_expenses_yr1 = merged_data.loc[1, 'Living_Expenses'] if projection_years >=1 else 0
boarding_expenses_yr1 = merged_data.loc[1, 'Boarding_Expenses'] if projection_years >=1 else 0

with col2:
    st.markdown(f"### Total Annual Expenses (Yr 1)")
    st.markdown(f"<h3 class='negative'>${total_expenses_yr1:,.2f}</h3>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"Mortgage: ${annual_mortgage_payment_yr1:,.2f}")
    st.markdown(f"Living: ${living_expenses_yr1:,.2f}")
    st.markdown(f"Boarding: ${boarding_expenses_yr1:,.2f}")
    st.markdown(f"Property Running: ${prop_running_costs_yr1:,.2f}")


# Net position (Year 1)
net_position_yr1 = total_income_yr1 - total_expenses_yr1
with col3:
    st.markdown(f"### Net Annual Position (Yr 1)")
    if net_position_yr1 >= 0:
        st.markdown(f"<h3 class='positive'>+${net_position_yr1:,.2f}</h3>", unsafe_allow_html=True)
    else:
        st.markdown(f"<h3 class='negative'>${net_position_yr1:,.2f}</h3>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"Monthly: ${net_position_yr1/12:,.2f}")
    st.markdown(f"Fortnightly: ${net_position_yr1/26:,.2f}")
    st.markdown(f"Weekly: ${net_position_yr1/52:,.2f}")

# Break-even analysis (Uses cumulative cashflow which starts calculation from Year 1's net cashflow)
st.markdown("<h2 class='sub-header'>Break-even & Key Ratios</h2>", unsafe_allow_html=True)

# Find break-even year (First year where Cumulative Cashflow is non-negative)
# Ensure we look at Year >= 1 for break-even point based on operational cashflow
break_even_year = None
cumulative_cashflow_positive_df = merged_data[merged_data['Year'] >= 1] # Start check from year 1
positive_cumulative_years = cumulative_cashflow_positive_df[cumulative_cashflow_positive_df['Cumulative_Cashflow'] >= 0]

if not positive_cumulative_years.empty:
    break_even_year = positive_cumulative_years['Year'].iloc[0]

col1, col2 = st.columns(2)

with col1:
    # Break-even status
    if net_position_yr1 >= 0:
        st.markdown("<div class='highlight'>Scenario starts <span class='positive'>cash-flow positive</span> in Year 1.</div>", unsafe_allow_html=True)
    elif break_even_year is not None and break_even_year <= projection_years:
        st.markdown(f"<div class='highlight'>Scenario cumulative cash flow becomes <span class='positive'>positive</span> around Year {break_even_year}.</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='warning'>Scenario cumulative cash flow does not become positive within the {projection_years}-year projection period.</div>", unsafe_allow_html=True)

with col2:
    # Key ratios (using Year 1 income and initial loan amount)
    # Avoid division by zero if income is zero
    debt_to_income_yr1 = loan_amount_final / total_income_yr1 if total_income_yr1 else 0
    expense_to_income_yr1 = total_expenses_yr1 / total_income_yr1 if total_income_yr1 else 0
    mortgage_to_income_yr1 = annual_mortgage_payment_yr1 / total_income_yr1 if total_income_yr1 else 0

    st.markdown(f"**Initial LVR**: {final_lvr:.2f}%") # Use final LVR
    st.markdown(f"**Debt to Income (Yr 1)**: {debt_to_income_yr1:.2f}x")
    st.markdown(f"**Expense to Income (Yr 1)**: {expense_to_income_yr1:.2f}x")
    st.markdown(f"**Mortgage to Income (Yr 1)**: {mortgage_to_income_yr1:.2f}x")


# --- Visualizations ---

# Cash Flow Visualization
st.markdown("<h2 class='sub-header'>Cash Flow Projection</h2>", unsafe_allow_html=True)
fig_cashflow = go.Figure()
fig_cashflow.add_trace(go.Bar(x=merged_data['Year'], y=merged_data['Total_Income'], name='Total Income', marker_color='#1E5631'))
fig_cashflow.add_trace(go.Bar(x=merged_data['Year'], y=merged_data['Total_Expenses'], name='Total Expenses', marker_color='#CA3433'))
fig_cashflow.add_trace(go.Scatter(x=merged_data['Year'], y=merged_data['Net_Cashflow'], name='Net Cashflow (Annual)', mode='lines+markers', line=dict(color='#365F91', width=3), marker=dict(size=6)))
fig_cashflow.add_trace(go.Scatter(x=merged_data['Year'], y=merged_data['Cumulative_Cashflow'], name='Cumulative Cashflow', mode='lines', line=dict(color='#F49130', width=3, dash='dot')))
fig_cashflow.update_layout(title='Annual Cash Flow Projection', xaxis_title='Year', yaxis_title='Amount (AUD$)', barmode='group', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), height=500)
st.plotly_chart(fig_cashflow, use_container_width=True)


# Loan Amortization, Property Value & LVR Chart
st.markdown("<h2 class='sub-header'>Loan, Equity & LVR Projection</h2>", unsafe_allow_html=True)
fig_loan = go.Figure()
fig_loan.add_trace(go.Scatter(x=merged_data['Year'], y=merged_data['Loan_Balance'], name='Loan Balance', mode='lines', line=dict(color='#8C4646', width=3)))
fig_loan.add_trace(go.Scatter(x=merged_data['Year'], y=merged_data['Property_Value'], name='Est. Property Value', mode='lines', line=dict(color='#376D37', width=3, dash='dash')))
# Calculate Equity
merged_data['Equity'] = merged_data['Property_Value'] - merged_data['Loan_Balance']
fig_loan.add_trace(go.Scatter(x=merged_data['Year'], y=merged_data['Equity'], name='Estimated Equity', mode='lines', line=dict(color='#365F91', width=3)))
# Add LVR on secondary axis
fig_loan.add_trace(go.Scatter(x=merged_data['Year'], y=merged_data['LVR_Percent'], name='LVR (%)', mode='lines', line=dict(color='#FFA500', width=2, dash='dot'), yaxis="y2")) # Orange color for LVR

# Update layout for dual axis
fig_loan.update_layout(
    title='Loan Balance, Property Value, Equity, and LVR Over Time',
    xaxis_title='Year',
    yaxis=dict(title='Amount (AUD$)'),
    yaxis2=dict(title='LVR (%)', overlaying='y', side='right', range=[0, 100], ticksuffix='%'), # Set range 0-100 for LVR axis
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    height=500
)
st.plotly_chart(fig_loan, use_container_width=True)


# Detailed income and expense breakdown (Year 1)
st.markdown("<h2 class='sub-header'>Income & Expense Breakdown (Year 1)</h2>", unsafe_allow_html=True)
col1, col2 = st.columns(2)
# Use Year 1 data (index 1) if available, otherwise Year 0 (index 0)
idx = 1 if projection_years >=1 else 0

with col1:
    # Income breakdown Yr 1
    income_data_yr1 = {
        'Category': ['Employment', 'Rental', 'Agistment'],
        'Amount': [merged_data.loc[idx, 'Employment_Income'], merged_data.loc[idx, 'Rental_Income'], merged_data.loc[idx, 'Agistment_Income']]
    }
    income_df_yr1 = pd.DataFrame(income_data_yr1)
    income_df_yr1 = income_df_yr1[income_df_yr1['Amount'] > 0.01] # Filter small/zero amounts
    
    if not income_df_yr1.empty:
        fig_income = px.pie(income_df_yr1, values='Amount', names='Category', title='Income Sources (Year 1)', color_discrete_sequence=px.colors.sequential.Greens_r)
        fig_income.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_income, use_container_width=True)
    else:
        st.info("No significant income sources in Year 1.")

with col2:
    # Expense breakdown Yr 1
    expense_data_yr1 = {
        'Category': ['Mortgage', 'Living', 'Boarding', 'Prop. Running Costs'],
        'Amount': [
            merged_data.loc[idx, 'Annual_Mortgage_Payment'],
            merged_data.loc[idx, 'Living_Expenses'],
            merged_data.loc[idx, 'Boarding_Expenses'],
            prop_running_costs_yr1 # Use summed value calculated earlier
            ]
    }
    expense_df_yr1 = pd.DataFrame(expense_data_yr1)
    expense_df_yr1 = expense_df_yr1[expense_df_yr1['Amount'] > 0.01] # Filter small/zero amounts

    if not expense_df_yr1.empty:
        fig_expense = px.pie(expense_df_yr1, values='Amount', names='Category', title='Expense Categories (Year 1)', color_discrete_sequence=px.colors.sequential.Reds_r)
        fig_expense.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_expense, use_container_width=True)
    else:
        st.info("No significant expenses in Year 1.")


# Risk Analysis (Modified to use final loan amount and handle LMI capitalization)
if risk_analysis:
    st.markdown("<h2 class='sub-header'>Risk Analysis (Year 1 Impact)</h2>", unsafe_allow_html=True)

    # Define risk scenarios - focus on Year 1 impact
    base_occupancy = occupancy_rate / 100 if include_rental else 0
    base_num_cattle = num_cattle if include_agistment else 0

    risk_scenarios = {
        "Base Case": {
            "occupancy_factor": 1.0,
            "agistment_factor": 1.0,
            "interest_rate_increase": 0.0
        },
        "No Rental Income": {
            "occupancy_factor": 0.0,
            "agistment_factor": 1.0,
            "interest_rate_increase": 0.0
        },
         "No Agistment Income": {
            "occupancy_factor": 1.0,
            "agistment_factor": 0.0,
            "interest_rate_increase": 0.0
        },
        "Reduced Agistment (50%)": {
            "occupancy_factor": 1.0,
            "agistment_factor": 0.5,
            "interest_rate_increase": 0.0
        },
        "Interest Rate +2%": {
            "occupancy_factor": 1.0, # Assume base occupancy/agistment for this scenario
            "agistment_factor": 1.0,
            "interest_rate_increase": 2.0
        },
         "Interest Rate +3%": {
            "occupancy_factor": 1.0, # Assume base occupancy/agistment for this scenario
            "agistment_factor": 1.0,
            "interest_rate_increase": 3.0
        },
        "Stress Test (Vacant, Low Agist, Rate +2%)": {
            "occupancy_factor": 0.5, # e.g., 50% vacancy
            "agistment_factor": 0.5, # e.g., 50% capacity/rate
            "interest_rate_increase": 2.0
        }
    }

    # Calculate cashflow for each scenario in Year 1
    scenario_results = []

    # Get Year 1 base expenses (excluding mortgage)
    base_expenses_excl_mortgage_yr1 = living_expenses_yr1 + boarding_expenses_yr1 + prop_running_costs_yr1

    for scenario_name, params in risk_scenarios.items():
        # Adjust income
        scen_rental_income = annual_rental_income * params["occupancy_factor"] # Use base annual rental
        scen_agistment_income = annual_agistment_income * params["agistment_factor"] # Use base annual agistment
        scen_total_income = annual_employment_income + scen_rental_income + scen_agistment_income # Use base employment income

        # Adjust mortgage
        scen_interest_rate = interest_rate + params["interest_rate_increase"]
        # Recalculate LMI if rate increase pushes LVR over 80 (edge case, usually LMI fixed at start)
        # For simplicity, assume LMI decision (capitalized or not) is fixed from base case
        scen_loan_amount = loan_amount_final # Use the final loan amount decided earlier
        
        scen_monthly_payment = calculate_monthly_mortgage_payment(scen_loan_amount, scen_interest_rate, loan_term)
        scen_annual_mortgage = scen_monthly_payment * 12

        # Calculate total expenses for scenario
        scen_total_expenses = base_expenses_excl_mortgage_yr1 + scen_annual_mortgage

        # Calculate net position
        scen_net_position = scen_total_income - scen_total_expenses

        scenario_results.append({
            "Scenario": scenario_name,
            "Annual Net Position (Year 1)": scen_net_position,
            "Monthly Net Position (Year 1)": scen_net_position / 12,
            "Interest Rate (%)": scen_interest_rate,
            "Annual Mortgage": scen_annual_mortgage
        })

    risk_df = pd.DataFrame(scenario_results)

    # Show risk comparison chart
    fig_risk = px.bar(
        risk_df,
        x="Scenario",
        y="Annual Net Position (Year 1)",
        color="Annual Net Position (Year 1)",
        color_continuous_scale=["#CA3433", "#FFF3CD", "#1E5631"], # Red -> Yellow -> Green
        color_continuous_midpoint=0, # Center color scale at zero
        title="Estimated Annual Net Position (Year 1) by Risk Scenario",
        text="Annual Net Position (Year 1)"
    )
    fig_risk.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
    fig_risk.update_layout(height=500, xaxis={'categoryorder':'array', 'categoryarray': risk_df["Scenario"]}) # Keep order
    
    # Calculate dynamic y-axis range with padding
    if not risk_df.empty:
        min_val = risk_df["Annual Net Position (Year 1)"].min()
        max_val = risk_df["Annual Net Position (Year 1)"].max()

        # Determine padding (e.g., 10% of the data range)
        data_range = max_val - min_val
        if data_range == 0: # Avoid division by zero if all values are the same
             # Set padding based on 10% of the value, or a default if value is 0
             padding = abs(max_val * 0.1) if max_val != 0 else 1000 
        else:
             padding = data_range * 0.10 # 10% padding

        # Apply padding
        yaxis_min = min_val - padding
        yaxis_max = max_val + padding

        # Optional: Ensure zero is included in the range if data is all positive or all negative
        # This often makes financial bar charts easier to interpret
        if min_val >= 0: # All data positive or zero
            yaxis_min = min(0, yaxis_min)
        if max_val <= 0: # All data negative or zero
            yaxis_max = max(0, yaxis_max)

        # Update the figure layout with the calculated range
        fig_risk.update_layout(yaxis_range=[yaxis_min, yaxis_max])
        
    st.plotly_chart(fig_risk, use_container_width=True)

    # Risk scenario table
    st.markdown("### Detailed Risk Scenario Analysis (Year 1 Estimates)")
    display_risk_df = risk_df.copy()
    display_risk_df["Annual Net Position (Year 1)"] = display_risk_df["Annual Net Position (Year 1)"].map("${:,.0f}".format)
    display_risk_df["Monthly Net Position (Year 1)"] = display_risk_df["Monthly Net Position (Year 1)"].map("${:,.0f}".format)
    display_risk_df["Interest Rate (%)"] = display_risk_df["Interest Rate (%)"].map("{:.2f}%".format)
    display_risk_df["Annual Mortgage"] = display_risk_df["Annual Mortgage"].map("${:,.0f}".format)
    st.dataframe(display_risk_df, use_container_width=True)

    # Add risk interpretation (based on Year 1 net position)
    st.markdown("### Risk Interpretation (Based on Year 1)")
    base_case_yr1 = risk_df.iloc[0]["Annual Net Position (Year 1)"] # First row is base case
    worst_case_yr1 = risk_df[risk_df['Scenario'].str.contains("Stress Test", case=False)]["Annual Net Position (Year 1)"].iloc[0]

    if base_case_yr1 >= 0 and worst_case_yr1 >= 0:
        st.markdown("<div class='highlight'>Initial financial plan appears <span class='positive'>robust</span>. Even under the stress test scenario, Year 1 maintains a positive cash flow.</div>", unsafe_allow_html=True)
    elif base_case_yr1 >= 0 and worst_case_yr1 < 0:
        st.markdown("<div class='warning'>Initial financial plan is <span class='negative'>vulnerable to stress scenarios</span>. While the base case is positive in Year 1, consider building a larger buffer for unexpected events or higher rates.</div>", unsafe_allow_html=True)
    else: # Base case is negative
        st.markdown("<div class='warning'>Initial financial plan shows <span class='negative'>significant risk</span>. Even in the base case scenario, Year 1 has a negative cash flow. Review assumptions, income, expenses, or loan structure.</div>", unsafe_allow_html=True)


# Detailed projection table
with st.expander("Detailed Annual Projection Data"):
    display_data = merged_data.copy()
    # Select and format columns for display
    cols_to_display = [
        'Year', 'Total_Income', 'Total_Expenses', 'Net_Cashflow', 'Cumulative_Cashflow',
        'Loan_Balance', 'Property_Value', 'Equity', 'LVR_Percent', 'Annual_Mortgage_Payment',
        'Employment_Income', 'Rental_Income', 'Agistment_Income',
        'Living_Expenses', 'Boarding_Expenses', 'Council_Rates', 'Insurance', 'Maintenance', 'Agistment_Costs'
    ]
    display_data = display_data[cols_to_display]
    
    # Formatting numerical columns
    for col in display_data.columns:
        if col == 'Year':
            continue
        elif col == 'LVR_Percent':
             display_data[col] = display_data[col].map("{:.2f}%".format)
        elif display_data[col].dtype in ['float64', 'int64']:
            # Apply currency format, handle potential NaNs if any survived
             display_data[col] = display_data[col].apply(lambda x: f"${x:,.0f}" if pd.notnull(x) else "N/A")

    st.dataframe(display_data, use_container_width=True)

    # Download button for projection data
    csv = merged_data.to_csv(index=False)
    st.download_button(
        label="Download Full Projection Data as CSV",
        data=csv,
        file_name="dorrigo_property_projection_detailed.csv",
        mime="text/csv",
    )

# PDF Export function (Needs update for new charts/info)
def create_pdf_summary():
    """Export a summary report as PDF (Updated for new info)"""
    try:
        # Ensure matplotlib backend is suitable for non-GUI environments
        import matplotlib
        matplotlib.use('Agg') 
        from matplotlib.backends.backend_pdf import PdfPages
        import matplotlib.pyplot as plt
        from matplotlib.ticker import FuncFormatter
        import io

        buffer = io.BytesIO()

        with PdfPages(buffer) as pdf:
            # --- Page 1: Title and Upfront Summary ---
            fig = plt.figure(figsize=(8.5, 11))
            fig.suptitle('Dorrigo Property Financial Summary', fontsize=18, y=0.96)
            
            # Summary Text (Increased y values to move up)
            summary_text = f"""
            Property Price: ${property_price:,.0f}
            Stamp Duty (Est.): ${stamp_duty:,.0f}
            LMI (Payable Upfront): ${lmi_payable:,.0f}
            Other Upfront Costs: ${other_upfront_costs:,.0f}
            -------------------------------------
            Total Upfront Costs (excl. deposit): ${stamp_duty + lmi_payable + other_upfront_costs:,.0f}
            Deposit Paid: ${actual_deposit_paid:,.0f}
            Total Funds Required: ${funds_needed_for_deposit_and_costs:,.0f}
            Available Deposit Funds: ${total_available_deposit_funds:,.0f}
            Shortfall/Surplus: ${shortfall_surplus:,.0f} {'(Surplus)' if shortfall_surplus >= 0 else '(Shortfall)'}
            -------------------------------------
            Loan Amount: ${loan_amount_final:,.0f} (LVR: {final_lvr:.1f}%)
            Interest Rate: {interest_rate:.2f}% | Loan Term: {loan_term} years
            Year 1 Est. Net Position: ${net_position_yr1:,.0f}
            """
            plt.figtext(0.1, 0.85, summary_text, fontsize=10, va='top')
            plt.figtext(0.5, 0.05, f"Generated on {datetime.now().strftime('%Y-%m-%d')}", fontsize=8, ha='center')
            plt.axis('off')
            pdf.savefig(fig)
            plt.close(fig)

            # --- Page 2: Cash Flow Projection ---
            fig_cf, ax_cf = plt.subplots(figsize=(8.5, 5.5)) # Adjusted size
            years = merged_data['Year'].values
            bar_width = 0.35
            ax_cf.bar(years - bar_width/2, merged_data['Total_Income'], width=bar_width, label='Income', color='#1E5631', alpha=0.7)
            ax_cf.bar(years + bar_width/2, merged_data['Total_Expenses'], width=bar_width, label='Expenses', color='#CA3433', alpha=0.7)
            ax_cf.plot(years, merged_data['Net_Cashflow'], 'o-', label='Net Cashflow', color='#365F91', markersize=4)
            ax_cf.plot(years, merged_data['Cumulative_Cashflow'], 'o--', label='Cumulative Cashflow', color='#F49130', markersize=4)
            ax_cf.set_xlabel('Year')
            ax_cf.set_ylabel('Amount (AUD$)')
            ax_cf.set_title('Annual Cash Flow Projection')
            ax_cf.legend(fontsize=8)
            ax_cf.grid(True, linestyle='--', alpha=0.6)
            ax_cf.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'${x:,.0f}'))
            plt.tight_layout()
            pdf.savefig(fig_cf)
            plt.close(fig_cf)

            # --- Page 3: Loan, Equity & LVR ---
            fig_loan, ax1 = plt.subplots(figsize=(8.5, 5.5)) # Adjusted size
            ax1.plot(years, merged_data['Loan_Balance'], 'o-', label='Loan Balance', color='#8C4646', markersize=4)
            ax1.plot(years, merged_data['Property_Value'], 'o--', label='Est. Property Value', color='#376D37', markersize=4)
            ax1.plot(years, merged_data['Equity'], 'o-', label='Est. Equity', color='#365F91', markersize=4)
            ax1.set_xlabel('Year')
            ax1.set_ylabel('Amount (AUD$)', color='black')
            ax1.tick_params(axis='y', labelcolor='black')
            ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'${x:,.0f}'))
            ax1.grid(True, linestyle='--', alpha=0.6)
            
            # Secondary axis for LVR
            ax2 = ax1.twinx()
            ax2.plot(years, merged_data['LVR_Percent'], 'o:', label='LVR (%)', color='#FFA500', markersize=4)
            ax2.set_ylabel('LVR (%)', color='#FFA500')
            ax2.tick_params(axis='y', labelcolor='#FFA500')
            ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.0f}%'))
            ax2.set_ylim(0, 105) # LVR Axis limit 0-105%

            # Combine legends
            lines, labels = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax2.legend(lines + lines2, labels + labels2, loc='best', fontsize=8)

            ax1.set_title('Loan Balance, Property Value, Equity, and LVR Over Time')
            plt.tight_layout()
            pdf.savefig(fig_loan)
            plt.close(fig_loan)

            # --- Page 4: Risk Analysis (if enabled) ---
            if risk_analysis and not risk_df.empty:
                fig_risk, ax_risk = plt.subplots(figsize=(8.5, 5.5)) # Adjusted size
                scenarios = risk_df["Scenario"]
                net_positions_yr1 = risk_df["Annual Net Position (Year 1)"]
                colors = ['#1E5631' if pos >= 0 else '#CA3433' for pos in net_positions_yr1]
                
                bars = ax_risk.bar(scenarios, net_positions_yr1, color=colors, alpha=0.8)
                ax_risk.axhline(0, color='grey', linewidth=0.8) # Zero line
                
                ax_risk.set_xlabel('Scenario')
                ax_risk.set_ylabel('Annual Net Position (Year 1, AUD$)')
                ax_risk.set_title('Risk Analysis - Year 1 Net Position Impact')
                ax_risk.grid(True, linestyle='--', alpha=0.6, axis='y')
                ax_risk.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'${x:,.0f}'))
                plt.xticks(rotation=45, ha='right', fontsize=8) # Rotate labels
                plt.tight_layout()
                pdf.savefig(fig_risk)
                plt.close(fig_risk)

        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"Error generating PDF report: {e}")
        # Print detailed traceback for debugging if needed
        import traceback
        st.error(traceback.format_exc()) 
        return None


# Add PDF export button
pdf_buffer = create_pdf_summary()
if pdf_buffer:
    st.download_button(
        label="Download Summary Report (PDF)",
        data=pdf_buffer,
        file_name="dorrigo_property_summary_report.pdf",
        mime="application/pdf",
    )

# Save/Load Configuration (Updated to include new/renamed keys)
st.markdown("<hr class='divider'>", unsafe_allow_html=True)
st.markdown("<h2 class='sub-header'>Save/Load Scenario Configuration</h2>", unsafe_allow_html=True)

# Function to save configuration
def save_config():
    config = {
        "property_price": property_price,
        "current_home_value": current_home_value,
        "other_upfront_costs": other_upfront_costs,
        "use_equity": use_equity,
        "equity_percentage": equity_percentage if use_equity else None,
        "deposit_amount": additional_deposit if use_equity else None, # Renamed key used here
        "deposit_percentage": deposit_percentage_input if not use_equity else None,
        # Note: loan_amount is now complex due to LMI capitalization
        # Better to save the inputs that *lead* to loan amount, rather than the final amount itself.
        # We will recalculate LMI and loan amount on load based on settings.
        "capitalize_lmi_setting": capitalize_lmi if initial_lvr > 80 else False, # Save user's choice if LMI was relevant
        "interest_rate": interest_rate,
        "loan_term": loan_term,
        "combined_fortnightly_income": combined_fortnightly_income,
        "include_rental": include_rental,
        "weekly_rental": weekly_rental if include_rental else 0,
        "occupancy_rate": occupancy_rate if include_rental else 0,
        "include_agistment": include_agistment,
        "num_cattle": num_cattle if include_agistment else 0,
        "agistment_rate": agistment_rate if include_agistment else 0,
        "fortnightly_living_expenses": fortnightly_living_expenses,
        "num_children_boarding": num_children_boarding,
        "annual_boarding_fee_per_child": annual_boarding_fee_per_child,
        "annual_council_rates": annual_council_rates,
        "annual_insurance": annual_insurance,
        "annual_maintenance": annual_maintenance,
        "annual_agistment_costs": annual_agistment_costs if include_agistment else 0,
        "annual_additional_property_expenses": annual_additional_property_expenses,
        "inflation_rate": inflation_rate,
        "property_growth_rate": property_growth_rate,
        "income_growth_rate": income_growth_rate,
        "rental_growth_rate": rental_growth_rate,
        "projection_years": projection_years,
        "risk_analysis": risk_analysis
    }
    # Clean None values for JSON compatibility if needed, though json.dumps handles None
    return json.dumps(config, indent=4) # Use indent for readability

# Function to load configuration
def load_config(config_data):
    """Load configuration from JSON dictionary"""
    # Use st.session_state to set widget defaults for the *next* rerun
    for key, value in config_data.items():
         if key == "deposit_amount" and config_data.get("use_equity"): # Handle renamed key
             st.session_state["deposit_amount"] = value 
         elif key == "deposit_percentage" and not config_data.get("use_equity"):
             st.session_state["deposit_percentage"] = value
         elif key == "capitalize_lmi_setting": # Special handling for LMI preference
              st.session_state["capitalize_lmi"] = value # Set the checkbox state directly
         elif key in st.session_state: # Check if key corresponds to a widget key
             if value is not None:
                 st.session_state[key] = value
         else: # If key isn't directly in session_state, try to set it anyway
              if value is not None:
                  st.session_state[key] = value

    # We don't explicitly set loan_amount here; it will be recalculated
    # on rerun based on the loaded deposit/equity/LMI settings.
    st.success("Configuration loaded. Rerunning...")

col1, col2 = st.columns(2)
with col1:
    config_json_str = save_config()
    st.download_button(
        label="Save Current Configuration (.json)",
        data=config_json_str,
        file_name="dorrigo_property_config.json",
        mime="application/json",
    )

with col2:
    uploaded_file = st.file_uploader("Load Configuration (.json)", type=["json"])
    if uploaded_file is not None:
        try:
            config_data = json.load(uploaded_file)
            # Use a button to trigger the load and rerun
            if st.button("Apply Loaded Configuration"):
                 load_config(config_data)
                 st.experimental_rerun() # Trigger rerun to apply loaded state
        except json.JSONDecodeError:
            st.error("Invalid JSON file.")
        except Exception as e:
            st.error(f"Failed to load configuration: {e}")


# Add footer
st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
st.markdown("<div class='footer'>Dorrigo Rural Property Financial Simulator © 2024 | Disclaimer: Estimates only. Consult financial professionals.</div>", unsafe_allow_html=True)

# --- END OF FILE DorrigoSimClaude/app.py ---