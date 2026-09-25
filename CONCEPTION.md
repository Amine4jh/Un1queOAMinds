# Change Impact Analysis with IBM Bob 2.0

## 1. Project Name

**Bob Change Impact Mode**

## 2. Problem

Today, when a developer wants to change existing code, they must explore the code manually to understand what will be affected. This process is slow, and it is easy to miss important dependencies. Bugs often appear only after the change is merged.

## 3. Goal

Build a tool that uses IBM Bob 2.0 to:

1. Analyze the impact of a code change before it is made.
2. Show the risks clearly.
3. Create a step-by-step plan.
4. Execute the approved change.
5. Test the result and report back.

This turns a slow **explore → modify → discover-breakage** process into a clear **analyze → execute → validate** workflow.

## 4. Users

- Developers who need to change existing code.
- Code reviewers who want a clear risk summary before approving a change.

## 5. System Overview

```
Developer
   │
   ▼
Change Request
   │
   ▼
Bob Change Impact Mode
   │
   ├── Dependency Agent
   ├── Database Agent
   └── Test Agent
   │
   ▼
Impact + Risk Summary
   │
   ▼
Implementation Plan
   │
   ▼
Human Approval
   │
   ▼
Bob Executes (Edit → Test → Debug → Retest)
   │
   ▼
Final Report (Git diff + Test results)
```

## 6. Agents

### 6.1 Dependency Agent

- **Input:** Change request + repository
- **Output:** List of modules and files that are affected
- **Task:** Find code that depends on the part being changed

### 6.2 Database Agent

- **Input:** Change request + repository
- **Output:** List of database tables or schema parts affected
- **Task:** Check if the change touches stored data

### 6.3 Test Agent

- **Input:** Change request + repository
- **Output:** List of tests that may be affected
- **Task:** Find existing tests linked to the changed code

## 7. Impact + Risk Summary

Combine the outputs of the three agents into one summary. Each item gets a risk level:

| Risk Level | Meaning                     |
| ---------- | --------------------------- |
| 🔴 High    | Core shared logic affected  |
| 🟠 Medium  | Several modules affected    |
| 🟡 Low     | A few tests may be affected |

## 8. Implementation Plan

Bob generates a clear, numbered list of steps needed to make the change. Example:

1. Modify the core service
2. Add the new component (e.g., PayPal adapter)
3. Update the API
4. Update data storage
5. Update affected tests
6. Run regression checks

## 9. Human Approval

Before Bob makes any change, the user must approve the plan. This keeps the developer in control and builds trust.

## 10. Execution

Once approved, Bob:

1. Edits the code
2. Runs the tests
3. If a test fails, Bob tries to fix it **once**
4. If it still fails, Bob stops and reports the problem clearly

We do not try to make Bob fully autonomous. This keeps the demo safe and realistic.

## 11. Final Report

The final output includes:

- Git diff of all changes
- Test results (pass/fail)
- A short summary of what was done

## 12. Frontend

A simple, single-page interface:

1. User types a change request
2. Each pipeline stage appears live, with real data (no fake steps)
3. Final view shows the diff and test results

The frontend only displays real agent output. It does not simulate results.

## 13. Success Criteria

- The pipeline runs on a real (or sample) repository
- The risk summary is accurate and useful
- The plan is clear and logical
- At least one full change is executed and tested successfully
- The demo shows real, live output — not mock data

## 14. Scope for the Hackathon

To fit the 48-hour timeframe:

- Use one small demo repository (e.g., a payment module)
- Test the full execution flow on **one** example change (e.g., adding PayPal support)
- If the execution step is not stable, fall back to showing only the analysis and plan, with execution demonstrated on a single pre-tested case

## 15. Business Value

- Fewer bugs after code changes
- Faster code reviews (reviewers get a ready risk map)
- Easier onboarding for new developers
- Useful for every change request, not just one-time projects
