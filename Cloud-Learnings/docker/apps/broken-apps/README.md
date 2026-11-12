# Broken Apps

These are deliberately broken applications for debugging practice.

## broken-api

A FastAPI application with intentional bugs. Use it to practice:
- Reading Python exception tracebacks
- Identifying missing environment variables
- Finding configuration errors
- Diagnosing startup failures

### How to use

1. Build the broken-api image
2. Try to start it — it will fail
3. Read the logs to find the bug
4. Fix the bug in `broken-api/app.py`
5. Rebuild and verify it works

### Bugs injected (spoiler — try yourself first)

- Missing required environment variable
- Wrong database port
- Import that doesn't exist (typo)
- Unhandled exception on /health endpoint

See `solution/README.md` for the fixes.
