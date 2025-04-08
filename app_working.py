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
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("<h1 class='main-header'>Rural Property Financial Simulator</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 1.2rem;'>For Dorrigo, NSW Property Purchase Analysis</p>", unsafe_allow_html=True)

# Sidebar for inputs
# Show Dorrigo image or placeholder
try:
    st.sidebar.image("dorrigo.jpg", caption="Dorrigo, NSW", use_column_width=True)
except:
    st.sidebar.image("https://via.placeholder.com/300x100?text=Dorrigo+NSW", use_column_width=True)
st.sidebar.markdown("## Property Parameters")

# Property Information
current_home_value = st.sidebar.number_input("Current Home Value (AUD$)", min_value=500000, max_value=5000000, value=1300000, step=10000, format="%d")
property_price = st.sidebar.slider("Property Price (AUD$)", min_value=1500000, max_value=2000000, value=1700000, step=10000, format="%d")

# Financing Parameters
with st.sidebar.expander("Financing Parameters", expanded=True):
    use_equity = st.checkbox("Use equity from current home?", value=True)
    
    if use_equity:
        equity_percentage = st.slider("Equity Percentage to Use (%)", min_value=0, max_value=100, value=80, step=5)
        equity_amount = current_home_value * (equity_percentage / 100)
        deposit_amount = st.number_input("Additional Deposit (AUD$)", min_value=0, max_value=1000000, value=0, step=10000, format="%d")
        total_deposit = equity_amount + deposit_amount
        
        # Display total deposit info
        st.info(f"Total deposit: ${total_deposit:,.2f} (${equity_amount:,.2f} equity + ${deposit_amount:,.2f} additional)")
    else:
        deposit_percentage = st.slider("Deposit Percentage (%)", min_value=10, max_value=50, value=20, step=5)
        deposit_amount = property_price * (deposit_percentage / 100)
        total_deposit = deposit_amount
        st.info(f"Total deposit: ${total_deposit:,.2f}")
    
    # Calculate loan amount
    loan_amount = max(0, property_price - total_deposit)
    loan_amount = st.number_input("Loan Amount (AUD$)", min_value=0, max_value=2000000, value=int(loan_amount), step=10000, format="%d")
    
    interest_rate = st.slider("Interest Rate (%)", min_value=3.0, max_value=8.0, value=5.0, step=0.1)
    loan_term = st.slider("Loan Term (Years)", min_value=10, max_value=30, value=25, step=5)

# Income Sources
st.sidebar.markdown("## Income Sources")

# Employment Income
with st.sidebar.expander("Employment Income", expanded=True):
    combined_fortnightly_income = st.number_input("Combined Fortnightly After-Tax Income (AUD$)", min_value=0, max_value=20000, value=5000, step=100, format="%d")
    annual_employment_income = combined_fortnightly_income * 26

# Rental Income
with st.sidebar.expander("Rental Income", expanded=True):
    include_rental = st.checkbox("Include Rental Income", value=True)
    if include_rental:
        weekly_rental = st.slider("Weekly Rental Income (AUD$)", min_value=300, max_value=700, value=450, step=10, format="%d")
        occupancy_rate = st.slider("Occupancy Rate (%)", min_value=0, max_value=100, value=90, step=5)
        annual_rental_income = weekly_rental * 52 * (occupancy_rate / 100)
    else:
        annual_rental_income = 0

# Agistment Income
with st.sidebar.expander("Agistment Income", expanded=True):
    include_agistment = st.checkbox("Include Agistment Income", value=True)
    if include_agistment:
        num_cattle = st.slider("Number of Cattle for Agistment", min_value=0, max_value=100, value=20, step=5)
        agistment_rate = st.slider("Agistment Rate (AUD$/head/week)", min_value=4.0, max_value=12.0, value=8.0, step=0.5)
        annual_agistment_income = num_cattle * agistment_rate * 52
    else:
        annual_agistment_income = 0

# Expenses
st.sidebar.markdown("## Expenses")

