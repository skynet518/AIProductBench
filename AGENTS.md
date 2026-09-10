# AIProductBench — Project Instructions

## Product Goal

AIProductBench is a lightweight, reproducible benchmark project for comparing LLMs from an AI product management perspective.

The immediate goal is to ship a credible public V0.1 quickly.

This is not intended to become a full evaluation framework in V0.1.

## V0.1 Fixed Scope

V0.1 contains exactly:

- 10 test cases
- 2 evaluated models
- 3 capability domains
- 1 LLM-as-Judge
- token tracking
- cost tracking
- latency tracking
- leaderboard.html
- README.md
- sample_results.json

Do not expand this scope unless explicitly instructed.

## Product Principles

Prioritize:

1. working end-to-end execution
2. reproducibility
3. readable benchmark design
4. credible GitHub presentation
5. minimal implementation complexity

Avoid unnecessary abstraction and premature extensibility.

## Evaluation

One LLM-as-Judge evaluates model responses using an explicit scoring rubric.

Judge output must be machine-readable.

Do not introduce multiple judges, voting, tournaments, or complex statistical evaluation in V0.1.

## Metrics

For every evaluated response, record when available:

- score
- input tokens
- output tokens
- total tokens
- estimated cost
- latency
- model
- test case
- capability domain

Never fabricate missing provider metrics.

## Engineering Constraints

Prefer Python for benchmark execution.

Keep dependencies minimal.

Prefer structured JSON for inputs and outputs.

Do not add databases, authentication, containers, cloud infrastructure, dashboards, or frontend frameworks unless explicitly requested.

## Git Safety

Do not push to GitHub unless explicitly instructed.

Do not rewrite history.

Do not merge or delete branches.

Do not commit credentials.

Before completion inspect:

- git status
- git diff

## Validation

V0.1 validation should establish that:

- all 10 cases can be loaded
- exactly 2 evaluated models are configured
- exactly 3 domains exist
- judge output parses correctly
- result JSON is valid
- leaderboard generation works
- sample_results.json is valid
- leaderboard.html opens standalone
- README matches the implementation

## Scope Control

If a feature is useful but unnecessary for V0.1, do not implement it.

Record it as a future improvement instead.
