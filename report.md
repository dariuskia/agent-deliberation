# Deliberation Mode Comparison — Experiment Report
Comparing centralized, clustered, and delegates deliberation modes across population sizes and questions.

---

## Experiment: 20260407_045115

**Grid:** 3 modes × 3 sizes × 1 questions × 1 trial(s)

- **Modes:** centralized, clustered, delegates
- **Population sizes:** 4, 10, 50
- **Questions:**
  - Is it ethical to use AI in the judicial system?
- **Rounds per deliberation:** 3

### Results Summary

| Mode | N | Question | Avg Sat | Min Sat | Bot. Quartile | Variance |
|------|---|----------|---------|---------|---------------|----------|
| centralized | 4 | Is it ethical to use AI in the judi | 9.0 | 9 | 9.0 | 0.00 |
| centralized | 10 | Is it ethical to use AI in the judi | 8.4 | 5 | 6.5 | 1.44 |
| centralized | 50 | Is it ethical to use AI in the judi | 8.6 | 6 | 7.4 | 0.61 |
| clustered | 4 | Is it ethical to use AI in the judi | 9.0 | 9 | 9.0 | 0.00 |
| clustered | 10 | Is it ethical to use AI in the judi | 8.8 | 8 | 8.0 | 0.16 |
| clustered | 50 | Is it ethical to use AI in the judi | 8.7 | 8 | 8.0 | 0.21 |
| delegates | 4 | Is it ethical to use AI in the judi | 9.0 | 9 | 9.0 | 0.00 |
| delegates | 10 | Is it ethical to use AI in the judi | 8.5 | 7 | 7.0 | 0.65 |
| delegates | 50 | Is it ethical to use AI in the judi | 8.4 | 6 | 7.2 | 0.76 |

### Aggregate by Mode (averaged across all questions & sizes)

| Mode | Avg Sat | Min Sat | Bot. Quartile | Variance |
|------|---------|---------|---------------|----------|
| centralized | 8.65 | 6.7 | 7.64 | 0.68 |
| clustered | 8.83 | 8.3 | 8.33 | 0.12 |
| delegates | 8.63 | 7.3 | 7.72 | 0.47 |

### Graphs

#### Inequality Scaling
![Inequality Scaling](runs/20260407_045115_graphs/inequality_scaling.png)

#### Metrics Comparison
![Metrics Comparison](runs/20260407_045115_graphs/metrics_comparison.png)

#### Satisfaction Distribution
![Satisfaction Distribution](runs/20260407_045115_graphs/satisfaction_distribution.png)

#### Scaling Curves
![Scaling Curves](runs/20260407_045115_graphs/scaling_curves.png)

### Key Findings

- **Highest average satisfaction:** clustered (8.83)
- **Best minority satisfaction:** clustered (8.33)
- **Most equitable (lowest variance):** clustered (0.12)

**Scaling trends (N=4 → N=50):**
- centralized: 9.0 → 8.6 (↓0.4)
- clustered: 9.0 → 8.7 (↓0.3)
- delegates: 9.0 → 8.4 (↓0.6)

---