with st.sidebar.expander("Living Expenses", expanded=True):
    fortnightly_living_expenses = st.number_input("Fortnightly Living Expenses (AUD$)", min_value=0, max_value=10000, value=3000, step=100, format="%d")
    annual_living_expenses = fortnightly_living_expenses * 26
    
    num_children_boarding = st.number_input("Number of Children in Boarding School", min_value=0, max_value=10, value=2, step=1)
    annual_boarding_fee_per_child = st.number_input("Annual Boarding School Fee per Child (AUD$)", min_value=0, max_value=100000, value=30000, step=1000, format="%d")
    annual_boarding_expenses = num_children_boarding * annual_boarding_fee_per_child

with st.sidebar.expander("Property Expenses", expanded=True):
    annual_council_rates = st.number_input("Annual Council Rates (AUD$)", min_value=0, max_value=10000, value=2000, step=100, format="%d")
    annual_insurance = st.number_input("Annual Insurance (AUD$)", min_value=0, max_value=10000, value=1500, step=100, format="%d")
    annual_maintenance = st.number_input("Annual Maintenance (AUD$)", min_value=0, max_value=20000, value=5000, step=500, format="%d")
    
    # Only show if agistment is included
    if include_agistment:
        annual_agistment_costs = st.number_input("Annual Agistment Costs (AUD$)", min_value=0, max_value=20000, value=2000, step=500, format="%d")
    else:
        annual_agistment_costs = 0
    
    # Add additional property-related expenses
    annual_additional_property_expenses = st.number_input("Other Annual Property Expenses (AUD$)", min_value=0, max_value=20000, value=1000, step=500, format="%d")

# Advanced Settings
with st.sidebar.expander("Advanced Settings", expanded=False):
    inflation_rate = st.slider("Annual Inflation Rate (%)", min_value=0.0, max_value=10.0, value=2.5, step=0.1)
    property_growth_rate = st.slider("Annual Property Growth Rate (%)", min_value=0.0, max_value=10.0, value=4.0, step=0.1)
    income_growth_rate = st.slider("Annual Income Growth Rate (%)", min_value=0.0, max_value=10.0, value=3.0, step=0.1)
    rental_growth_rate = st.slider("Annual Rental Growth Rate (%)", min_value=0.0, max_value=10.0, value=3.5, step=0.1)
    projection_years = st.slider("Projection Years", min_value=1, max_value=40, value=10, step=1)
    risk_analysis = st.checkbox("Include Risk Analysis", value=True)

# Helper functions for calculations
def calculate_monthly_mortgage_payment(loan_amount, annual_interest_rate, loan_term_years):
    """Calculate the monthly mortgage payment."""
    if loan_amount <= 0 or annual_interest_rate <= 0:
        return 0
    monthly_interest_rate = annual_interest_rate / 100 / 12
    num_payments = loan_term_years * 12
    monthly_payment = loan_amount * (monthly_interest_rate * (1 + monthly_interest_rate)**num_payments) / ((1 + monthly_interest_rate)**num_payments - 1)
    return monthly_payment

def calculate_loan_balance_over_time(loan_amount, annual_interest_rate, monthly_payment, loan_term_years):
    """Calculate the loan balance over time."""
    monthly_interest_rate = annual_interest_rate / 100 / 12
    num_payments = loan_term_years * 12
    loan_balance = [loan_amount]
    
    for i in range(1, num_payments + 1):
        interest = loan_balance[-1] * monthly_interest_rate
        principal = monthly_payment - interest
        new_balance = loan_balance[-1] - principal
        if new_balance < 0:
            new_balance = 0
        loan_balance.append(new_balance)
    
    return loan_balance

def calculate_annual_totals(loan_balance, monthly_payment, projection_years):
    """Calculate annual loan statistics."""
    annual_balance = loan_balance[0::12]
    annual_payment = monthly_payment * 12
    
    df = pd.DataFrame({
        'Year': range(projection_years + 1),
        'Loan_Balance': annual_balance[:projection_years + 1],
        'Annual_Mortgage_Payment': [annual_payment] * (projection_years + 1)
    })
    
    return df

