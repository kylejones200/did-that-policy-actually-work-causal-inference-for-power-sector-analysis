"""
Python code extracted from 04_causal_inference_blog.md

This code was automatically extracted from the markdown file.
You may need to adjust imports and add necessary dependencies.
"""

import logging
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
    force=True,
)
logger = logging.getLogger(__name__)
states = pd.read_parquet("merged_data/egrid_state_1996-2023.parquet")
treated_states = ["CA", "NY", "MA", "WA", "OR"]
treatment_year = 2018
states["treated"] = states["Plant state abbreviation"].isin(treated_states).astype(int)
states["post"] = (states["data_year"] >= treatment_year).astype(int)
states["carbon_intensity"] = (
    states["State annual CO2 emissions (tons)"]
    / states["State annual net generation (MWh)"]
)
pre_period = states[states["data_year"] < treatment_year]
pre_trends = (
    pre_period.groupby(["data_year", "treated"])["carbon_intensity"].mean().unstack()
)
plt.figure(figsize=(10, 6))
plt.plot(pre_trends.index, pre_trends[0], "o-", label="Control States", linewidth=2)
plt.plot(pre_trends.index, pre_trends[1], "s-", label="Treated States", linewidth=2)
plt.xlabel("Year")
plt.ylabel("Carbon Intensity")
plt.title("Pre-Treatment Trends: Are They Parallel?")
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig("parallel_trends.png", dpi=150)
import statsmodels.formula.api as smf

states["treat_post"] = states["treated"] * states["post"]
model = smf.ols("carbon_intensity ~ treated + post + treat_post", data=states).fit(
    cov_type="cluster", cov_kwds={"groups": states["state_abbr"]}
)
logger.info(model.summary())
did_effect = model.params["treat_post"]
did_se = model.bse["treat_post"]
did_pval = model.pvalues["treat_post"]
logger.info(f"\nTreatment Effect: {did_effect:.6f} tons/MWh")
logger.info(f"Standard Error: {did_se:.6f}")
logger.info(f"P-value: {did_pval:.4f}")
if did_pval < 0.05:
    logger.info(
        f"  by {abs(did_effect):.6f} tons/MWh ({abs(did_effect) / states['carbon_intensity'].mean() * 100:.1f}%)"
    )
else:
    pass
states["years_to_treatment"] = states["data_year"] - treatment_year
for year in range(-5, 6):
    if year != -1:
        states[f"treated_year_{year}"] = (
            states["treated"] * (states["years_to_treatment"] == year)
        ).astype(int)
formula = "carbon_intensity ~ treated + " + " + ".join(
    [f"treated_year_{y}" for y in range(-5, 6) if y != -1]
)
event_model = smf.ols(formula, data=states).fit(cov_type="HC1")
event_time = []
coefficients = []
conf_int = []
for year in range(-5, 6):
    event_time.append(year)
    if year == -1:
        coefficients.append(0)
        conf_int.append((0, 0))
    else:
        coef_name = f"treated_year_{year}"
        coefficients.append(event_model.params.get(coef_name, 0))
        ci = (
            event_model.conf_int().loc[coef_name]
            if coef_name in event_model.params
            else (0, 0)
        )
        conf_int.append(ci)
plt.figure(figsize=(10, 6))
plt.plot(event_time, coefficients, "o-", linewidth=2, markersize=8)
plt.fill_between(
    event_time, [ci[0] for ci in conf_int], [ci[1] for ci in conf_int], alpha=0.3
)
plt.axhline(0, color="black", linestyle="--")
plt.axvline(-0.5, color="red", linestyle="--", label="Policy Implementation")
plt.xlabel("Years Relative to Policy")
plt.ylabel("Treatment Effect")
plt.title("Event Study: Dynamic Policy Effects")
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig("event_study.png", dpi=150)
from scipy.optimize import minimize


