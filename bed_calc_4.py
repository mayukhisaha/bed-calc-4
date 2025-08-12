import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
from datetime import date

# --------------------------
# Page Configuration
# --------------------------
st.set_page_config(page_title="NHS vs Darwin Bed Cost Calculator", layout="centered")
st.title("NHS vs Darwin Bed Cost Calculator")
st.caption(f"Report generated on {date.today().strftime('%d %B %Y')}")

# --------------------------
# Cost Data
# --------------------------
data = {
    "Care Type": [
        "General Ward", "Surgical Ward", "Critical Care", "Maternity Ward", "Paediatrics", "Orthopaedics",
        "Oncology", "Cardiovascular", "ENT", "Neurology", "Psychiatric", "Specialised Ward"
    ],
    "NHS Capital Cost": [
        80.63, 278.29, 77.96, 54.55, 61.82, 57.98,
        65.75, 65.75, 57.98, 65.75, 45.68, 63.94
    ],
    "NHS Maintenance Cost": [
        12.20, 15.58, 5.48, 3.41, 4.05, 3.62,
        4.38, 4.60, 3.93, 4.38, 2.74, 4.26
    ],
    "Area per Bed (m²)": [
        32, 40, 40, 32, 35, 34,
        36, 36, 34, 36, 30, 35
    ]
}
df = pd.DataFrame(data)
df["NHS Total Cost Per Night"] = df["NHS Capital Cost"] + df["NHS Maintenance Cost"]

# --------------------------
# Sidebar Inputs
# --------------------------
st.sidebar.header("User Inputs")
selected_ward = st.sidebar.selectbox("Select Ward Type", df["Care Type"].unique())
num_beds = st.sidebar.number_input("Number of Beds", min_value=1, max_value=100, value=10)
num_nights = st.sidebar.number_input("Number of Nights", min_value=1, max_value=365, value=30)
occupancy_rate = st.sidebar.slider("Occupancy Rate (%)", 50, 100, 90)
timeframe = st.sidebar.selectbox("Cost Timeframe", ["Daily", "5 Years", "10 Years", "15 Years", "60 Years"])
darwin_cost_input = st.sidebar.number_input("Darwin Cost per Night (£)", min_value=50.0, max_value=200.0, value=80.0, step=1.0)
sqm_cost = st.sidebar.number_input("NHS Build Cost per m² (£)", min_value=1500, max_value=4000, value=2500, step=100)

if occupancy_rate < 70:
    st.sidebar.warning("Warning: NHS beds typically operate above 85% occupancy.")

# --------------------------
# Functions
# --------------------------
def get_timeframe_days(label):
    return {"Daily": 1, "5 Years": 1825, "10 Years": 3650, "15 Years": 5475, "60 Years": 21900}[label]

def calculate_effective_nights(nights, occ_rate, tf_days):
    return nights if tf_days == 1 else tf_days * (occ_rate / 100)

def calculate_costs(cap, maint, darwin, beds, nights):
    nhs_night = cap + maint
    total_nhs = nhs_night * beds * nights
    total_darwin = darwin * beds * nights
    savings = total_nhs - total_darwin
    percent_savings = ((savings / total_nhs) * 100) if total_nhs else 0
    return nhs_night, total_nhs, total_darwin, savings, percent_savings

# --------------------------
# Calculations
# --------------------------
row = df[df["Care Type"] == selected_ward].iloc[0]
area = row["Area per Bed (m²)"]
timeframe_days = get_timeframe_days(timeframe)
effective_nights = calculate_effective_nights(num_nights, occupancy_rate, timeframe_days)

# Capital cost switch for 60-year model
if timeframe == "60 Years":
    capital_cost = (sqm_cost * area) / 60 / (365 * 0.9)
else:
    capital_cost = row["NHS Capital Cost"]

nhs_night, total_nhs, total_darwin, savings, percent_savings = calculate_costs(
    capital_cost, row["NHS Maintenance Cost"], darwin_cost_input, num_beds, effective_nights
)

# --------------------------
# Summary Display
# --------------------------
st.subheader(f"Cost Summary for: {selected_ward}")
col1, col2, col3, col4 = st.columns(4)
col1.metric("NHS Total Cost", f"£{total_nhs:,.2f}")
col2.metric("Darwin Total Cost", f"£{total_darwin:,.2f}")
col3.metric("Estimated Savings", f"£{abs(savings):,.2f}", delta=f"{'-' if savings > 0 else '+'}£{abs(savings):,.2f}")
col4.metric("% Savings", f"{percent_savings:.1f}%")

st.markdown("### Detailed NHS Cost Breakdown (per bed per night)")
st.write(f"• Capital Cost: £{capital_cost:.2f}")
st.write(f"• Maintenance Cost: £{row['NHS Maintenance Cost']:.2f}")
st.write(f"• Total NHS Cost: £{nhs_night:.2f}")
st.write(f"• Darwin Flat Cost: £{darwin_cost_input:.2f}")

# --------------------------
# Chart
# --------------------------
st.subheader("Cost per Bed per Night")
fig1, ax1 = plt.subplots()
ax1.bar(["NHS", "Darwin"], [nhs_night, darwin_cost_input], color=["#1f77b4", "#ff7f0e"])
ax1.set_ylabel("£ per Bed per Night")
ax1.set_title("Unit Cost Comparison")
st.pyplot(fig1)

st.subheader("Total Cost Comparison")
fig2, ax2 = plt.subplots()
ax2.bar(["NHS", "Darwin"], [total_nhs, total_darwin], color=["#1f77b4", "#ff7f0e"])
ax2.set_ylabel("Total Cost (£)")
ax2.set_title(f"Total Cost for {selected_ward} ({timeframe})")
st.pyplot(fig2)

# --------------------------
# Download Report
# --------------------------
st.markdown("Download Report")
report_df = pd.DataFrame({
    "Ward Type": [selected_ward],
    "Beds": [num_beds],
    "Nights (Adjusted)": [effective_nights],
    "NHS per Night (£)": [nhs_night],
    "Darwin per Night (£)": [darwin_cost_input],
    "NHS Total (£)": [total_nhs],
    "Darwin Total (£)": [total_darwin],
    "Savings (£)": [savings],
    "% Savings": [percent_savings]
})
csv_buffer = io.StringIO()
report_df.to_csv(csv_buffer, index=False)
st.download_button("Download CSV Report", data=csv_buffer.getvalue(), file_name="bed_cost_comparison_report.csv", mime="text/csv")

# --------------------------
# Assumptions
# --------------------------
st.markdown("---")
st.markdown(f"""
**Assumptions:**
- NHS capital costs amortised over selected timeframe (5–60 years)  
- NHS Build cost per m² (£{sqm_cost}) only applied when '60 Years' is selected  
- Hard FM includes building maintenance (not clinical or soft FM)  
- Darwin cost is flat per night and user-defined  
- NHS occupancy rate set to 90% by default (adjustable)

**Sources:** HPCG, NHS ERIC, Royal Papworth, Darwin Group
""")
