# Mistakes

- 2026-08-28: The first subagent delegation attempt failed because the inherited model name was unavailable. Retry with an explicitly available lightweight model.
- 2026-08-28: Node could not check JavaScript piped through `/dev/stdin` in this PTY environment. Use a temporary extracted script file for syntax checks.
- 2026-08-28: The first Node inline regex check was over-escaped and failed to parse. Use simple string splitting for the inline check.
- 2026-08-28: Network assignments used raw-registry indexes while plan files used generated-registry indexes. The validator caught 9,333 mismatches; assignments now use the generated registry.
