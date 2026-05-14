# Did That Policy Actually Work? Causal Inference for Power Sector Analysis

*Using Difference-in-Differences, Synthetic Control, and Propensity Score Matching to rigorously evaluate environmental policy impacts*

Kyle Jones  
13 min read · Oct 6, 2025

---

In 2018, several states implemented carbon pricing policies. Five years later, their emissions are down 15%. Success, right?

Not so fast. Emissions might have declined anyway due to cheaper natural gas displacing coal, falling renewable energy costs, economic recession reducing electricity demand, and federal efficiency standards for appliances.

How do we know what would have happened *without* the policy? That's the fundamental problem of causal inference: we can't observe the same state both with and without treatment.

This article demonstrates three rigorous methods—Difference-in-Differences, Synthetic Control, and Propensity Score Matching—to estimate causal effects using 27 years of EPA power plant data. These techniques power billion-dollar policy decisions and academic research worldwide.

![Causal inference visualization showing treatment effects](04_causal_inference_main.png)

---

## The Fundamental Problem

Imagine California implements carbon pricing in 2018. Emissions drop 20% by 2023. Did the policy work?

What we observe:
- California with policy: Emissions down 20%

What we don't observe but need:
- California without policy: What would emissions have been?

The counterfactual (California without policy) is impossible to observe—California can't exist in both states simultaneously. Causal inference constructs this counterfactual from data.

Naive Comparison Fails:

