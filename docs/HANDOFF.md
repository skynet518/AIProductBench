# AIProductBench V0.1 — Handoff

## Current Objective

Ship AIProductBench V0.1 quickly as a credible public GitHub portfolio project.

The implementation should be small, functional, understandable, reproducible, and visually presentable.

## Confirmed V0.1 Definition

AIProductBench V0.1 contains:

- 10 test cases
- 2 evaluated LLMs
- 3 capability domains
- 1 LLM-as-Judge
- Token / Cost / Latency tracking
- leaderboard.html
- README.md
- sample_results.json

Anything materially beyond this definition is out of scope unless explicitly approved.

## Current Strategy

Use a minimal benchmark pipeline:

test cases
→ benchmark runner
→ two model responses
→ LLM-as-Judge
→ structured results
→ aggregated summary
→ sample_results.json
→ leaderboard.html

## Product Positioning

This project should demonstrate:

- model evaluation design
- LLM-as-Judge
- quantitative model comparison
- API integration
- Token / Cost / Latency awareness
- reproducible AI product experimentation

It should be understandable to recruiters, AI PMs, and engineers.

## Important Constraint

Do not present V0.1 as a scientifically comprehensive benchmark.

Position it honestly as an early lightweight practical benchmark.

## Implementation Preference

Prefer:

- simple files
- simple functions
- clear JSON schemas
- small dependency surface
- readable implementation

Avoid:

- large frameworks
- unnecessary classes
- databases
- web backends
- frontend frameworks
- deployment infrastructure
- multi-agent systems

## Execution Model

GPT is the planner / product architect / reviewer.

DeepSeek Flash through Codex CLI is the implementation executor.

When an important architecture or product decision is unclear, DeepSeek should stop and ask rather than invent scope.

## Current Status

DeepSeek Codex execution environment is configured and validated.

The AIProductBench repository is newly initialized and currently empty except for project instruction files.

## Next Milestone

Inspect the repository and propose the smallest viable V0.1 implementation plan.

Do not begin implementation before the plan is reviewed.

## Definition of Done

A new user can understand the repository, inspect the benchmark methodology, see example results, view leaderboard.html, and understand how to reproduce the benchmark.
