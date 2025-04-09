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
import math # Needed for ceiling and floor functions

# Set page config
st.set_page_config(
    page_title="Rural Property Financial Simulator - Dorrigo NSW",
    page_icon="🏡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom CSS
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

# Header
st.markdown("<h1 class='main-header'>Rural Property Financial Simulator</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 1.2rem;'>For Dorrigo, NSW Property Purchase Analysis</p>", unsafe_allow_html=True)

# --- Helper Functions ---

def calculate_nsw_stamp_duty(property_value):
    """Calculates approximate NSW Transfer Duty based on value."""
    # Rates as of late 2023/early 2024 - check Revenue NSW for current rates
    if property_value <= 0: return 0 # Handle zero or negative input

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
        return 0, 0 # Avoid division by zero

    lvr = (loan_amount / property_price) * 100 if property_price > 0 else 0
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
    try:
        monthly_payment = loan_amount * (monthly_interest_rate * (1 + monthly_interest_rate)**num_payments) / ((1 + monthly_interest_rate)**num_payments - 1)
    except OverflowError: # Handle potential overflow for very high rates/terms
        st.warning("Calculation overflow encountered for mortgage payment - check inputs.")
        return 0
    return monthly_payment

def calculate_loan_balance_over_time(loan_amount, annual_interest_rate, monthly_payment, loan_term_years):
    """Calculate the loan balance over time."""
    if loan_amount <= 0 or loan_term_years <= 0:
         return [0] * (loan_term_years * 12 + 1)

    # Handle zero payment case (e.g., interest only or error)
    if monthly_payment <= 0:
        if annual_interest_rate > 0: # If interest accrues but no payment, balance grows (simplified)
             st.warning("Monthly payment is zero or negative. Loan balance calculation assumes interest accrues but principal doesn't decrease.")
             monthly_rate = annual_interest_rate / 100 / 12
             balances = [loan_amount]
             for _ in range(loan_term_years * 12):
                  balances.append(balances[-1] * (1 + monthly_rate))
             return balances
        else: # No interest, no payment, balance stays same
             return [loan_amount] * (loan_term_years * 12 + 1)

    monthly_interest_rate = annual_interest_rate / 100 / 12
    num_payments = loan_term_years * 12
    loan_balance = [loan_amount]
    current_balance = loan_amount

    for i in range(1, num_payments + 1):
        interest = max(0, current_balance * monthly_interest_rate) # Ensure non-negative interest
        # Ensure payment doesn't exceed balance + interest
        actual_payment = min(monthly_payment, current_balance + interest) if current_balance > 0 else 0
        principal = max(0, actual_payment - interest) # Ensure non-negative principal payment
        current_balance -= principal
        # Ensure balance doesn't go below zero
        current_balance = max(0, current_balance)
        loan_balance.append(current_balance)
        # Optimization: if balance hits zero, stop early and pad
        if current_balance == 0:
            loan_balance.extend([0] * (num_payments - i))
            break

    return loan_balance

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
    monthly_rate = annual_interest_rate / 100 / 12 if annual_interest_rate > 0 else 0

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


def project_income_expenses(
    # Base annual values (Year 0)
    annual_employment_income, annual_rental_income, annual_agistment_income,
    annual_living_expenses, annual_boarding_expenses, # Base boarding/education cost
    annual_council_rates, annual_insurance, annual_maintenance,
    annual_agistment_costs, annual_additional_property_expenses,
    # Loan data & projection settings
    loan_data_df, projection_years,
    # Growth rates
    income_growth_rate, inflation_rate, rental_growth_rate,
    # --- EVENT PARAMETERS ---
    num_children_boarding, # Need number of children here
    include_super_events, user_retire_year, user_super_amount, wife_retire_year, wife_super_amount,
    include_education_change, years_until_edu_change, new_annual_edu_cost_per_child, duration_of_new_cost
    ):
    """
    Project income and expenses over time, incorporating retirement and education cost changes.
    """
    years = list(range(projection_years + 1))
    df = pd.DataFrame({'Year': years})

    # --- Pre-calculate event timing ---
    # Education change timing (change occurs *after* this year)
    edu_change_ends_after_year = math.floor(years_until_edu_change)
    # New education cost starts in the year *following* edu_change_ends_after_year
    new_edu_cost_start_year = edu_change_ends_after_year + 1
    new_edu_cost_end_year = new_edu_cost_start_year + duration_of_new_cost - 1 # Inclusive end year


    # --- Loop through each projection year ---
    projected_employment = []
    projected_rental = []
    projected_agistment = []
    projected_lump_sums = []
    projected_living = []
    projected_education = []
    projected_rates = []
    projected_insurance = []
    projected_maintenance = []
    projected_agistment_costs = []
    projected_additional_prop = []

    for year in years:
        # --- Calculate Growth Factors ---
        emp_growth = (1 + income_growth_rate / 100) ** year
        rent_growth = (1 + rental_growth_rate / 100) ** year
        inf_growth = (1 + inflation_rate / 100) ** year

        # --- Income Projections for the Year ---
        current_year_employment = annual_employment_income * emp_growth
        current_year_rental = annual_rental_income * rent_growth
        current_year_agistment = annual_agistment_income * inf_growth # Assume grows with inflation
        current_year_lump_sum = 0

        # Apply Retirement Events
        if include_super_events:
            # User retirement - stops employment income AFTER this year
            if year >= user_retire_year:
                current_year_employment = 0
            # User super access - lump sum IN this year
            if year == user_retire_year:
                current_year_lump_sum += user_super_amount
            # Partner retirement (assuming partner income is part of combined employment)
            # NOTE: This assumes combined income stops when the FIRST person retires based on user_retire_year.
            # Partner super access - lump sum IN this year
            if year == wife_retire_year:
                 current_year_lump_sum += wife_super_amount

        # --- Expense Projections for the Year ---
        current_year_living = annual_living_expenses * inf_growth
        current_year_rates = annual_council_rates * inf_growth
        current_year_insurance = annual_insurance * inf_growth
        current_year_maintenance = annual_maintenance * inf_growth
        current_year_agistment_costs = annual_agistment_costs * inf_growth
        current_year_additional_prop = annual_additional_property_expenses * inf_growth

        # Apply Education Cost Logic
        current_year_education = 0
        # Base cost before inflation for the year
        base_cost_no_inflation = annual_boarding_expenses # This is already num_children * fee
        # New cost base before inflation for the year
        new_cost_base_no_inflation = new_annual_edu_cost_per_child * num_children_boarding

        if include_education_change:
             # Before the change period ends
             if year <= edu_change_ends_after_year:
                  current_year_education = base_cost_no_inflation * inf_growth
             # During the new cost period
             elif new_edu_cost_start_year <= year <= new_edu_cost_end_year:
                  current_year_education = new_cost_base_no_inflation * inf_growth
             # After the new cost period ends
             else:
                  current_year_education = 0 # Cost stops
        else:
             # If change not included, just use the base boarding cost projected
             current_year_education = base_cost_no_inflation * inf_growth


        # --- Append annual values to lists ---
        projected_employment.append(current_year_employment)
        projected_rental.append(current_year_rental)
        projected_agistment.append(current_year_agistment)
        projected_lump_sums.append(current_year_lump_sum)
        projected_living.append(current_year_living)
        projected_education.append(current_year_education)
        projected_rates.append(current_year_rates)
        projected_insurance.append(current_year_insurance)
        projected_maintenance.append(current_year_maintenance)
        projected_agistment_costs.append(current_year_agistment_costs)
        projected_additional_prop.append(current_year_additional_prop)

    # --- Populate DataFrame ---
    df['Employment_Income'] = projected_employment
    df['Rental_Income'] = projected_rental
    df['Agistment_Income'] = projected_agistment
    df['Lump_Sum_Income'] = projected_lump_sums
    # Add lump sums to total income
    df['Total_Income'] = df['Employment_Income'] + df['Rental_Income'] + df['Agistment_Income'] + df['Lump_Sum_Income']

    df['Living_Expenses'] = projected_living
    # Use the calculated phased education cost
    df['Education_Expenses'] = projected_education # Renamed from Boarding_Expenses
    df['Council_Rates'] = projected_rates
    df['Insurance'] = projected_insurance
    df['Maintenance'] = projected_maintenance
    df['Agistment_Costs'] = projected_agistment_costs
    df['Additional_Property_Expenses'] = projected_additional_prop

    # Merge mortgage payments from loan_data_df
    df = pd.merge(df, loan_data_df[['Year', 'Annual_Mortgage_Payment']], on='Year', how='left')
    df['Annual_Mortgage_Payment'] = df['Annual_Mortgage_Payment'].fillna(0)

    # Calculate Total Expenses (using the new Education_Expenses column)
    df['Total_Expenses_Excl_Mortgage'] = (df['Living_Expenses'] + df['Education_Expenses'] + df['Council_Rates'] +
                                        df['Insurance'] + df['Maintenance'] + df['Agistment_Costs'] +
                                        df['Additional_Property_Expenses'])
    df['Total_Expenses'] = df['Total_Expenses_Excl_Mortgage'] + df['Annual_Mortgage_Payment']

    # Calculate net cashflow
    df['Net_Cashflow'] = df['Total_Income'] - df['Total_Expenses']
    # Set Year 0 Net Cashflow to 0 (it's the starting point before income/expenses occur)
    df.loc[df['Year'] == 0, 'Net_Cashflow'] = 0
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
        # Use session state to remember choice across reruns if loading config
        if 'capitalize_lmi' not in st.session_state:
             st.session_state.capitalize_lmi = True # Default to capitalizing
        capitalize_lmi = st.checkbox("Add LMI to Loan Amount?", value=st.session_state.capitalize_lmi, key="capitalize_lmi")

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
        # Ensure capitalize_lmi state reflects reality if LVR drops below 80
        st.session_state.capitalize_lmi = False # Update session state if LMI becomes irrelevant
        capitalize_lmi = False

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

    num_children_boarding = st.number_input("Number of Children (for Education Costs)", min_value=0, max_value=10, value=1, step=1, key="num_children_boarding")
    annual_boarding_fee_per_child = st.number_input("Initial Annual Education Fee per Child (AUD$)", min_value=0, max_value=100000, value=50000, step=1000, format="%d", key="annual_boarding_fee_per_child", help="e.g., Boarding school fee")
    # This is the BASE education cost before phasing/inflation
    annual_boarding_expenses = num_children_boarding * annual_boarding_fee_per_child
    st.write(f"Initial Annual Education: ${annual_boarding_expenses:,.2f}")

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


# --- NEW: Future Financial Events ---
st.sidebar.markdown("## Future Financial Events")
# Placeholder for projection_years if not defined yet
proj_years_default = st.session_state.get('loan_term', 25) # Default based on loan term default

# Retirement & Superannuation Events
with st.sidebar.expander("Retirement & Super Access", expanded=False):
    include_super_events = st.checkbox("Include Retirement/Super Events?", value=True, key="include_super_events")
    if include_super_events:
        user_retire_year = st.number_input("Your Retirement Year (Years from now)", min_value=0, max_value=proj_years_default, value=7, step=1, key="user_retire_year")
        user_super_amount = st.number_input("Your Est. Super Access Amount (AUD$)", min_value=0, max_value=2000000, value=700000, step=10000, format="%d", key="user_super_amount")
        wife_retire_year = st.number_input("Partner's Retirement Year (Years from now)", min_value=0, max_value=proj_years_default, value=10, step=1, key="wife_retire_year")
        wife_super_amount = st.number_input("Partner's Est. Super Access Amount (AUD$)", min_value=0, max_value=2000000, value=600000, step=10000, format="%d", key="wife_super_amount")
        use_your_super_payoff = st.checkbox("Use Your Super Access Amount to Pay Off Mortgage?", value=True, key="use_your_super_payoff")
    else:
        # Set defaults if checkbox is off to avoid errors later
        user_retire_year = proj_years_default + 1 # Effectively disable
        user_super_amount = 0
        wife_retire_year = proj_years_default + 1 # Effectively disable
        wife_super_amount = 0
        use_your_super_payoff = False # Ensure default is False if parent checkbox is off

# Future Education Costs
with st.sidebar.expander("Future Education Costs", expanded=False):
    include_education_change = st.checkbox("Include Phased Education Costs?", value=True, key="include_education_change")
    if include_education_change:
        st.info("Current 'Initial Education Fee' applies until the change point.")
        years_until_edu_change = st.number_input("Years Until Education Cost Change", min_value=0.0, max_value=float(proj_years_default), value=3.5, step=0.5, key="years_until_edu_change")
        new_annual_edu_cost_per_child = st.number_input("New Annual Education Cost per Child After Change (AUD$)", min_value=0, max_value=100000, value=15000, step=1000, format="%d", key="new_annual_edu_cost_per_child", help="e.g., University support. Enter 0 if support stops.")
        duration_of_new_cost = st.number_input("Duration of New Education Cost (Years)", min_value=0, max_value=proj_years_default, value=4, step=1, key="duration_of_new_cost", help="How many years does the new cost apply?")
    else:
        # Set defaults if checkbox is off
        years_until_edu_change = proj_years_default + 1 # Effectively disable change
        new_annual_edu_cost_per_child = 0
        duration_of_new_cost = 0

# Advanced Settings
with st.sidebar.expander("Advanced Settings & Projections", expanded=False):
    inflation_rate = st.slider("Annual Inflation Rate (Expenses Growth) (%)", min_value=0.0, max_value=10.0, value=2.5, step=0.1, key="inflation_rate")
    property_growth_rate = st.slider("Annual Property Value Growth Rate (%)", min_value=-5.0, max_value=10.0, value=4.0, step=0.1, key="property_growth_rate") # Allow negative growth
    income_growth_rate = st.slider("Annual Employment Income Growth Rate (%)", min_value=0.0, max_value=10.0, value=3.0, step=0.1, key="income_growth_rate")
    rental_growth_rate = st.slider("Annual Rental Income Growth Rate (%)", min_value=0.0, max_value=10.0, value=3.5, step=0.1, key="rental_growth_rate")
    # Update projection_years default and max value dynamically based on input events if needed
    max_event_year = 0
    if include_super_events:
         max_event_year = max(user_retire_year, wife_retire_year)
    if include_education_change:
         max_event_year = max(max_event_year, math.ceil(years_until_edu_change + duration_of_new_cost))

    # Default projection to loan term or max event year, whichever is longer
    proj_years_default_final = max(loan_term, max_event_year, 10) # Ensure at least 10 years
    projection_years = st.slider("Projection Years", min_value=1, max_value=40, value=int(proj_years_default_final), step=1, key="projection_years") # Default to relevant term
    risk_analysis = st.checkbox("Include Risk Analysis Section", value=True, key="risk_analysis")


# --- Main Calculation Section ---

# Calculate Stamp Duty
stamp_duty = calculate_nsw_stamp_duty(property_price)

# Calculate total upfront funds needed
# Deposit needed = Property Price - Final Loan Amount
actual_deposit_paid = max(0, property_price - loan_amount_final)
funds_needed_for_deposit_and_costs = actual_deposit_paid + stamp_duty + lmi_payable + other_upfront_costs

# Calculate monthly mortgage payment using final loan amount
monthly_mortgage_payment = calculate_monthly_mortgage_payment(loan_amount_final, interest_rate, loan_term)

# Calculate loan balance over time
loan_balance = calculate_loan_balance_over_time(loan_amount_final, interest_rate, monthly_mortgage_payment, loan_term)

# Calculate annual loan data matching projection years
loan_data = calculate_annual_totals(loan_balance, monthly_mortgage_payment, loan_term, projection_years, interest_rate)

# Project income and expenses - includes event logic
projection_data = project_income_expenses(
    # Base annual values
    annual_employment_income, annual_rental_income, annual_agistment_income,
    annual_living_expenses, annual_boarding_expenses, # Pass base education cost
    annual_council_rates, annual_insurance, annual_maintenance,
    annual_agistment_costs, annual_additional_property_expenses,
    # Loan data & projection settings
    loan_data, projection_years,
    # Growth rates
    income_growth_rate, inflation_rate, rental_growth_rate,
    # --- EVENT PARAMETERS PASSED ---
    num_children_boarding, # Pass number of children
    include_super_events, user_retire_year, user_super_amount, wife_retire_year, wife_super_amount,
    include_education_change, years_until_edu_change, new_annual_edu_cost_per_child, duration_of_new_cost
)


# Merge loan balance into projection data
merged_data = pd.merge(projection_data, loan_data[['Year', 'Loan_Balance']], on='Year', how='left')

# --- START: Mortgage Payoff Logic ---
payoff_applied_info = "" # For potential display later
if include_super_events and use_your_super_payoff:
    # Check if the retirement year is within the projection period
    if user_retire_year <= projection_years and not merged_data[merged_data['Year'] == user_retire_year].empty:

        # Get loan balance just BEFORE the super is received (end of previous year or start of current)
        # Using balance at the end of the specified year seems most intuitive for payoff decision
        loan_balance_at_payoff_year = merged_data.loc[merged_data['Year'] == user_retire_year, 'Loan_Balance'].iloc[0]

        # Get the super amount for payoff
        super_lump_sum_for_payoff = user_super_amount # Assuming we use the full specified amount

        # Calculate how much is actually used for payoff
        amount_paid_off = min(super_lump_sum_for_payoff, loan_balance_at_payoff_year)

        # Calculate the new loan balance after payoff
        new_loan_balance_after_payoff = max(0, loan_balance_at_payoff_year - amount_paid_off)

        if amount_paid_off > 0:
            payoff_applied_info = f"Mortgage payoff applied in Year {user_retire_year}. Amount: ${amount_paid_off:,.0f}. New Balance: ${new_loan_balance_after_payoff:,.0f}."
            st.sidebar.success(payoff_applied_info) # Show message in sidebar

            # Update the DataFrame for the payoff year and all subsequent years
            payoff_mask = merged_data['Year'] >= user_retire_year
            merged_data.loc[payoff_mask, 'Loan_Balance'] = new_loan_balance_after_payoff
            merged_data.loc[payoff_mask, 'Annual_Mortgage_Payment'] = 0 # No more payments after payoff

            # Recalculate cumulative cashflow because expenses changed from payoff year onwards
            # Recalculate net cashflow first based on zero mortgage payments
            merged_data.loc[payoff_mask, 'Total_Expenses'] = merged_data['Total_Expenses_Excl_Mortgage'] # Remove mortgage payment
            merged_data.loc[payoff_mask, 'Net_Cashflow'] = merged_data['Total_Income'] - merged_data['Total_Expenses']
            # Now recalculate cumulative sum from scratch
            merged_data['Cumulative_Cashflow'] = merged_data['Net_Cashflow'].cumsum()


# --- END: Mortgage Payoff Logic ---

# Calculate property value and LVR over time
merged_data['Property_Value'] = [property_price * ((1 + property_growth_rate/100) ** year) for year in merged_data['Year']]
# Recalculate Equity based on potentially adjusted loan balance
merged_data['Equity'] = merged_data['Property_Value'] - merged_data['Loan_Balance']
# Avoid division by zero if property value becomes zero or negative (unlikely but safe)
merged_data['LVR_Percent'] = (merged_data['Loan_Balance'] / merged_data['Property_Value'].replace(0, np.nan)) * 100
merged_data['LVR_Percent'] = merged_data['LVR_Percent'].fillna(0).clip(lower=0) # Handle NaN and ensure non-negative


# --- Main Content Area - Results ---

# Upfront Costs Summary
st.markdown("<div class='upfront-summary'>", unsafe_allow_html=True)
st.markdown("### Upfront Funds Required & Summary")
col1_upfront, col2_upfront = st.columns(2)
with col1_upfront:
    st.metric("Property Price", f"${property_price:,.0f}")
    st.metric("Stamp Duty (NSW Est.)", f"${stamp_duty:,.0f}")
    st.metric("LMI (Payable Upfront)", f"${lmi_payable:,.0f}")
    st.metric("Other Upfront Costs", f"${other_upfront_costs:,.0f}")
with col2_upfront:
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
col1_yr1, col2_yr1, col3_yr1 = st.columns(3)

# Check if projection_data has at least Year 1 (index 1)
idx_yr1 = 1 if len(merged_data) > 1 else 0 # Use index 1 if possible, else 0

# Total income (Year 1 - from merged_data row idx_yr1)
total_income_yr1 = merged_data.loc[idx_yr1, 'Total_Income']
with col1_yr1:
    st.markdown(f"### Total Annual Income (Yr 1)")
    st.markdown(f"<h3 class='positive'>${total_income_yr1:,.2f}</h3>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"Employment: ${merged_data.loc[idx_yr1, 'Employment_Income']:,.2f}")
    if include_rental:
        st.markdown(f"Rental: ${merged_data.loc[idx_yr1, 'Rental_Income']:,.2f}")
    if include_agistment:
        st.markdown(f"Agistment: ${merged_data.loc[idx_yr1, 'Agistment_Income']:,.2f}")
    if merged_data.loc[idx_yr1, 'Lump_Sum_Income'] > 0:
         st.markdown(f"Lump Sums: ${merged_data.loc[idx_yr1, 'Lump_Sum_Income']:,.2f}")


# Total expenses (Year 1 - from merged_data row idx_yr1)
total_expenses_yr1 = merged_data.loc[idx_yr1, 'Total_Expenses']
annual_mortgage_payment_yr1 = merged_data.loc[idx_yr1, 'Annual_Mortgage_Payment']
prop_running_costs_yr1 = merged_data.loc[idx_yr1, ['Council_Rates', 'Insurance', 'Maintenance', 'Agistment_Costs', 'Additional_Property_Expenses']].sum()
living_expenses_yr1 = merged_data.loc[idx_yr1, 'Living_Expenses']
education_expenses_yr1 = merged_data.loc[idx_yr1, 'Education_Expenses'] # Changed from boarding

with col2_yr1:
    st.markdown(f"### Total Annual Expenses (Yr 1)")
    st.markdown(f"<h3 class='negative'>${total_expenses_yr1:,.2f}</h3>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"Mortgage: ${annual_mortgage_payment_yr1:,.2f}")
    st.markdown(f"Living: ${living_expenses_yr1:,.2f}")
    st.markdown(f"Education: ${education_expenses_yr1:,.2f}") # Changed label
    st.markdown(f"Property Running: ${prop_running_costs_yr1:,.2f}")


# Net position (Year 1)
net_position_yr1 = total_income_yr1 - total_expenses_yr1
with col3_yr1:
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

col1_be, col2_be = st.columns(2)

with col1_be:
    # Break-even status
    if net_position_yr1 >= 0:
        st.markdown("<div class='highlight'>Scenario starts <span class='positive'>cash-flow positive</span> in Year 1.</div>", unsafe_allow_html=True)
    elif break_even_year is not None and break_even_year <= projection_years:
        st.markdown(f"<div class='highlight'>Scenario cumulative cash flow becomes <span class='positive'>positive</span> around Year {break_even_year}.</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='warning'>Scenario cumulative cash flow does not become positive within the {projection_years}-year projection period.</div>", unsafe_allow_html=True)

with col2_be:
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
fig_cashflow.add_trace(go.Bar(x=merged_data['Year'], y=merged_data['Total_Income'], name='Total Income (incl. Lump Sums)', marker_color='#1E5631'))
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
col1_pie, col2_pie = st.columns(2)

with col1_pie:
    # Income breakdown Yr 1
    income_data_yr1 = {
        'Category': ['Employment', 'Rental', 'Agistment', 'Lump Sums'],
        'Amount': [
            merged_data.loc[idx_yr1, 'Employment_Income'],
            merged_data.loc[idx_yr1, 'Rental_Income'],
            merged_data.loc[idx_yr1, 'Agistment_Income'],
            merged_data.loc[idx_yr1, 'Lump_Sum_Income']
            ]
    }
    income_df_yr1 = pd.DataFrame(income_data_yr1)
    income_df_yr1 = income_df_yr1[income_df_yr1['Amount'] > 0.01] # Filter small/zero amounts

    if not income_df_yr1.empty:
        fig_income = px.pie(income_df_yr1, values='Amount', names='Category', title='Income Sources (Year 1)', color_discrete_sequence=px.colors.sequential.Greens_r)
        fig_income.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_income, use_container_width=True)
    else:
        st.info("No significant income sources in Year 1.")

with col2_pie:
    # Expense breakdown Yr 1
    expense_data_yr1 = {
        'Category': ['Mortgage', 'Living', 'Education', 'Prop. Running Costs'], # Updated label
        'Amount': [
            merged_data.loc[idx_yr1, 'Annual_Mortgage_Payment'],
            merged_data.loc[idx_yr1, 'Living_Expenses'],
            merged_data.loc[idx_yr1, 'Education_Expenses'], # Use new column name
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
    base_annual_rental_income_yr1 = merged_data.loc[idx_yr1, 'Rental_Income']
    base_annual_agistment_income_yr1 = merged_data.loc[idx_yr1, 'Agistment_Income']
    base_annual_employment_income_yr1 = merged_data.loc[idx_yr1, 'Employment_Income']
    # Get Year 1 base expenses (excluding mortgage)
    base_expenses_excl_mortgage_yr1 = living_expenses_yr1 + education_expenses_yr1 + prop_running_costs_yr1


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
        "Stress Test (Vacant 50%, Low Agist 50%, Rate +2%)": {
            "occupancy_factor": 0.5, # e.g., 50% vacancy
            "agistment_factor": 0.5, # e.g., 50% capacity/rate
            "interest_rate_increase": 2.0
        }
    }

    # Calculate cashflow for each scenario in Year 1
    scenario_results = []

    for scenario_name, params in risk_scenarios.items():
        # Adjust income (using Year 1 base values)
        scen_rental_income = base_annual_rental_income_yr1 * params["occupancy_factor"]
        scen_agistment_income = base_annual_agistment_income_yr1 * params["agistment_factor"]
        # Assume employment and lump sums (0 in Yr 1) are unaffected by these specific risks
        scen_total_income = base_annual_employment_income_yr1 + scen_rental_income + scen_agistment_income

        # Adjust mortgage
        scen_interest_rate = interest_rate + params["interest_rate_increase"]
        # For simplicity, assume LMI decision (capitalized or not) is fixed from base case
        scen_loan_amount = loan_amount_final # Use the final loan amount decided earlier

        scen_monthly_payment = calculate_monthly_mortgage_payment(scen_loan_amount, scen_interest_rate, loan_term)
        scen_annual_mortgage = scen_monthly_payment * 12

        # Calculate total expenses for scenario (using Yr 1 base non-mortgage costs)
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

    # --- Add Dynamic Y-Axis Range ---
    if not risk_df.empty:
        min_val = risk_df["Annual Net Position (Year 1)"].min()
        max_val = risk_df["Annual Net Position (Year 1)"].max()
        data_range = max_val - min_val
        if data_range == 0:
             padding = abs(max_val * 0.1) if max_val != 0 else 1000
        else:
             padding = data_range * 0.10 # 10% padding

        yaxis_min = min_val - padding
        yaxis_max = max_val + padding
        if min_val >= 0: yaxis_min = min(0, yaxis_min)
        if max_val <= 0: yaxis_max = max(0, yaxis_max)
        fig_risk.update_layout(yaxis_range=[yaxis_min, yaxis_max])
    # --- End Dynamic Y-Axis Range ---

    fig_risk.update_layout(height=500, xaxis={'categoryorder':'array', 'categoryarray': risk_df["Scenario"]}) # Keep order
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
    # Find the stress test row more reliably
    stress_test_row = risk_df[risk_df['Scenario'].str.contains("Stress Test", case=False, na=False)]
    worst_case_yr1 = stress_test_row["Annual Net Position (Year 1)"].iloc[0] if not stress_test_row.empty else base_case_yr1 # Default to base if not found

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
        'Year', 'Total_Income', 'Lump_Sum_Income', 'Total_Expenses', 'Net_Cashflow', 'Cumulative_Cashflow', # Added Lump_Sum_Income
        'Loan_Balance', 'Property_Value', 'Equity', 'LVR_Percent', 'Annual_Mortgage_Payment',
        'Employment_Income', 'Rental_Income', 'Agistment_Income',
        'Living_Expenses', 'Education_Expenses', 'Council_Rates', 'Insurance', 'Maintenance', 'Agistment_Costs' # Changed Boarding_Expenses
    ]
    # Ensure all columns exist before selecting
    cols_to_display = [col for col in cols_to_display if col in display_data.columns]
    display_data = display_data[cols_to_display]

    # Formatting numerical columns
    for col in display_data.columns:
        if col == 'Year':
            continue
        elif col == 'LVR_Percent':
             display_data[col] = display_data[col].map("{:.2f}%".format)
        elif display_data[col].dtype in ['float64', 'int64', 'float32', 'int32']:
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
            # Add event summary if enabled
            event_summary = "\nFuture Events Included:"
            has_events = False
            if include_super_events:
                 event_summary += f"\n  - Your Retirement: Year {user_retire_year} (${user_super_amount:,.0f})"
                 event_summary += f"\n  - Partner Retirement: Year {wife_retire_year} (${wife_super_amount:,.0f})"
                 has_events = True
            if include_education_change:
                 event_summary += f"\n  - Education Cost Change: Year {years_until_edu_change:.1f}"
                 event_summary += f" to ${new_annual_edu_cost_per_child:,.0f}/child for {duration_of_new_cost} years"
                 has_events = True

            if has_events:
                 summary_text += event_summary


            plt.figtext(0.1, 0.88, summary_text, fontsize=9, va='top', wrap=True) # Reduced font size, increased y
            plt.figtext(0.5, 0.05, f"Generated on {datetime.now().strftime('%Y-%m-%d')}", fontsize=8, ha='center')
            plt.axis('off')
            pdf.savefig(fig)
            plt.close(fig)

            # --- Page 2: Cash Flow Projection ---
            fig_cf, ax_cf = plt.subplots(figsize=(8.5, 5.5)) # Adjusted size
            years = merged_data['Year'].values
            bar_width = 0.35
            ax_cf.bar(years - bar_width/2, merged_data['Total_Income'], width=bar_width, label='Income (incl. Lump Sums)', color='#1E5631', alpha=0.7)
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
            fig_loan_pdf, ax1_pdf = plt.subplots(figsize=(8.5, 5.5)) # Adjusted size, new variable names
            ax1_pdf.plot(years, merged_data['Loan_Balance'], 'o-', label='Loan Balance', color='#8C4646', markersize=4)
            ax1_pdf.plot(years, merged_data['Property_Value'], 'o--', label='Est. Property Value', color='#376D37', markersize=4)
            ax1_pdf.plot(years, merged_data['Equity'], 'o-', label='Est. Equity', color='#365F91', markersize=4)
            ax1_pdf.set_xlabel('Year')
            ax1_pdf.set_ylabel('Amount (AUD$)', color='black')
            ax1_pdf.tick_params(axis='y', labelcolor='black')
            ax1_pdf.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'${x:,.0f}'))
            ax1_pdf.grid(True, linestyle='--', alpha=0.6)

            # Secondary axis for LVR
            ax2_pdf = ax1_pdf.twinx()
            ax2_pdf.plot(years, merged_data['LVR_Percent'], 'o:', label='LVR (%)', color='#FFA500', markersize=4)
            ax2_pdf.set_ylabel('LVR (%)', color='#FFA500')
            ax2_pdf.tick_params(axis='y', labelcolor='#FFA500')
            ax2_pdf.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.0f}%'))
            ax2_pdf.set_ylim(0, 105) # LVR Axis limit 0-105%

            # Combine legends
            lines, labels = ax1_pdf.get_legend_handles_labels()
            lines2, labels2 = ax2_pdf.get_legend_handles_labels()
            ax2_pdf.legend(lines + lines2, labels + labels2, loc='best', fontsize=8)

            ax1_pdf.set_title('Loan Balance, Property Value, Equity, and LVR Over Time')
            plt.tight_layout()
            pdf.savefig(fig_loan_pdf) # Use unique figure name
            plt.close(fig_loan_pdf) # Close unique figure name

            # --- Page 4: Risk Analysis (if enabled) ---
            if risk_analysis and not risk_df.empty:
                fig_risk_pdf, ax_risk_pdf = plt.subplots(figsize=(8.5, 5.5)) # Adjusted size, unique names
                scenarios = risk_df["Scenario"]
                net_positions_yr1 = risk_df["Annual Net Position (Year 1)"]
                colors = ['#1E5631' if pos >= 0 else '#CA3433' for pos in net_positions_yr1]

                bars = ax_risk_pdf.bar(scenarios, net_positions_yr1, color=colors, alpha=0.8)
                ax_risk_pdf.axhline(0, color='grey', linewidth=0.8) # Zero line

                # Calculate dynamic y-range for PDF too
                min_val_risk = risk_df["Annual Net Position (Year 1)"].min()
                max_val_risk = risk_df["Annual Net Position (Year 1)"].max()
                risk_range = max_val_risk - min_val_risk
                padding_risk = risk_range * 0.1 if risk_range != 0 else abs(max_val_risk * 0.1) if max_val_risk != 0 else 1000
                yrange_min = min(0, min_val_risk) - padding_risk
                yrange_max = max(0, max_val_risk) + padding_risk
                ax_risk_pdf.set_ylim(yrange_min, yrange_max)

                ax_risk_pdf.set_ylabel('Annual Net Position (Year 1, AUD$)')
                ax_risk_pdf.set_title('Risk Analysis - Year 1 Net Position Impact')
                ax_risk_pdf.grid(True, linestyle='--', alpha=0.6, axis='y')
                ax_risk_pdf.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'${x:,.0f}'))
                plt.xticks(rotation=45, ha='right', fontsize=8) # Rotate labels
                plt.tight_layout() # Apply after rotation
                pdf.savefig(fig_risk_pdf) # Use unique figure name
                plt.close(fig_risk_pdf) # Close unique figure name

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