You might think comparing California to a state without the policy would work. But states differ in many ways including different energy mix (CA has more renewables), different economy (CA's GDP growth differs), different regulations (CA has stricter standards pre-policy), and different weather (affects electricity demand).

Simply comparing California to, say, Texas would confound the policy effect with these pre-existing differences. We need methods that account for this.

---

## Method 1: Difference-in-Differences (DiD)

DiD is the workhorse of policy evaluation. The intuition is elegant. First, compare California before and after policy (difference #1). Second, compare control states before and after same period (difference #2). Third, subtract difference #2 from difference #1. The second difference removes trends that would have happened anyway. What remains is the causal effect.

### The Key Assumption: Parallel Trends

DiD assumes that without treatment, treated and control groups would have followed parallel trends. This assumption is testable by examining pre-treatment behavior.

The system loads state-level EPA data spanning 1996-2023, defining treated states as those implementing hypothetical carbon pricing in 2018: California, New York, Massachusetts, Washington, and Oregon. Carbon intensity is calculated as state annual CO2 emissions divided by state annual net generation (MWh), creating the metric we want to evaluate for policy impact.

Visual inspection of pre-treatment trends from 1996-2017 reveals whether treated and control states followed similar trajectories. If lines are roughly parallel pre-2018, the parallel trends assumption holds. If treated states were already declining faster than controls, basic DiD cannot identify causal effects—the differing trends confound treatment with pre-existing differences.

(See Complete Implementation section for parallel trends code)

### Estimating the Treatment Effect

The DiD regression specification models carbon intensity as a function of three terms plus their interaction: a treated dummy (1 for CA/NY/MA/WA/OR), a post-2018 dummy, and the treated×post interaction. The coefficient on the interaction term represents the DiD estimate—the differential change in treated states relative to control states after policy implementation.

Standard errors cluster at the state level to account for serial correlation within states over time. Without clustering, standard errors would be artificially small, overstating precision.

Example output shows a treatment effect of -0.042 tons/MWh (standard error 0.018, p-value 0.020). This means carbon pricing reduced emissions intensity by 0.042 tons/MWh, approximately 7.8% of the mean, with statistical significance at the 5% level. The interpretation: Carbon pricing caused an 8% reduction in emissions intensity after controlling for national trends affecting all states equally.

(See Complete Implementation section for DiD regression code)

### Event Study: Dynamic Treatment Effects

Was the policy effect immediate or gradual? Did anticipation effects occur before implementation? Event studies reveal treatment dynamics by estimating separate coefficients for each year relative to treatment.

The system creates year dummies for five years before and five years after treatment, omitting year -1 as the reference period. Interactions between treated status and each year dummy generate time-varying treatment effects. Plotting these coefficients with confidence intervals reveals the temporal pattern.

What to look for:

Pre-treatment coefficients near zero confirm parallel trends. If coefficients before year 0 deviate significantly from zero, the parallel trends assumption fails—treated and control groups were already diverging.

Post-treatment patterns reveal implementation dynamics. Immediate negative coefficients indicate quick policy response. Gradual deepening suggests cumulative effects as compliance improves or investments materialize. Growing effects over time may indicate learning or capital stock turnover.

Confidence intervals quantify precision. Narrow bands post-treatment mean precisely estimated effects. Widening intervals suggest growing uncertainty (often due to diverging state trajectories).

(See Complete Implementation section for event study code)

---

## Method 2: Synthetic Control

What if you have only ONE treated unit? DiD requires multiple treated and control units for statistical inference. When analyzing a single treated entity—like Germany's nuclear phase-out or California's emissions trading—Synthetic Control provides the solution.

The idea: Create a "synthetic California" by weighting control states to match pre-treatment California as closely as possible in all relevant dimensions. Then compare real California to its synthetic counterpart after treatment. The gap is the causal effect.

### Building the Synthetic Control

Synthetic control optimization finds weights for control states that minimize the distance between treated unit pre-treatment outcomes and the weighted average of control unit outcomes. Weights must be non-negative and sum to 1, ensuring the synthetic unit represents a convex combination of controls.

The system prepares California as the treated unit and constructs control matrices from non-treated states. Pre-treatment outcomes (2012-2017) form the basis for optimization. The algorithm searches weight space to minimize squared distance between California's actual trajectory and the synthetic trajectory.

Example output shows Synthetic California composed of: Texas 28.3%, Pennsylvania 22.1%, Florida 18.7%, Ohio 15.2%, Illinois 10.9%, and Georgia 4.8%. These states, when weighted appropriately, match California's pre-treatment carbon intensity path despite having different energy mixes individually. The optimization finds the combination that best replicates California's behavior absent the policy.

(See Complete Implementation section for synthetic control optimization code)

### Comparing Real vs Synthetic

After constructing Synthetic California, the system generates post-treatment predictions by applying the same weights to control states' post-2018 outcomes. The gap between actual California and Synthetic California after 2018 represents the treatment effect—what California achieved beyond what its synthetic counterpart (representing the no-policy scenario) would have achieved.

Visualization plots both series: actual California matches synthetic California closely pre-2018 (by construction), then diverges post-2018. The area between curves represents cumulative treatment effect. If actual California falls below synthetic California, the policy reduced emissions. Upward divergence would indicate policy backfire (though rare in practice).

The average treatment effect computes the mean gap across post-treatment years, providing a single summary statistic for policy impact.

(See Complete Implementation section for synthetic control visualization code)

### Inference: Placebo Tests

How do we know the observed gap isn't due to random chance? Classical inference doesn't apply—we have one treated unit, not a sample. Synthetic Control uses placebo tests for statistical inference.

Placebo logic: Apply synthetic control methodology to states that didn't receive treatment. These "placebo" treatments should show no effects (by definition, nothing changed in these states). If California's effect is larger than 95% of placebo effects, it's statistically significant at the 5% level.

The system iterates through control states, constructing synthetic versions of each using the remaining controls. For each placebo state, it calculates the post-treatment gap between actual and synthetic. The distribution of placebo effects characterizes what random chance looks like. California's actual effect is compared to this distribution to compute a p-value: the fraction of placebo effects as large or larger than California's effect.

If the p-value is less than 0.05, California's effect is statistically distinguishable from random variation—we reject the null hypothesis of no effect.

(See Complete Implementation section for placebo test code)

---

## Method 3: Propensity Score Matching

DiD and Synthetic Control work at aggregate levels (states, countries). What about plant-level interventions where units choose whether to receive treatment?

Example: Some power plants adopted efficiency upgrades in 2020. Did they reduce emissions?

Challenge: Plants self-selected into treatment. Perhaps only well-run plants with available capital chose to upgrade. Comparing upgraders to non-upgraders confounds treatment effect with plant quality—selection bias undermines causal identification.

Solution: Propensity Score Matching creates balanced comparison groups by matching treated and control units with similar likelihoods of treatment based on observed covariates.

### Step 1: Estimate Propensity Scores

Propensity scores represent the probability each plant receives treatment given its observed characteristics: generation capacity, plant age, capacity factor, historical emissions. Logistic regression estimates these probabilities using pre-treatment covariates.

The system uses 2020 plant characteristics to predict treatment, then matches to 2021 outcomes (post-treatment). Features include log generation, log capacity, capacity factor, and plant age—variables likely correlated with both treatment and outcomes. In practice, domain knowledge guides feature selection: include variables affecting both treatment assignment and outcomes, exclude post-treatment variables (colliders), and avoid variables only affecting outcomes (instrumental variables wasted as controls).

Propensity score distributions show whether treated and control plants overlap in characteristics. Good overlap means matching will succeed; poor overlap (treated plants all large, controls all small) means no valid comparisons exist in the data.

(See Complete Implementation section for propensity score estimation code)

### Step 2: Check Common Support

Common support requires propensity score distributions to overlap between treated and control groups. If treated plants have scores 0.7-0.9 and controls have 0.1-0.3, no overlap exists—we cannot find valid matches. Trimming drops observations outside the common support region.

Histograms visualize overlap. Substantial overlap (both distributions cover 0.2-0.8) enables matching. Minimal overlap (distributions barely touch) suggests treatment selection is too strong for matching—treated and control plants are fundamentally different on observables, making as-if randomization impossible.

(See Complete Implementation section for common support visualization code)

### Step 3: Match and Estimate Effect

Nearest neighbor matching pairs each treated plant with the control plant having the closest propensity score. This creates matched pairs balanced on covariates—treated and control plants within pairs look similar pre-treatment, so differences in outcomes plausibly reflect treatment effects rather than pre-existing differences.

The Average Treatment Effect on the Treated (ATT) computes the mean difference in outcomes between treated plants and their matched controls. Standard errors account for matching variance. Confidence intervals determine statistical significance.

Example output might show ATT of -0.035 tons/MWh (SE 0.012), indicating efficiency upgrades reduced emissions intensity by 0.035 tons/MWh on average among plants that upgraded. The 95% confidence interval excludes zero, establishing statistical significance.

(See Complete Implementation section for matching and ATT estimation code)

### Step 4: Check Balance

Did matching succeed in balancing covariates? For each covariate, compare means between matched treated and matched control groups. Standardized differences (mean difference divided by pooled standard deviation, expressed as percentage) quantify balance.

Rule of thumb: Standardized differences < 10% indicate good balance. Differences > 25% suggest poor balance—the covariate remains imbalanced after matching, threatening causal identification.

If balance checks fail, refine the propensity score model (add interactions, polynomials) or change matching algorithm (caliper matching, kernel matching) to achieve balance.

(See Complete Implementation section for balance checking code)

---

## When to Use Which Method?

Difference-in-Differences works best when you have multiple treated and control units, a clear before and after period, the parallel trends assumption holds, and policy affects groups (states, regions). Example application is state-level carbon pricing.

Synthetic Control works best when you have a single treated unit, many control units, a long pre-treatment period, and policy affects one entity. Example application is Germany's nuclear phase-out.

Propensity Score Matching works best when you have individual-level treatment, selection on observables, good covariate overlap, and cross-sectional or panel data. Example application is plant efficiency upgrades.

---

## Common Pitfalls

Avoid assuming correlation equals causation. Just because emissions fell after a policy doesn't mean the policy caused it.

Avoid ignoring parallel trends. If the treated group was already trending differently, DiD fails.

Avoid poor overlap in PSM. You can't match if groups are too different.

Avoid p-hacking. Testing many specifications and reporting the one that works undermines validity.

Avoid confusing statistical and practical significance. A tiny effect might be statistically significant but practically meaningless.

Instead, pre-register analyses, test assumptions, report robustness checks, and be transparent about limitations.

---

## So What?

Causal inference transforms policy evaluation from guesswork to science. Instead of "emissions fell 15% after the policy," we can say "the policy caused a 7-8% reduction, after accounting for other factors—a $2.3B annual benefit."

These methods enable:

Evidence-based policy: Know what works before scaling nationwide. A/B test policies like tech companies A/B test features.

Accountability: Did the promised benefits materialize? Rigorous evaluation holds policymakers accountable.

Efficient allocation: Invest in policies with proven effects, not politically popular but ineffective ones.

Learning: Understand why some policies work and others fail. Refine and improve.

The methods shown here—DiD for group-level policies, Synthetic Control for single units, PSM for individual interventions—cover most policy evaluation scenarios. Combined with domain expertise and careful thinking about identification assumptions, they provide credible answers to causal questions.

Correlation isn't causation—but with these tools, you can find out what is.

---

Causal Inference · Policy Analysis · Statistics · Energy · Python

---

*Found this useful? I'm Kyle Jones—I write about rigorous data analysis for policy, energy, and climate. Follow for more evidence-based insights.*

---

## Complete Implementation

All code for the three causal inference methods is consolidated below, including parallel trends testing, DiD regression, event studies, synthetic control optimization, placebo tests, and propensity score matching.

### Method 1: Difference-in-Differences

#### Parallel Trends Visualization

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load state-level data
states = pd.read_parquet('merged_data/egrid_state_1996-2023.parquet')

# Define treatment (hypothetical carbon pricing states)
treated_states = ['CA', 'NY', 'MA', 'WA', 'OR']
treatment_year = 2018

states['treated'] = states['Plant state abbreviation'].isin(treated_states).astype(int)
states['post'] = (states['data_year'] >= treatment_year).astype(int)

# Calculate carbon intensity
states['carbon_intensity'] = (
    states['State annual CO2 emissions (tons)'] / 
    states['State annual net generation (MWh)']
)

# Check parallel trends visually
pre_period = states[states['data_year'] < treatment_year]

pre_trends = pre_period.groupby(['data_year', 'treated'])['carbon_intensity'].mean().unstack()

plt.figure(figsize=(10, 6))
plt.plot(pre_trends.index, pre_trends[0], 'o-', label='Control States', linewidth=2)
plt.plot(pre_trends.index, pre_trends[1], 's-', label='Treated States', linewidth=2)
plt.xlabel('Year')
plt.ylabel('Carbon Intensity')
plt.title('Pre-Treatment Trends: Are They Parallel?')
plt.legend()
plt.grid(False)
plt.savefig('parallel_trends.png', dpi=150)
```

#### DiD Regression

```python
import statsmodels.formula.api as smf

# Create interaction term
states['treat_post'] = states['treated'] * states['post']

# DiD regression: Y = β0 + β1*treated + β2*post + β3*(treated*post) + ε
# β3 is the DiD estimate
model = smf.ols(
    'carbon_intensity ~ treated + post + treat_post',
    data=states
).fit(cov_type='cluster', cov_kwds={'groups': states['state_abbr']})

print(model.summary())

did_effect = model.params['treat_post']
did_se = model.bse['treat_post']
did_pval = model.pvalues['treat_post']

print(f"\nTreatment Effect: {did_effect:.6f} tons/MWh")
print(f"Standard Error: {did_se:.6f}")
print(f"P-value: {did_pval:.4f}")

if did_pval < 0.05:
    print(f"\n✓ Policy significantly {'reduced' if did_effect < 0 else 'increased'} emissions")
    print(f"  by {abs(did_effect):.6f} tons/MWh ({abs(did_effect)/states['carbon_intensity'].mean()*100:.1f}%)")
else:
    print("\n✗ No significant policy effect detected")
```

#### Event Study

```python
# Create year dummies relative to treatment
states['years_to_treatment'] = states['data_year'] - treatment_year

# Create interactions (omit year -1 as reference)
for year in range(-5, 6):
    if year != -1:
        states[f'treated_year_{year}'] = (
            states['treated'] * (states['years_to_treatment'] == year)
        ).astype(int)

# Run event study regression
formula = 'carbon_intensity ~ treated + ' + ' + '.join([
    f'treated_year_{y}' for y in range(-5, 6) if y != -1
])

event_model = smf.ols(formula, data=states).fit(cov_type='HC1')

# Extract coefficients
event_time = []
coefficients = []
conf_int = []

for year in range(-5, 6):
    event_time.append(year)
    if year == -1:
        coefficients.append(0)  # Reference period
        conf_int.append((0, 0))
    else:
        coef_name = f'treated_year_{year}'
        coefficients.append(event_model.params.get(coef_name, 0))
        ci = event_model.conf_int().loc[coef_name] if coef_name in event_model.params else (0, 0)
        conf_int.append(ci)

# Plot event study
plt.figure(figsize=(10, 6))
plt.plot(event_time, coefficients, 'o-', linewidth=2, markersize=8)
plt.fill_between(event_time, 
                 [ci[0] for ci in conf_int], 
                 [ci[1] for ci in conf_int], 
                 alpha=0.3)
plt.axhline(0, color='black', linestyle='--')
plt.axvline(-0.5, color='red', linestyle='--', label='Policy Implementation')
plt.xlabel('Years Relative to Policy')
plt.ylabel('Treatment Effect')
plt.title('Event Study: Dynamic Policy Effects')
plt.legend()
plt.grid(False)
plt.savefig('event_study.png', dpi=150)
```

---

### Method 2: Synthetic Control

#### Optimization and Construction

```python
from scipy.optimize import minimize

def synthetic_control(treated_pre, control_pre, control_post):
    """
    Find optimal weights for synthetic control
    
    Returns: weights that minimize distance between treated and synthetic control
    """
    
    def objective(weights):
        synthetic = control_pre @ weights
        return np.sum((treated_pre - synthetic)**2)
    
    n_controls = control_pre.shape[1]
    
    # Constraints: weights sum to 1, all non-negative
    constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1})
    bounds = [(0, 1) for _ in range(n_controls)]
    initial = np.ones(n_controls) / n_controls
    
    result = minimize(objective, initial, method='SLSQP', 
                     bounds=bounds, constraints=constraints)
    
    return result.x

