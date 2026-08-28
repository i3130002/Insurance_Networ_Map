# Mistakes

- 2026-08-28: Firecrawl could not resolve `api.firecrawl.dev` while fetching the ASD-STE100 site. Switched to the available official web reader.
- 2026-08-28: The skill initializer command used `python`, which is unavailable in this environment. Use `python3`.

- 2026-08-28: The first subagent delegation attempt failed because the inherited model name was unavailable. Retry with an explicitly available lightweight model.
- 2026-08-28: Node could not check JavaScript piped through `/dev/stdin` in this PTY environment. Use a temporary extracted script file for syntax checks.
- 2026-08-28: The first Node inline regex check was over-escaped and failed to parse. Use simple string splitting for the inline check.
- 2026-08-28: Network assignments used raw-registry indexes while plan files used generated-registry indexes. The validator caught 9,333 mismatches; assignments now use the generated registry.
- 2026-08-28: The Nominatim backlog run stalled on network timeouts before its first checkpoint and was interrupted. The geocoder remains resumable; use a reachable geocoding service or smaller batches.
- 2026-08-28: A follow-up commit failed because the main workspace exposes `.git` as read-only. The timeout note remains uncommitted.
- 2026-08-28: The escalated geocoding batch was rejected because it would send provider names and addresses to Nominatim. A single read-only connectivity test succeeded.
- 2026-08-28: The approved geocoding run completed, but staging its outputs failed because the main workspace `.git` remains read-only. Attempt a focused commit through the writable agent workspace.
- 2026-08-28: The focused commit attempt failed because Git could not create `.git/index.lock`; retry with escalated permission.
- 2026-08-28: The objectives commit attempt failed because Git could not create `.git/index.lock` in the read-only repository metadata. Retry with escalated permission.