# Save/Load Configuration (Updated to include new event keys)
st.markdown("<hr class='divider'>", unsafe_allow_html=True)
st.markdown("<h2 class='sub-header'>Save/Load Scenario Configuration</h2>", unsafe_allow_html=True)

# Function to save configuration
def save_config():
    config = {
        # Property & Upfront
        "property_price": property_price,
        "current_home_value": current_home_value,
        "other_upfront_costs": other_upfront_costs,
        # Financing
        "use_equity": use_equity,
        "equity_percentage": equity_percentage if use_equity else None,
        "deposit_amount": additional_deposit if use_equity else None, # Original key used here
        "deposit_percentage": deposit_percentage_input if not use_equity else None,
        "capitalize_lmi": capitalize_lmi if initial_lvr > 80 else False, # Save user's choice if LMI was relevant
        "loan_amount": loan_amount_final, # Save the final amount used in calcs
        "interest_rate": interest_rate,
        "loan_term": loan_term,
        # Income
        "combined_fortnightly_income": combined_fortnightly_income,
        "include_rental": include_rental,
        "weekly_rental": weekly_rental if include_rental else 0,
        "occupancy_rate": occupancy_rate if include_rental else 0,
        "include_agistment": include_agistment,
        "num_cattle": num_cattle if include_agistment else 0,
        "agistment_rate": agistment_rate if include_agistment else 0,
        # Expenses
        "fortnightly_living_expenses": fortnightly_living_expenses,
        "num_children_boarding": num_children_boarding,
        "annual_boarding_fee_per_child": annual_boarding_fee_per_child, # Initial fee
        "annual_council_rates": annual_council_rates,
        "annual_insurance": annual_insurance,
        "annual_maintenance": annual_maintenance,
        "annual_agistment_costs": annual_agistment_costs if include_agistment else 0,
        "annual_additional_property_expenses": annual_additional_property_expenses,
        # Future Events
        "include_super_events": include_super_events,
        "user_retire_year": user_retire_year,
        "user_super_amount": user_super_amount,
        "wife_retire_year": wife_retire_year,
        "wife_super_amount": wife_super_amount,
        "use_your_super_payoff": use_your_super_payoff,
        "include_education_change": include_education_change,
        "years_until_edu_change": years_until_edu_change,
        "new_annual_edu_cost_per_child": new_annual_edu_cost_per_child,
        "duration_of_new_cost": duration_of_new_cost,
        # Advanced Settings
        "inflation_rate": inflation_rate,
        "property_growth_rate": property_growth_rate,
        "income_growth_rate": income_growth_rate,
        "rental_growth_rate": rental_growth_rate,
        "projection_years": projection_years,
        "risk_analysis": risk_analysis
    }
    return json.dumps(config, indent=4)