def project_income_expenses(annual_employment_income, annual_rental_income, annual_agistment_income,
                           annual_living_expenses, annual_boarding_expenses, annual_council_rates,
                           annual_insurance, annual_maintenance, annual_agistment_costs, 
                           annual_additional_property_expenses, mortgage_payment_annual,
                           income_growth_rate, inflation_rate, rental_growth_rate, projection_years):
    """Project income and expenses over time."""
    years = list(range(projection_years + 1))
    
    # Initialize dataframe
    df = pd.DataFrame({'Year': years})
    
    # Project income
    df['Employment_Income'] = [annual_employment_income * ((1 + income_growth_rate/100) ** year) for year in years]
    df['Rental_Income'] = [annual_rental_income * ((1 + rental_growth_rate/100) ** year) for year in years]
    df['Agistment_Income'] = [annual_agistment_income * ((1 + inflation_rate/100) ** year) for year in years]
    df['Total_Income'] = df['Employment_Income'] + df['Rental_Income'] + df['Agistment_Income']
    
    # Project expenses
    df['Living_Expenses'] = [annual_living_expenses * ((1 + inflation_rate/100) ** year) for year in years]
    df['Boarding_Expenses'] = [annual_boarding_expenses * ((1 + inflation_rate/100) ** year) for year in years]
    df['Council_Rates'] = [annual_council_rates * ((1 + inflation_rate/100) ** year) for year in years]
    df['Insurance'] = [annual_insurance * ((1 + inflation_rate/100) ** year) for year in years]
    df['Maintenance'] = [annual_maintenance * ((1 + inflation_rate/100) ** year) for year in years]
    df['Agistment_Costs'] = [annual_agistment_costs * ((1 + inflation_rate/100) ** year) for year in years]
    df['Additional_Property_Expenses'] = [annual_additional_property_expenses * ((1 + inflation_rate/100) ** year) for year in years]
    df['Mortgage_Payment'] = [mortgage_payment_annual] * (projection_years + 1)
    
    df['Total_Expenses'] = (df['Living_Expenses'] + df['Boarding_Expenses'] + df['Council_Rates'] + 
                           df['Insurance'] + df['Maintenance'] + df['Agistment_Costs'] + 
                           df['Additional_Property_Expenses'] + df['Mortgage_Payment'])
    
    # Calculate net cashflow
    df['Net_Cashflow'] = df['Total_Income'] - df['Total_Expenses']
    df['Cumulative_Cashflow'] = df['Net_Cashflow'].cumsum()
    
    return df

# Main calculation section
# Calculate monthly mortgage payment
monthly_mortgage_payment = calculate_monthly_mortgage_payment(loan_amount, interest_rate, loan_term)
annual_mortgage_payment = monthly_mortgage_payment * 12

# Calculate loan balance over time
loan_balance = calculate_loan_balance_over_time(loan_amount, interest_rate, monthly_mortgage_payment, loan_term)
loan_data = calculate_annual_totals(loan_balance, monthly_mortgage_payment, projection_years)

# Project income and expenses
projection_data = project_income_expenses(
    annual_employment_income, annual_rental_income, annual_agistment_income,
    annual_living_expenses, annual_boarding_expenses, annual_council_rates,
    annual_insurance, annual_maintenance, annual_agistment_costs, 
    annual_additional_property_expenses, annual_mortgage_payment,
    income_growth_rate, inflation_rate, rental_growth_rate, projection_years
)

# Merge loan data with projection data
merged_data = pd.merge(projection_data, loan_data, on='Year')

# Main content area - Results section
st.markdown("<h2 class='sub-header'>Financial Summary</h2>", unsafe_allow_html=True)

# Key metrics
col1, col2, col3 = st.columns(3)

