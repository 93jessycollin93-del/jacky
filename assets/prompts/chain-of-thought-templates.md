# Chain-of-Thought Prompt Templates

A collection of reusable CoT prompts for OmniAgent.

---

## 1 — Bug Investigation

```
You are debugging a bug. Think step by step:

1. What is the observed behaviour?
2. What is the expected behaviour?
3. What are the possible causes? (list at least 3)
4. What is the most likely cause and why?
5. What is the minimal change to fix it?
6. What test would catch this bug in the future?
```

---

## 2 — Code Review

```
Review the following diff. For each issue found:
- Severity: Critical / Major / Minor / Nit
- Location: file:line
- Description: what is wrong
- Suggestion: how to fix it

Focus on: correctness, security, performance, maintainability.
Ignore: style nits already caught by linters.
```

---

## 3 — Architecture Decision

```
I need to decide between the following options:
<OPTIONS>

For each option, evaluate:
1. Does it meet the functional requirements?
2. What are the performance implications?
3. What are the security implications?
4. How complex is the implementation?
5. How easy is it to reverse this decision?

Recommendation: <best option and why>
```

---

## 4 — Root Cause Analysis (5-Whys)

```
Problem: <describe the problem>

Why 1: Why did this happen?
Why 2: Why did that happen?
Why 3: Why did that happen?
Why 4: Why did that happen?
Why 5: Why did that happen?

Root cause: <final answer>
Corrective action: <what to change to prevent recurrence>
```

---

## 5 — Security Review

```
Review the following code for security vulnerabilities.
Check for:
- Injection (SQL, command, LDAP, XPath)
- Broken authentication / session management
- Sensitive data exposure
- SSRF / open redirects
- Insecure deserialization
- Dependency vulnerabilities
- Hardcoded secrets

For each finding: severity (Critical/High/Medium/Low), OWASP category,
line reference, and recommended fix.
```