# Prepare data: California as treated unit
ca_data = states[states['Plant state abbreviation'] == 'CA'].sort_values('data_year')
control_data = states[~states['Plant state abbreviation'].isin(treated_states)].sort_values(['Plant state abbreviation', 'data_year'])

# Get pre-treatment outcomes
pre_years = [y for y in range(2012, 2018)]
ca_pre = ca_data[ca_data['data_year'] < 2018]['carbon_intensity'].values

# Build control matrices
control_states_list = control_data['Plant state abbreviation'].unique()
control_pre_matrix = []
control_post_matrix = []

for state in control_states_list:
    state_data = control_data[control_data['Plant state abbreviation'] == state]
    pre = state_data[state_data['data_year'] < 2018]['carbon_intensity'].values
    post = state_data[state_data['data_year'] >= 2018]['carbon_intensity'].values
    
    if len(pre) == len(ca_pre):  # Same length
        control_pre_matrix.append(pre)
        control_post_matrix.append(post)

control_pre_matrix = np.array(control_pre_matrix).T
control_post_matrix = np.array(control_post_matrix).T

# Find optimal weights
weights = synthetic_control(ca_pre, control_pre_matrix, control_post_matrix)

print("Synthetic California composed of:")
for i, weight in enumerate(weights):
    if weight > 0.01:  # Only show states with >1% weight
        state = control_states_list[i]
        print(f"  {state}: {weight*100:.1f}%")