# Total income
total_income = annual_employment_income + annual_rental_income + annual_agistment_income
with col1:
    st.markdown(f"### Total Annual Income")
    st.markdown(f"<h3 class='positive'>${total_income:,.2f}</h3>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"Employment: ${annual_employment_income:,.2f}")
    if include_rental:
        st.markdown(f"Rental: ${annual_rental_income:,.2f}")
    if include_agistment:
        st.markdown(f"Agistment: ${annual_agistment_income:,.2f}")

# Total expenses
total_expenses = (annual_living_expenses + annual_boarding_expenses + annual_council_rates +
                 annual_insurance + annual_maintenance + annual_agistment_costs +
                 annual_additional_property_expenses + annual_mortgage_payment)
with col2:
    st.markdown(f"### Total Annual Expenses")
    st.markdown(f"<h3 class='negative'>${total_expenses:,.2f}</h3>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"Mortgage: ${annual_mortgage_payment:,.2f}")
    st.markdown(f"Living: ${annual_living_expenses:,.2f}")
    st.markdown(f"Boarding: ${annual_boarding_expenses:,.2f}")
    st.markdown(f"Property: ${annual_council_rates + annual_insurance + annual_maintenance + annual_agistment_costs + annual_additional_property_expenses:,.2f}")

# Net position
net_position = total_income - total_expenses
with col3:
    st.markdown(f"### Net Annual Position")
    if net_position >= 0:
        st.markdown(f"<h3 class='positive'>+${net_position:,.2f}</h3>", unsafe_allow_html=True)
    else:
        st.markdown(f"<h3 class='negative'>${net_position:,.2f}</h3>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"Monthly: ${net_position/12:,.2f}")
    st.markdown(f"Fortnightly: ${net_position/26:,.2f}")
    st.markdown(f"Weekly: ${net_position/52:,.2f}")

# Break-even analysis
st.markdown("<h2 class='sub-header'>Break-even Analysis</h2>", unsafe_allow_html=True)

# Find break-even year
break_even_year = None
for index, row in merged_data.iterrows():
    if row['Cumulative_Cashflow'] >= 0 and break_even_year is None:
        break_even_year = row['Year']
        break

col1, col2 = st.columns(2)

with col1:
    # Break-even status
    if net_position >= 0:
        st.markdown("<div class='highlight'>Your scenario is <span class='positive'>cash-flow positive</span> from year one.</div>", unsafe_allow_html=True)
    elif break_even_year is not None and break_even_year <= projection_years:
        st.markdown(f"<div class='highlight'>Your scenario becomes <span class='positive'>cash-flow positive</span> in year {break_even_year}.</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='warning'>Your scenario does not become cash-flow positive within the projection period.</div>", unsafe_allow_html=True)

with col2:
    # Key ratios
    debt_to_income = loan_amount / total_income
    expense_to_income = total_expenses / total_income
    mortgage_to_income = annual_mortgage_payment / total_income
    st.markdown(f"**Debt to Income Ratio**: {debt_to_income:.2f}x")
    st.markdown(f"**Expense to Income Ratio**: {expense_to_income:.2f}x")
    st.markdown(f"**Mortgage to Income Ratio**: {mortgage_to_income:.2f}x")

# Cash Flow Visualization
st.markdown("<h2 class='sub-header'>Cash Flow Projection</h2>", unsafe_allow_html=True)

# Cash flow chart
fig = go.Figure()

# Add income
fig.add_trace(go.Bar(
    x=merged_data['Year'],
    y=merged_data['Total_Income'],
    name='Total Income',
    marker_color='#1E5631'
))

# Add expenses
fig.add_trace(go.Bar(
    x=merged_data['Year'],
    y=merged_data['Total_Expenses'],
    name='Total Expenses',
    marker_color='#CA3433'
))

# Add net cashflow
fig.add_trace(go.Scatter(
    x=merged_data['Year'],
    y=merged_data['Net_Cashflow'],
    name='Net Cashflow',
    mode='lines+markers',
    line=dict(color='#365F91', width=3),
    marker=dict(size=8)
))

# Add cumulative cashflow
fig.add_trace(go.Scatter(
    x=merged_data['Year'],
    y=merged_data['Cumulative_Cashflow'],
    name='Cumulative Cashflow',
    mode='lines',
    line=dict(color='#F49130', width=3, dash='dot')
))

# Update layout
fig.update_layout(
    title='Annual Cash Flow Projection',
    xaxis_title='Year',
    yaxis_title='Amount (AUD$)',
    barmode='group',
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    height=500
)

st.plotly_chart(fig, use_container_width=True)

# Loan Amortization Chart
st.markdown("<h2 class='sub-header'>Loan Amortization</h2>", unsafe_allow_html=True)

# Loan balance visualization
fig_loan = go.Figure()

# Add loan balance
fig_loan.add_trace(go.Scatter(
    x=merged_data['Year'],
    y=merged_data['Loan_Balance'],
    name='Loan Balance',
    mode='lines+markers',
    line=dict(color='#8C4646', width=3)
))

# Add property value if growing
property_value_over_time = [property_price * ((1 + property_growth_rate/100) ** year) for year in merged_data['Year']]
fig_loan.add_trace(go.Scatter(
    x=merged_data['Year'],
    y=property_value_over_time,
    name='Property Value',
    mode='lines',
    line=dict(color='#376D37', width=3, dash='dot')
))

# Add equity line
equity_over_time = [property_value - loan_balance for property_value, loan_balance in zip(property_value_over_time, merged_data['Loan_Balance'])]
fig_loan.add_trace(go.Scatter(
    x=merged_data['Year'],
    y=equity_over_time,
    name='Equity',
    mode='lines',
    line=dict(color='#365F91', width=3)
))

# Update layout
fig_loan.update_layout(
    title='Loan Balance and Property Value Over Time',
    xaxis_title='Year',
    yaxis_title='Amount (AUD$)',
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    height=500
)

st.plotly_chart(fig_loan, use_container_width=True)

# Detailed income and expense breakdown
st.markdown("<h2 class='sub-header'>Income & Expense Breakdown (Year 1)</h2>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    # Income breakdown
    income_data = {
        'Category': ['Employment', 'Rental', 'Agistment'],
        'Amount': [annual_employment_income, annual_rental_income, annual_agistment_income]
    }
    income_df = pd.DataFrame(income_data)
    income_df = income_df[income_df['Amount'] > 0]  # Only show categories with income
    
    # Create pie chart for income
    fig_income = px.pie(
        income_df, 
        values='Amount', 
        names='Category',
        title='Income Sources',
        color_discrete_sequence=px.colors.sequential.Greens_r
    )
    fig_income.update_traces(textposition='inside', textinfo='percent+label')
    
    st.plotly_chart(fig_income, use_container_width=True)

with col2:
    # Expense breakdown
    expense_data = {
        'Category': ['Mortgage', 'Living', 'Boarding School', 'Council Rates', 'Insurance', 'Maintenance', 'Agistment Costs', 'Other Property'],
        'Amount': [annual_mortgage_payment, annual_living_expenses, annual_boarding_expenses, annual_council_rates, annual_insurance, annual_maintenance, annual_agistment_costs, annual_additional_property_expenses]
    }
    expense_df = pd.DataFrame(expense_data)
    expense_df = expense_df[expense_df['Amount'] > 0]  # Only show categories with expenses
    
    # Create pie chart for expenses
    fig_expense = px.pie(
        expense_df, 
        values='Amount', 
        names='Category',
        title='Expense Categories',
        color_discrete_sequence=px.colors.sequential.Reds_r
    )
    fig_expense.update_traces(textposition='inside', textinfo='percent+label')
    
    st.plotly_chart(fig_expense, use_container_width=True)

# Risk Analysis
if risk_analysis:
    st.markdown("<h2 class='sub-header'>Risk Analysis</h2>", unsafe_allow_html=True)
    
    # Define risk scenarios
    risk_scenarios = {
        "Base Case": {
            "rental_occupancy": occupancy_rate / 100,
            "agistment_capacity": 1.0,
            "interest_rate_increase": 0.0
        },
        "No Rental Income": {
            "rental_occupancy": 0.0,
            "agistment_capacity": 1.0,
            "interest_rate_increase": 0.0
        },
        "Reduced Agistment (50%)": {
            "rental_occupancy": occupancy_rate / 100,
            "agistment_capacity": 0.5,
            "interest_rate_increase": 0.0
        },
        "Interest Rate +2%": {
            "rental_occupancy": occupancy_rate / 100,
            "agistment_capacity": 1.0,
            "interest_rate_increase": 2.0
        },
        "Worst Case": {
            "rental_occupancy": 0.5,
            "agistment_capacity": 0.5,
            "interest_rate_increase": 2.0
        }
    }
    
    # Calculate cashflow for each scenario
    scenario_results = []
    
    for scenario_name, scenario_params in risk_scenarios.items():
        # Adjust income based on scenario
        scenario_rental_income = annual_rental_income * scenario_params["rental_occupancy"]
        scenario_agistment_income = annual_agistment_income * scenario_params["agistment_capacity"]
        
        # Adjust mortgage payment based on scenario
        scenario_interest_rate = interest_rate + scenario_params["interest_rate_increase"]
        scenario_monthly_payment = calculate_monthly_mortgage_payment(loan_amount, scenario_interest_rate, loan_term)
        scenario_annual_mortgage = scenario_monthly_payment * 12
        
        # Calculate net position
        scenario_total_income = annual_employment_income + scenario_rental_income + scenario_agistment_income
        scenario_total_expenses = (annual_living_expenses + annual_boarding_expenses + annual_council_rates +
                                 annual_insurance + annual_maintenance + annual_agistment_costs +
                                 annual_additional_property_expenses + scenario_annual_mortgage)
        scenario_net_position = scenario_total_income - scenario_total_expenses
        
        # Add to results
        scenario_results.append({
            "Scenario": scenario_name,
            "Annual Net Position": scenario_net_position,
            "Monthly Net Position": scenario_net_position / 12
        })
    
    # Create risk comparison DataFrame
    risk_df = pd.DataFrame(scenario_results)
    
    # Show risk comparison chart
    fig_risk = px.bar(
        risk_df,
        x="Scenario",
        y="Annual Net Position",
        color="Annual Net Position",
        color_continuous_scale=["#CA3433", "#FFCC00", "#1E5631"],
        title="Annual Net Position by Risk Scenario",
        text="Annual Net Position"
    )
    
    fig_risk.update_traces(
        texttemplate='%{text:.2s}', 
        textposition='outside'
    )
    
    fig_risk.update_layout(height=500)
    
    st.plotly_chart(fig_risk, use_container_width=True)
    
    # Risk scenario table
    st.markdown("### Detailed Risk Scenario Analysis")
    
    # Format risk_df for display
    display_risk_df = risk_df.copy()
    display_risk_df["Annual Net Position"] = display_risk_df["Annual Net Position"].map("${:,.2f}".format)
    display_risk_df["Monthly Net Position"] = display_risk_df["Monthly Net Position"].map("${:,.2f}".format)
    
    st.dataframe(display_risk_df, use_container_width=True)
    
    # Add risk analysis interpretation
    st.markdown("### Risk Interpretation")
    
    # Check if base case is positive
    base_case = next(item for item in scenario_results if item["Scenario"] == "Base Case")
    worst_case = next(item for item in scenario_results if item["Scenario"] == "Worst Case")
    
    if base_case["Annual Net Position"] >= 0 and worst_case["Annual Net Position"] >= 0:
        st.markdown("<div class='highlight'>Your financial plan appears <span class='positive'>robust</span>. Even under the worst-case scenario, you maintain a positive cash flow.</div>", unsafe_allow_html=True)
    elif base_case["Annual Net Position"] >= 0 and worst_case["Annual Net Position"] < 0:
        st.markdown("<div class='warning'>Your financial plan is <span class='negative'>vulnerable to stress scenarios</span>. While your base case is positive, you should consider building a larger buffer for unexpected events.</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='warning'>Your financial plan shows <span class='negative'>significant risk</span>. Even in the base case scenario, you have a negative cash flow. Consider revising your plans or increasing your income sources.</div>", unsafe_allow_html=True)

# Detailed projection table
with st.expander("Detailed Projection Table"):
    # Format data for display
    display_data = merged_data.copy()
    for col in display_data.columns:
        if col != 'Year' and not pd.api.types.is_bool_dtype(display_data[col]):
            display_data[col] = display_data[col].map("${:,.2f}".format)
    
    st.dataframe(display_data, use_container_width=True)
    
    # Download button for projection data
    csv = merged_data.to_csv(index=False)
    st.download_button(
        label="Download Projection Data as CSV",
        data=csv,
        file_name="dorrigo_property_projection.csv",
        mime="text/csv",
    )
    
# PDF Export function
def create_pdf_summary():
    """Export a summary report as PDF"""
    try:
        import matplotlib
        matplotlib.use('Agg')
        from matplotlib.backends.backend_pdf import PdfPages
        import matplotlib.pyplot as plt
        from matplotlib.ticker import FuncFormatter
        import io
        
        buffer = io.BytesIO()
        
        with PdfPages(buffer) as pdf:
            # Title page
            fig = plt.figure(figsize=(8.5, 11))
            fig.suptitle('Dorrigo Property Financial Summary', fontsize=24)
            plt.figtext(0.5, 0.8, f"Property Price: ${property_price:,.2f}", fontsize=14, ha='center')
            plt.figtext(0.5, 0.75, f"Loan Amount: ${loan_amount:,.2f}", fontsize=14, ha='center')
            plt.figtext(0.5, 0.7, f"Interest Rate: {interest_rate}%", fontsize=14, ha='center')
            plt.figtext(0.5, 0.65, f"Loan Term: {loan_term} years", fontsize=14, ha='center')
            plt.figtext(0.5, 0.6, f"Annual Income: ${total_income:,.2f}", fontsize=14, ha='center')
            plt.figtext(0.5, 0.55, f"Annual Expenses: ${total_expenses:,.2f}", fontsize=14, ha='center')
            plt.figtext(0.5, 0.5, f"Net Position: ${net_position:,.2f}", fontsize=14, ha='center')
            plt.figtext(0.5, 0.4, f"Generated on {datetime.now().strftime('%Y-%m-%d')}", fontsize=10, ha='center')
            plt.axis('off')
            pdf.savefig()
            plt.close()
            
            # Cash flow chart
            fig, ax = plt.subplots(figsize=(8.5, 6))
            years = merged_data['Year'].values
            ax.bar(years - 0.2, merged_data['Total_Income'], width=0.4, label='Income', color='green', alpha=0.7)
            ax.bar(years + 0.2, merged_data['Total_Expenses'], width=0.4, label='Expenses', color='red', alpha=0.7)
            ax.plot(years, merged_data['Net_Cashflow'], 'bo-', label='Net Cashflow')
            ax.plot(years, merged_data['Cumulative_Cashflow'], 'ko--', label='Cumulative Cashflow')
            ax.set_xlabel('Year')
            ax.set_ylabel('Amount (AUD$)')
            ax.set_title('Cash Flow Projection')
            ax.legend()
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # Format y-axis to show dollar amounts
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'${x:,.0f}'))
            
            pdf.savefig()
            plt.close()
            
            # Loan balance chart
            fig, ax = plt.subplots(figsize=(8.5, 6))
            ax.plot(years, merged_data['Loan_Balance'], 'ro-', label='Loan Balance')
            ax.plot(years, property_value_over_time, 'go-', label='Property Value')
            ax.plot(years, equity_over_time, 'bo-', label='Equity')
            ax.set_xlabel('Year')
            ax.set_ylabel('Amount (AUD$)')
            ax.set_title('Loan Amortization and Property Value')
            ax.legend()
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # Format y-axis to show dollar amounts
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'${x:,.0f}'))
            
            pdf.savefig()
            plt.close()
            
            # Risk analysis chart if enabled
            if risk_analysis:
                fig, ax = plt.subplots(figsize=(8.5, 6))
                scenarios = [item["Scenario"] for item in scenario_results]
                net_positions = [item["Annual Net Position"] for item in scenario_results]
                
                bars = ax.bar(scenarios, net_positions)
                
                # Color bars based on value
                for i, bar in enumerate(bars):
                    if net_positions[i] >= 0:
                        bar.set_color('green')
                        bar.set_alpha(0.7)
                    else:
                        bar.set_color('red')
                        bar.set_alpha(0.7)
                
                ax.set_xlabel('Scenario')
                ax.set_ylabel('Annual Net Position (AUD$)')
                ax.set_title('Risk Analysis')
                ax.grid(True, linestyle='--', alpha=0.7, axis='y')
                
                # Format y-axis to show dollar amounts
                ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'${x:,.0f}'))
                
                # Rotate x-axis labels for readability
                plt.xticks(rotation=45, ha='right')
                
                plt.tight_layout()
                pdf.savefig()
                plt.close()
        
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"Error generating PDF: {e}")
        return None

