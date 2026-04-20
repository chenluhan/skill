# AI Review

Use this file only when the PRD clearly includes AI-generated output, AI recommendation, AI understanding, AI automation, or model-dependent behavior.
Do not force this section into a non-AI PRD.

## Table of Contents

- 1. Decide whether AI is really in scope
- 2. Check the input contract
- 3. Check the output contract
- 4. Check uncertainty, failure, and fallback
- 5. Check latency, cost, and control
- 6. Check safety, privacy, and policy
- 7. Check evaluation and launch gates

## 1. Decide Whether AI Is Really In Scope

Ask first:

- Is AI central to the user value, or is it decorative?
- Would a non-AI rule-based version solve the immediate problem more safely?
- Is the PRD using AI language as branding while the actual feature is deterministic?

If AI is not a real dependency, say so and avoid expanding the review with irrelevant AI theory.

## 2. Check The Input Contract

Check whether the PRD defines:

- what the model receives
- input limits, formatting, and invalid input behavior
- whether context comes from user input, history, retrieval, tools, or templates
- whether the user can edit or preview the input before generation or submission

Common gap:

- the PRD says "call model" without defining what context the model sees

## 3. Check The Output Contract

Check whether the PRD defines:

- what form the output takes
- what minimum quality bar makes the output usable
- whether the result is editable
- whether the result can be regenerated, refined, or rejected
- whether confidence, rationale, or citation is needed

Common gap:

- the PRD expects deterministic output from a probabilistic system

## 4. Check Uncertainty, Failure, And Fallback

Check whether the PRD defines:

- hallucination or wrong-answer handling
- empty, unsafe, low-confidence, or partial outputs
- timeout and retry behavior
- fallback to template, manual flow, search, or human support
- visible explanation when the system cannot complete the task

Mark `致命缺失` when the user could receive harmful, unusable, or silently wrong output with no fallback path.

## 5. Check Latency, Cost, And Control

Check whether the PRD defines:

- expected wait experience
- cancel behavior during generation
- whether generation can continue in background
- limits on regenerate, tool calls, or long sessions
- cost-sensitive constraints that affect UX or entitlement

Common gap:

- the PRD treats AI response time like a normal synchronous API call

## 6. Check Safety, Privacy, And Policy

Check whether the PRD defines:

- sensitive input handling
- storage, deletion, and retention rules
- moderation or policy filters
- abuse, prompt injection, or unsafe content controls when relevant
- user-facing disclosure when content is generated or uncertain

## 7. Check Evaluation And Launch Gates

Check whether the PRD defines:

- quality metrics in addition to business metrics
- failure-rate or fallback-rate metrics
- manual review or shadow mode before full release
- no-go conditions when quality is below threshold

Do not accept "we will optimize later" as a substitute for launch evaluation.