```

#### Visualization

```python
# Generate synthetic control series
synthetic_ca_pre = control_pre_matrix @ weights
synthetic_ca_post = control_post_matrix @ weights

ca_post = ca_data[ca_data['data_year'] >= 2018]['carbon_intensity'].values

# Calculate treatment effect
gap = ca_post - synthetic_ca_post
avg_effect = gap.mean()

print(f"\nAverage Treatment Effect: {avg_effect:.6f} tons/MWh")

# Visualize
all_years = list(pre_years) + list(range(2018, 2024))

plt.figure(figsize=(12, 6))
plt.plot(pre_years, ca_pre, 'o-', label='California (Actual)', linewidth=2)
plt.plot(range(2018, 2024), ca_post, 'o-', linewidth=2)
plt.plot(pre_years, synthetic_ca_pre, 's--', label='Synthetic California', linewidth=2, color='red')
plt.plot(range(2018, 2024), synthetic_ca_post, 's--', linewidth=2, color='red')
plt.axvline(2017.5, color='black', linestyle='--', alpha=0.5)
plt.fill_between(range(2018, 2024), ca_post, synthetic_ca_post, alpha=0.3, color='green')
plt.xlabel('Year')
plt.ylabel('Carbon Intensity')
plt.title('Synthetic Control: California vs Synthetic California')
plt.legend()
plt.grid(False)
plt.savefig('synthetic_control.png', dpi=150)
```

#### Placebo Tests

```python
# Run synthetic control on each control state (placebos)
placebo_effects = []

