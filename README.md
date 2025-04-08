# --- START OF FILE DorrigoSimClaude/README.md ---
# Dorrigo Rural Property Financial Simulator

A Streamlit application for simulating financial scenarios for purchasing a rural property in Dorrigo, NSW. This tool helps users explore various combinations of income (employment, rental, agistment), costs (mortgage, school fees, living expenses), upfront costs (stamp duty, LMI), and financing structures.

## Features

- **Interactive Web Interface**: Built with Streamlit featuring sliders, toggles, and input fields
- **Financial Calculations**:
  - Upfront Costs: Stamp Duty (NSW estimate), Lender's Mortgage Insurance (LMI estimate if LVR > 80%), other user-defined costs.
  - Financing: Calculates loan amount based on deposit/equity, LMI capitalization option.
  - Income: Total income from employment, rental, and agistment sources.
  - Expenses: Annual mortgage repayments, living costs, school fees, property running costs.
  - Projections: Net surplus or shortfall, cashflow over time, property value growth, equity accumulation, Loan-to-Value Ratio (LVR) over time.
  - Analysis: Break-even points and risk scenarios (e.g., income loss, interest rate rises).
- **Visualizations**:
  - Upfront funds summary and shortfall/surplus check.
  - Cash flow projection chart (annual and cumulative).
  - Loan amortization, property value, equity, and LVR chart (dual axis).
  - Income and expense breakdown pie charts (Year 1).
  - Risk analysis bar chart comparing scenarios.
- **Export & Configuration**:
  - Download detailed annual projection data as CSV.
  - Export summary report as PDF (includes upfront costs, charts, risk analysis).
  - Save/load scenario configuration settings as a JSON file.

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop/)
- [Visual Studio Code](https://code.visualstudio.com/) (recommended)

### Running with Docker

1.  Clone this repository or download the files (`app.py`, `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `dorrigo.jpg`) to your local machine.
2.  Open a terminal in the project directory.
3.  Build and run the Docker container:

    ```bash
    docker build -t dorrigo-simulator .
    docker run -p 8501:8501 dorrigo-simulator
    ```

4.  Access the application in your web browser at: `http://localhost:8501`

### Running with Docker Compose

Alternatively, you can use Docker Compose (useful for development as it mounts the local directory):

```bash
docker-compose up --build