def synthetic_control(treated_pre, control_pre, control_post):
    """
    Find optimal weights for synthetic control

    Returns: weights that minimize distance between treated and synthetic control
    """

    def objective(weights):
        synthetic = control_pre @ weights
        return np.sum((treated_pre - synthetic) ** 2)

    n_controls = control_pre.shape[1]
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1}
    bounds = [(0, 1) for _ in range(n_controls)]
    initial = np.ones(n_controls) / n_controls
    result = minimize(
        objective, initial, method="SLSQP", bounds=bounds, constraints=constraints
    )
    return result.x


ca_data = states[states["Plant state abbreviation"] == "CA"].sort_values("data_year")
control_data = states[
    ~states["Plant state abbreviation"].isin(treated_states)
].sort_values(["Plant state abbreviation", "data_year"])
pre_years = list(range(2012, 2018))
ca_pre = ca_data[ca_data["data_year"] < 2018]["carbon_intensity"].values
control_states_list = control_data["Plant state abbreviation"].unique()
control_pre_matrix = []
control_post_matrix = []
for state in control_states_list:
    state_data = control_data[control_data["Plant state abbreviation"] == state]
    pre = state_data[state_data["data_year"] < 2018]["carbon_intensity"].values
    post = state_data[state_data["data_year"] >= 2018]["carbon_intensity"].values
    if len(pre) == len(ca_pre):
        control_pre_matrix.append(pre)
        control_post_matrix.append(post)
control_pre_matrix = np.array(control_pre_matrix).T
control_post_matrix = np.array(control_post_matrix).T
weights = synthetic_control(ca_pre, control_pre_matrix, control_post_matrix)
logger.info("Synthetic California composed of:")
for i, weight in enumerate(weights):
    if weight > 0.01:
        state = control_states_list[i]
        logger.info(f"  {state}: {weight * 100:.1f}%")
synthetic_ca_pre = control_pre_matrix @ weights
synthetic_ca_post = control_post_matrix @ weights
ca_post = ca_data[ca_data["data_year"] >= 2018]["carbon_intensity"].values
gap = ca_post - synthetic_ca_post
avg_effect = gap.mean()
logger.info(f"\nAverage Treatment Effect: {avg_effect:.6f} tons/MWh")
all_years = list(pre_years) + list(range(2018, 2024))
plt.figure(figsize=(12, 6))
plt.plot(pre_years, ca_pre, "o-", label="California (Actual)", linewidth=2)
plt.plot(range(2018, 2024), ca_post, "o-", linewidth=2)
plt.plot(
    pre_years,
    synthetic_ca_pre,
    "s--",
    label="Synthetic California",
    linewidth=2,
    color="red",
)
plt.plot(range(2018, 2024), synthetic_ca_post, "s--", linewidth=2, color="red")
plt.axvline(2017.5, color="black", linestyle="--", alpha=0.5)
plt.fill_between(
    range(2018, 2024), ca_post, synthetic_ca_post, alpha=0.3, color="green"
)
plt.xlabel("Year")
plt.ylabel("Carbon Intensity")
plt.title("Synthetic Control: California vs Synthetic California")
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig("synthetic_control.png", dpi=150)
placebo_effects = []
for placebo_state in control_states_list[:20]:
    placebo_data = control_data[
        control_data["Plant state abbreviation"] == placebo_state
    ]
    placebo_pre = placebo_data[placebo_data["data_year"] < 2018][
        "carbon_intensity"
    ].values
    placebo_post = placebo_data[placebo_data["data_year"] >= 2018][
        "carbon_intensity"
    ].values
    if len(placebo_pre) == len(ca_pre):
        other_controls_pre = []
        other_controls_post = []
        for other_state in control_states_list:
            if other_state != placebo_state:
                other_data = control_data[
                    control_data["Plant state abbreviation"] == other_state
                ]
                pre = other_data[other_data["data_year"] < 2018][
                    "carbon_intensity"
                ].values
                post = other_data[other_data["data_year"] >= 2018][
                    "carbon_intensity"
                ].values
                if len(pre) == len(placebo_pre):
                    other_controls_pre.append(pre)
                    other_controls_post.append(post)
        if len(other_controls_pre) > 0:
            other_controls_pre = np.array(other_controls_pre).T
            other_controls_post = np.array(other_controls_post).T
            placebo_weights = synthetic_control(
                placebo_pre, other_controls_pre, other_controls_post
            )
            synthetic_placebo_post = other_controls_post @ placebo_weights
            placebo_gap = (placebo_post - synthetic_placebo_post).mean()
            placebo_effects.append(placebo_gap)