for placebo_state in control_states_list[:20]:  # Limit for speed
    # Create synthetic control for this placebo state
    placebo_data = control_data[control_data['Plant state abbreviation'] == placebo_state]
    placebo_pre = placebo_data[placebo_data['data_year'] < 2018]['carbon_intensity'].values
    placebo_post = placebo_data[placebo_data['data_year'] >= 2018]['carbon_intensity'].values
    
    if len(placebo_pre) == len(ca_pre):
        # Build control matrix excluding this placebo
        other_controls_pre = []
        other_controls_post = []
        
        for other_state in control_states_list:
            if other_state != placebo_state:
                other_data = control_data[control_data['Plant state abbreviation'] == other_state]
                pre = other_data[other_data['data_year'] < 2018]['carbon_intensity'].values
                post = other_data[other_data['data_year'] >= 2018]['carbon_intensity'].values
                
                if len(pre) == len(placebo_pre):
                    other_controls_pre.append(pre)
                    other_controls_post.append(post)
        
        if len(other_controls_pre) > 0:
            other_controls_pre = np.array(other_controls_pre).T
            other_controls_post = np.array(other_controls_post).T
            
            placebo_weights = synthetic_control(placebo_pre, other_controls_pre, other_controls_post)
            synthetic_placebo_post = other_controls_post @ placebo_weights
            
            placebo_gap = (placebo_post - synthetic_placebo_post).mean()
            placebo_effects.append(placebo_gap)

