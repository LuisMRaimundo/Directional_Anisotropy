# Anisotropy regression fixture inspection (exploratory)

Non-golden exploratory report. Values are **not** strict regression references.

Fixtures: `corpus\fixtures\anisotropy_regression`

## alternating_up_down_same_axis

- Events: 6
- Transitions (horizontal, all parts): 5
- Config window_mode: `total`
- 2B: A=1.0000, R=0.4817, μ=1.5708, D=0.2000, τ=0.8000, flow_U=0.0000, flow_V=1.0000
- Note: Exploratory snapshot D=0.200, A=1.000, R=0.482.

## balanced_four_directions

- Events: 9
- Transitions (horizontal, all parts): 8
- Config window_mode: `total`
- 2B: A=1.0000, R=0.3950, μ=1.5708, D=0.1250, τ=0.8750, flow_U=0.0000, flow_V=1.0000
- Note: Exploratory snapshot D=0.125, A=1.000, R=0.395.

## contrary_motion_symmetric

- Events: 10
- Transitions (horizontal, all parts): 8
- Config window_mode: `total`
- 2B: A=1.0000, R=0.5122, μ=1.5708, D=0.0000, τ=1.0000, flow_U=0.0000, flow_V=1.0000
- Directional conflict: 0.0000
- Note: Exploratory snapshot D=0.000, A=1.000, R=0.512.

## dense_events_no_direction

- Events: 24
- Transitions (horizontal, all parts): 23
- Config window_mode: `total`
- 2B: A=1.0000, R=0.4489, μ=1.5708, D=0.0435, τ=0.9565, flow_U=0.0000, flow_V=1.0000
- Note: Many alternating events; concentration may stay moderate (R≈0.449) despite high n.

## directional_change_by_window

- Events: 16
- Transitions (horizontal, all parts): 15
- Config window_mode: `measures`
- Window `m1–m2`: A=1.0000, R=0.9377, μ=1.5708, flow_V=1.0000
- Window `m3–m4`: A=1.0000, R=0.9895, μ=1.5708, flow_V=1.0000
- Note: directional_change_by_window: windowed profile — compare D sign across measure windows (not flow_V; μ≈π/2).

## oblique_motion

- Events: 10
- Transitions (horizontal, all parts): 8
- Config window_mode: `total`
- 2B: A=1.0000, R=0.8668, μ=1.5708, D=1.0000, τ=0.0000, flow_U=0.0000, flow_V=1.0000
- Directional conflict: 0.0000
- Note: Exploratory snapshot D=1.000, A=1.000, R=0.867.

## parallel_ascending_parts

- Events: 10
- Transitions (horizontal, all parts): 8
- Config window_mode: `total`
- 2B: A=1.0000, R=0.9903, μ=1.5708, D=1.0000, τ=0.0000, flow_U=0.0000, flow_V=1.0000
- Directional conflict: 0.0000
- Note: Exploratory snapshot D=1.000, A=1.000, R=0.990.

## pitch_inversion_same_rhythm

- Events: 5
- Transitions (horizontal, all parts): 4
- Config window_mode: `total`
- 2B: A=1.0000, R=0.9903, μ=1.5708, D=-1.0000, τ=0.0000, flow_U=0.0000, flow_V=1.0000
- Note: Exploratory snapshot D=-1.000, A=1.000, R=0.990.

## sparse_strong_direction

- Events: 3
- Transitions (horizontal, all parts): 2
- Config window_mode: `total`
- 2B: A=1.0000, R=0.9996, μ=1.5708, D=1.0000, τ=0.0000, flow_U=0.0000, flow_V=1.0000
- Note: Exploratory snapshot D=1.000, A=1.000, R=1.000.

## static_repetition

- Events: 4
- Transitions (horizontal, all parts): 3
- Config window_mode: `total`
- 2B: A=nan, R=1.0000, μ=nan, D=0.0000, τ=0.0000, flow_U=nan, flow_V=nan
- Note: Repeated pitch: Δp=0 transitions; temporal symbolic motion, not registral drift.

## time_stretched_same_contour

- Events: 5
- Transitions (horizontal, all parts): 4
- Config window_mode: `total`
- 2B: A=1.0000, R=0.9903, μ=1.5708, D=1.0000, τ=0.0000, flow_U=0.0000, flow_V=1.0000
- Note: Exploratory snapshot D=1.000, A=1.000, R=0.990.

## transposed_same_contour

- Events: 5
- Transitions (horizontal, all parts): 4
- Config window_mode: `total`
- 2B: A=1.0000, R=0.9903, μ=1.5708, D=1.0000, τ=0.0000, flow_U=0.0000, flow_V=1.0000
- Note: Exploratory snapshot D=1.000, A=1.000, R=0.990.

## uniform_ascending_steps

- Events: 5
- Transitions (horizontal, all parts): 4
- Config window_mode: `total`
- 2B: A=1.0000, R=0.9903, μ=1.5708, D=1.0000, τ=0.0000, flow_U=0.0000, flow_V=1.0000
- Note: Monotone ascent: D≈1.000, high concentration (A≈1.000, R≈0.990); flow_V>0 does not imply ascent alone.

## uniform_descending_steps

- Events: 5
- Transitions (horizontal, all parts): 4
- Config window_mode: `total`
- 2B: A=1.0000, R=0.9903, μ=1.5708, D=-1.0000, τ=0.0000, flow_U=0.0000, flow_V=1.0000
- Note: Monotone descent: D≈-1.000; flow_V may still be positive when μ≈π/2 — use D for registral direction.
