# UNIVERSAL SOFTWARE ENGINEERING PROTOCOL (PRACTICAL EDITION)

## Mission

Build, maintain, optimize, and repair software systems with:

* Maximum stability
* Minimum regressions
* Low CPU usage
* Low RAM usage
* High maintainability
* Evidence-based decisions

Applies to:

* Backend
* Frontend
* Mobile
* Desktop
* Embedded
* Linux / Windows / macOS

---

# 1. Core Principles

## Never Guess

Never assume:

* Architecture
* File contents
* APIs
* Dependencies
* Runtime behavior

Use evidence only.

---

## Source of Truth

The only valid sources are:

* Existing files
* Search results
* Build results
* Test results
* Logs
* Runtime behavior

---

## Golden Rule

Read
→ Verify
→ Plan
→ Edit
→ Verify
→ Build
→ Test

Never skip steps.

---

# 2. Discovery First

Before any modification:

1. Discover files
2. Search references
3. Read relevant code
4. Understand context
5. Plan changes
6. Modify

Required workflow:

Find
↓
Search
↓
Read
↓
Analyze
↓
Plan
↓
Edit

Never edit blindly.

---

# 3. Context Confidence Rule

Before implementation:

* If confidence < 90%
* Stop
* Read more files
* Ask questions
* Gather context

Never implement based on weak assumptions.

---

# 4. Planning Rule

Before coding:

Provide:

* Goal
* Constraints
* Risks
* Files affected
* Proposed solution

No direct implementation before analysis.

---

# 5. Impact Analysis

Before editing:

Identify:

* Files affected
* Dependencies affected
* APIs affected
* User-facing changes
* Regression risks

---

# 6. Edit First Policy

Prefer:

* Small edits
* Localized changes
* Existing architecture

Avoid:

* Full rewrites
* Massive refactors
* Unrelated modifications

---

# 7. File Protection

Forbidden:

* Full file replacement
* Deleting unrelated code
* Rebuilding files from memory

Required:

* Read first
* Preserve existing behavior
* Modify only intended sections

---

# 8. File Touch Budget

For a single task:

* Define target files first
* Avoid modifying unrelated files

If the same file is modified repeatedly:

1. Stop
2. Re-analyze
3. Find root cause

Do not endlessly patch.

---

# 9. Root Cause Rule

Always:

Identify
↓
Explain
↓
Fix
↓
Verify

Fix causes, not symptoms.

---

# 10. Build & Test

After every change:

* Build
* Lint
* Type check
* Run relevant tests

Do not declare success before verification.

---

# 11. Regression Prevention

For every change:

Ask:

* What could break?
* Which workflows are affected?
* Which tests cover this change?

Prevent regressions before they occur.

---

# 12. Performance First

Goals:

* Lower CPU usage
* Lower RAM usage
* Faster startup
* Faster response time

Prefer:

* Lazy loading
* Caching
* Streaming
* Efficient algorithms
* Memoization

Avoid unnecessary work.

---

# 13. Memory Budget Rule

Avoid:

* Large in-memory datasets
* Unlimited caches
* Duplicate objects
* Memory leaks

Prefer:

* Pagination
* Streaming
* Bounded caches
* Cleanup of temporary resources

Always consider memory lifetime.

---

# 14. CPU Usage Rule

Avoid:

* Heavy loops
* Repeated calculations
* Blocking operations

Prefer:

* Async processing
* Batching
* Caching
* Efficient data structures

---

# 15. Measure First Rule

Never optimize based on assumptions.

Use:

* Profiling
* Benchmarks
* Memory measurements
* CPU measurements

Measure before changing.

---

# 16. Dependency Rule

Add dependencies only when:

* Necessary
* Maintained
* Justified

Avoid dependency bloat.

Prefer existing project solutions.

---

# 17. Version Control Rule

Before updating dependencies:

1. Analyze impact
2. Check compatibility
3. Review changelog
4. Update minimally

Forbidden:

* Blind upgrades
* Large dependency jumps
* Removing lock files

Prefer incremental upgrades.

---

# 18. Generated Files Rule

Never manually edit:

* Generated code
* Build outputs
* Protobuf outputs
* Auto-generated bindings

Modify source files only.

---

# 19. Error Handling Rule

When a strategy fails:

1. Stop
2. Analyze cause
3. Change approach
4. Retry incrementally

Never repeat the same failed action.

---

# 20. Timeout Rule

If timeout occurs:

* Reduce scope
* Split work
* Retry incrementally

Do not rerun large operations unchanged.

---

# 21. Rollback Rule

Before risky changes:

Know:

* What changes
* How to revert
* Recovery procedure

Always maintain a rollback path.

---

# 22. Git Workflow

Use:

* Dedicated branches
* Small commits
* Clear commit messages

Before merge:

* Build passes
* Tests pass
* Review completed

---

# 23. Security Checklist

Always verify:

* Input validation
* Authentication
* Authorization
* Secrets handling
* Injection risks
* Data exposure

Security is never optional.

---

# 24. Linux Desktop Compatibility

Desktop applications should support:

### Desktop Environments

* GNOME
* KDE Plasma
* XFCE
* Cinnamon
* MATE
* Budgie
* LXQt
* DDE
* Pantheon

### Window Managers

* i3
* Sway
* Hyprland
* bspwm
* AwesomeWM
* Openbox

### Display Servers

* X11
* Wayland

Never assume a specific desktop environment.

---

# 25. Linux Standards

Prefer:

* XDG Base Directory
* Freedesktop standards
* Desktop Portals

Avoid hardcoded Linux paths.

Support:

* Flatpak
* Snap
* AppImage
* Native packages

---

# 26. UI/UX Standards

Prioritize:

* Responsiveness
* Accessibility
* Smooth rendering
* Low resource usage

Avoid:

* Excessive animations
* Unnecessary re-renders
* Heavy startup logic

---

# 27. Context Window Protection

For large projects:

Do not load everything.

Split into:

* Core
* UI
* Services
* Database
* Infrastructure

Work on one area at a time.

---

# 28. Multi-Agent Workflow

Planner

* Understand problem
* Compare approaches
* Create implementation plan

Architect

* Validate approach
* Reject over-engineering
* Ensure maintainability

Developer

* Implement approved solution
* Minimize changes
* Respect architecture

Reviewer

* Verify correctness
* Check performance
* Check security
* Prevent regressions

---

# 29. Completion Criteria

Task is complete only if:

✓ Requirements satisfied

✓ Build successful

✓ Tests passing

✓ No critical regressions

✓ Review completed

✓ Risks documented

✓ Results verified

---

# Final Principles

* Never Guess
* Read First
* Verify Always
* Plan Before Coding
* Fix Root Causes
* Build Often
* Test Early
* Keep Changes Small
* Preserve Existing Behavior
* Measure Before Optimizing
* Minimize RAM Usage
* Minimize CPU Usage
* Prevent Regressions
* Prefer Simplicity
* Prefer Stability
* Prefer Maintainability
* Always Keep a Rollback Path
* Deliver Verified Results Only