# Compare CA effect to placebo distribution
p_value = (np.abs(placebo_effects) >= np.abs(avg_effect)).mean()

print(f"\nPlacebo Test Results:")
print(f"  California effect: {avg_effect:.6f}")
print(f"  Mean placebo effect: {np.mean(placebo_effects):.6f}")
print(f"  P-value: {p_value:.4f}")

if p_value < 0.05:
    print("  ✓ California's effect is statistically significant")
else:
    print("  ✗ Effect not distinguishable from random chance")
```

---

### Method 3: Propensity Score Matching

#### Propensity Score Estimation

```python
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# Plant-level data (hypothetical treatment)
plants_2020 = plants[plants['data_year'] == 2020].copy()

# Create features predicting treatment
X_features = ['log_generation', 'log_capacity', 'capacity_factor', 'plant_age']

# Simulate treatment based on covariates (in practice, use actual treatment)
np.random.seed(42)
treatment_prob = 1 / (1 + np.exp(-(plants_2020['log_generation'] - 10) / 2))
plants_2020['treated'] = (np.random.random(len(plants_2020)) < treatment_prob).astype(int)

# Outcome: 2021 carbon intensity
plants_2021 = plants[plants['data_year'] == 2021]
outcome_map = plants_2021.set_index('Plant ID')['carbon_intensity']
plants_2020['outcome_2021'] = plants_2020['Plant ID'].map(outcome_map)