# Add PDF export button
pdf_buffer = create_pdf_summary()
if pdf_buffer:
    st.download_button(
        label="Download Summary Report (PDF)",
        data=pdf_buffer,
        file_name="dorrigo_property_summary.pdf",
        mime="application/pdf",
    )

# Save/Load Configuration
st.markdown("<hr class='divider'>", unsafe_allow_html=True)
st.markdown("<h2 class='sub-header'>Save/Load Configuration</h2>", unsafe_allow_html=True)

# Function to save configuration
def save_config():
    """Save current configuration as JSON"""
    config = {
        "property_price": property_price,
        "current_home_value": current_home_value,
        "use_equity": use_equity,
        "equity_percentage": equity_percentage if use_equity else None,
        "deposit_amount": deposit_amount,
        "loan_amount": loan_amount,
        "interest_rate": interest_rate,
        "loan_term": loan_term,
        "combined_fortnightly_income": combined_fortnightly_income,
        "include_rental": include_rental,
        "weekly_rental": weekly_rental if include_rental else None,
        "occupancy_rate": occupancy_rate if include_rental else None,
        "include_agistment": include_agistment,
        "num_cattle": num_cattle if include_agistment else None,
        "agistment_rate": agistment_rate if include_agistment else None,
        "fortnightly_living_expenses": fortnightly_living_expenses,
        "num_children_boarding": num_children_boarding,
        "annual_boarding_fee_per_child": annual_boarding_fee_per_child,
        "annual_council_rates": annual_council_rates,
        "annual_insurance": annual_insurance,
        "annual_maintenance": annual_maintenance,
        "annual_agistment_costs": annual_agistment_costs if include_agistment else None,
        "annual_additional_property_expenses": annual_additional_property_expenses,
        "inflation_rate": inflation_rate,
        "property_growth_rate": property_growth_rate,
        "income_growth_rate": income_growth_rate,
        "rental_growth_rate": rental_growth_rate,
        "projection_years": projection_years,
        "risk_analysis": risk_analysis
    }
    
    return json.dumps(config)

# Function to load configuration
def load_config(config_str):
    """Load configuration from JSON"""
    config = json.loads(config_str)
    # We can't directly set values for Streamlit widgets,
    # but we can set session state which will be used on next rerun
    for key, value in config.items():
        if value is not None:
            st.session_state[key] = value
    
    # Force rerun to apply settings
    st.experimental_rerun()

col1, col2 = st.columns(2)

with col1:
    config_str = save_config()
    st.download_button(
        label="Save Current Configuration",
        data=config_str,
        file_name="dorrigo_property_config.json",
        mime="application/json",
    )

with col2:
    uploaded_file = st.file_uploader("Load Configuration", type=["json"])
    if uploaded_file is not None:
        config_str = uploaded_file.getvalue().decode("utf-8")
        if st.button("Apply Configuration"):
            load_config(config_str)

# Add footer
st.markdown("<div class='footer'>Dorrigo Rural Property Financial Simulator © 2025</div>", unsafe_allow_html=True)
