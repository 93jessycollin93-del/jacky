# Prompt Templates

Reusable prompt fragments for common situations.

---

## 1. Plan-and-Execute Bootstrap

```
You are working on: {TASK}

First, produce a numbered plan (5 steps max). Then execute each step one at a
time. After each step, state what you observed. If a step fails, explain why
and try an alternative. After all steps, write a one-paragraph summary.
```

---

## 2. Code Review Request

```
Review the following code for: correctness, security, performance, and style.
File: {FILE_PATH}

For each issue found, state:
- Severity: BLOCKER | MAJOR | MINOR | NIT
- Location: line number
- Description: what is wrong
- Suggestion: how to fix it

```{code}
```
```

---

## 3. Bug Report → Investigation

```
Bug report: {SYMPTOM}

Steps to reproduce:
1. {STEP_1}
2. {STEP_2}

Expected: {EXPECTED}
Actual: {ACTUAL}

Investigate the root cause. Form 3 hypotheses and test each. Report the root
cause and the minimal fix.
```

---

## 4. Thermal-Aware Routing Prompt

```
The current GPU temperature is {GPU_TEMP}°C.
- If ≥ 75°C: refuse the request and ask the user to wait for cooling.
- If 70–74°C: use the smallest capable model (phi3, gemma2:2b).
- If < 70°C: proceed normally.
```

---

## 5. Chain-of-Thought Verification

```
Before giving your final answer, verify:
1. Does the answer directly address the question asked?
2. Are all facts accurate (cite sources if possible)?
3. Is the answer complete (no missing steps)?
4. Is there a simpler or cheaper way to achieve the same result?

If any check fails, revise your answer before responding.
```