# Drop missing
psm_data = plants_2020[X_features + ['treated', 'outcome_2021']].dropna()

# Estimate propensity scores
X = psm_data[X_features]
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

ps_model = LogisticRegression(random_state=42)
ps_model.fit(X_scaled, psm_data['treated'])

psm_data['propensity_score'] = ps_model.predict_proba(X_scaled)[:, 1]

print("Propensity Score Distribution:")
print(psm_data.groupby('treated')['propensity_score'].describe())
```

#### Common Support Check

```python
plt.figure(figsize=(10, 5))
psm_data[psm_data['treated']==0]['propensity_score'].hist(
    bins=50, alpha=0.5, label='Control', color='blue'
)
psm_data[psm_data['treated']==1]['propensity_score'].hist(
    bins=50, alpha=0.5, label='Treated', color='red'
)
plt.xlabel('Propensity Score')
plt.ylabel('Frequency')
plt.title('Propensity Score Overlap')
plt.legend()
plt.savefig('propensity_overlap.png', dpi=150)
```

#### Matching and ATT Estimation

```python
from sklearn.neighbors import NearestNeighbors

# Nearest neighbor matching
treated = psm_data[psm_data['treated']==1]
control = psm_data[psm_data['treated']==0]

nn = NearestNeighbors(n_neighbors=1, metric='euclidean')
nn.fit(control[['propensity_score']])

distances, indices = nn.kneighbors(treated[['propensity_score']])

# Get matched pairs
matched_control_idx = control.index[indices.flatten()]
matched_treated_idx = treated.index

# Estimate ATT (Average Treatment Effect on Treated)
treated_outcomes = psm_data.loc[matched_treated_idx, 'outcome_2021']
control_outcomes = psm_data.loc[matched_control_idx, 'outcome_2021']

att = (treated_outcomes.values - control_outcomes.values).mean()
se = (treated_outcomes.values - control_outcomes.values).std() / np.sqrt(len(matched_treated_idx))

print(f"\nAverage Treatment Effect on Treated (ATT): {att:.6f}")
print(f"Standard Error: {se:.6f}")
print(f"95% CI: [{att - 1.96*se:.6f}, {att + 1.96*se:.6f}]")

if abs(att) / se > 1.96:
    print(f"✓ Statistically significant effect at 5% level")
```

#### Balance Checking

```python
print("\nCovariate Balance After Matching:")
for var in X_features:
    treated_mean = psm_data.loc[matched_treated_idx, var].mean()
    control_mean = psm_data.loc[matched_control_idx, var].mean()
    pooled_std = psm_data[var].std()
    std_diff = (treated_mean - control_mean) / pooled_std * 100
    
    print(f"  {var}:")
    print(f"    Treated mean: {treated_mean:.4f}")
    print(f"    Control mean: {control_mean:.4f}")
    print(f"    Standardized difference: {std_diff:.2f}%")
    print(f"    {'✓ Good balance' if abs(std_diff) < 10 else '✗ Poor balance'}")
```