# Function to load configuration
def load_config(config_data):
    """Load configuration from JSON dictionary"""
    st.session_state.update(config_data) # Update session state directly
    st.success("Configuration loaded. Rerunning...")


col1_config, col2_config = st.columns(2)
with col1_config:
    config_json_str = save_config()
    st.download_button(
        label="Save Current Configuration (.json)",
        data=config_json_str,
        file_name="dorrigo_property_config.json",
        mime="application/json",
    )

with col2_config:
    uploaded_file = st.file_uploader("Load Configuration (.json)", type=["json"])
    if uploaded_file is not None:
        try:
            config_data = json.load(uploaded_file)
            # Use a button to trigger the load and rerun
            if st.button("Apply Loaded Configuration"):
                 # Clear existing state slightly differently to ensure overwrite
                 # for key in config_data:
                 #     if key in st.session_state:
                 #          del st.session_state[key] # Remove old value first? Maybe not needed.
                 load_config(config_data)
                 st.experimental_rerun() # Trigger rerun to apply loaded state
        except json.JSONDecodeError:
            st.error("Invalid JSON file.")
        except Exception as e:
            st.error(f"Failed to load configuration: {e}")


# Add footer
st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
st.markdown("<div class='footer'>Dorrigo Rural Property Financial Simulator | Disclaimer: Estimates only. Consult financial professionals.</div>", unsafe_allow_html=True)

# --- END OF FILE DorrigoSimClaude/app.py ---