import pandas as pd
import matplotlib.pyplot as plt
import os

# Define the output directory for plots
PLOTS_DIR = "outputs/plots"
os.makedirs(PLOTS_DIR, exist_ok=True)

# Load the sweep results from the outputs folder
try:
    df = pd.read_csv('outputs/override_coeff_sweep.csv')
except FileNotFoundError:
    print("Error: 'override_coeff_sweep.csv' not found.")
    print("Please run the main simulation with the 'sweep' argument first.")
    exit()

# --- Plot 1: Equity Gap vs coefficient value ---
plt.figure(figsize=(8, 5))
for param, grp in df.groupby('param'):
    plt.plot(grp['value'], grp['equity_gap'], marker='o', label=param.replace('_', ' ').title())

plt.axhline(0, color='grey', linestyle='--')
plt.xlabel("Coefficient Value")
plt.ylabel("Equity Gap (Mean Wait B − A) [min]")
plt.title("Impact of Override Coefficients on Equity Gap")
plt.legend()
plt.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, "sweep_plot_equity_gap.png"))
print(f"Saved equity gap plot to {PLOTS_DIR}/sweep_plot_equity_gap.png")
plt.close()


# --- Plot 2: Override Rate vs coefficient value ---
plt.figure(figsize=(8, 5))
for param, grp in df.groupby('param'):
    plt.plot(grp['value'], grp['override_rate'] * 100, marker='o', label=param.replace('_', ' ').title()) # Multiply by 100 for percentage

plt.xlabel("Coefficient Value")
plt.ylabel("Overall Override Rate (%)")
plt.title("Impact of Override Coefficients on Override Rate")
plt.legend()
plt.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, "sweep_plot_override_rate.png"))
print(f"Saved override rate plot to {PLOTS_DIR}/sweep_plot_override_rate.png")
plt.close()