p_value = (np.abs(placebo_effects) >= np.abs(avg_effect)).mean()
logger.info("\nPlacebo Test Results:")
logger.info(f"  California effect: {avg_effect:.6f}")
logger.info(f"  Mean placebo effect: {np.mean(placebo_effects):.6f}")
logger.info(f"  P-value: {p_value:.4f}")
if p_value < 0.05:
    pass
else:
    pass
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

plants_2020 = plants[plants["data_year"] == 2020].copy()
X_features = ["log_generation", "log_capacity", "capacity_factor", "plant_age"]
treatment_prob = 1 / (1 + np.exp(-(plants_2020["log_generation"] - 10) / 2))
plants_2020["treated"] = (np.random.random(len(plants_2020)) < treatment_prob).astype(
    int
)
plants_2021 = plants[plants["data_year"] == 2021]
outcome_map = plants_2021.set_index("Plant ID")["carbon_intensity"]
plants_2020["outcome_2021"] = plants_2020["Plant ID"].map(outcome_map)
psm_data = plants_2020[X_features + ["treated", "outcome_2021"]].dropna()
X = psm_data[X_features]
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
ps_model = LogisticRegression(random_state=42)
ps_model.fit(X_scaled, psm_data["treated"])
psm_data["propensity_score"] = ps_model.predict_proba(X_scaled)[:, 1]
logger.info("Propensity Score Distribution:")
logger.info(psm_data.groupby("treated")["propensity_score"].describe())
plt.figure(figsize=(10, 5))
psm_data[psm_data["treated"] == 0]["propensity_score"].hist(
    bins=50, alpha=0.5, label="Control", color="blue"
)
psm_data[psm_data["treated"] == 1]["propensity_score"].hist(
    bins=50, alpha=0.5, label="Treated", color="red"
)
plt.xlabel("Propensity Score")
plt.ylabel("Frequency")
plt.title("Propensity Score Overlap")
plt.legend()
plt.savefig("propensity_overlap.png", dpi=150)
from sklearn.neighbors import NearestNeighbors

np.random.seed(42)
treated = psm_data[psm_data["treated"] == 1]
control = psm_data[psm_data["treated"] == 0]
nn = NearestNeighbors(n_neighbors=1, metric="euclidean")
nn.fit(control[["propensity_score"]])
distances, indices = nn.kneighbors(treated[["propensity_score"]])
matched_control_idx = control.index[indices.flatten()]
matched_treated_idx = treated.index
treated_outcomes = psm_data.loc[matched_treated_idx, "outcome_2021"]
control_outcomes = psm_data.loc[matched_control_idx, "outcome_2021"]
att = (treated_outcomes.values - control_outcomes.values).mean()
se = (treated_outcomes.values - control_outcomes.values).std() / np.sqrt(
    len(matched_treated_idx)
)
logger.info(f"\nAverage Treatment Effect on Treated (ATT): {att:.6f}")
logger.info(f"Standard Error: {se:.6f}")
logger.info(f"95% CI: [{att - 1.96 * se:.6f}, {att + 1.96 * se:.6f}]")
if abs(att) / se > 1.96:
    pass
logger.info("\nCovariate Balance After Matching:")
for var in X_features:
    treated_mean = psm_data.loc[matched_treated_idx, var].mean()
    control_mean = psm_data.loc[matched_control_idx, var].mean()
    pooled_std = psm_data[var].std()
    std_diff = (treated_mean - control_mean) / pooled_std * 100
    logger.info(f"  {var}:")
    logger.info(f"    Treated mean: {treated_mean:.4f}")
    logger.info(f"    Control mean: {control_mean:.4f}")
    logger.info(f"    Standardized difference: {std_diff:.2f}%")

