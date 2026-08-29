# Mistakes

- 2026-08-29: The local commit could not create `.git/index.lock` because the
  repository metadata is read-only. The project files remain in the worktree.

- 2026-08-29: The published GitHub Pages URL returned HTTP 404 during the
  release smoke test. The repository is locally valid, but deployment is not
  currently available at the documented URL.

- 2026-08-29: The full Zavis retry exceeded the practical run time while page
  requests were still pending. It was interrupted before the extractor wrote
  its output; keep the existing source until a bounded retry is implemented.
- 2026-08-29: The first bounded Zavis sample still fetched every category because
  `--max-pages` only limited pagination. Add `--max-categories` to bound the
  category-first-page requests as well.
- 2026-08-29: The one-category Zavis sample completed with zero records because
  that category response was unavailable or did not match the parser. Do not
  use the sample as refreshed source data.

- 2026-08-29: A combined UI/documentation patch did not apply because the
  expected duplicate assignment was not present. Re-read the exact lines and
  applied the changes in a narrower patch.

- The completed Zavis crawl had seven pages return temporary HTTP 503 responses; the output contains 11,499 deduplicated records and those URLs should be retried on the next refresh.

- A diagnostic command used a misspelled tool name (`execartement`) and did not run; no project files were changed.

- The full Zavis crawl stopped when a category root returned HTTP 503; category and pagination fetches now use the same non-aborting retry path as detail pages.

- The expanded Zavis parser test initially used one extra escaping layer and failed to find its synthetic provider card; the fixture is being corrected.

- The first Zavis extractor run hit sandbox DNS failure; rerun the public fetch with network escalation.
- Zavis returned HTTP 503 during the first parallel pass; the extractor now retries and records failed URLs instead of aborting the batch.

- Zavis Firecrawl mapping could not start because the wrapper requires Podman, while this environment only exposed Docker Compose. The shared Firecrawl service itself started successfully.

- Validation failed after changing phone matching because generated plan files had not been rebuilt, and `GN+` initially collided with `GN` in the slugifier. Both issues are being corrected before the next validation run.
- Git staging failed with `confused by unstable object source data`; the generated files remain in the worktree and will be staged again after checking repository state.

- 2026-08-28: The first skill-file lookup treated catalog aliases as literal subdirectories. Use the mapped skill roots directly.

- 2026-08-28: Firecrawl could not resolve `api.firecrawl.dev` while fetching the ASD-STE100 site. Switched to the available official web reader.
- 2026-08-28: The skill initializer command used `python`, which is unavailable in this environment. Use `python3`.

- 2026-08-28: The first subagent delegation attempt failed because the inherited model name was unavailable. Retry with an explicitly available lightweight model.
- 2026-08-28: Node could not check JavaScript piped through `/dev/stdin` in this PTY environment. Use a temporary extracted script file for syntax checks.
- 2026-08-28: The first Node inline regex check was over-escaped and failed to parse. Use simple string splitting for the inline check.
- 2026-08-28: Network assignments used raw-registry indexes while plan files used generated-registry indexes. The validator caught 9,333 mismatches; assignments now use the generated registry.
- 2026-08-28: The Nominatim backlog run stalled on network timeouts before its first checkpoint and was interrupted. The geocoder remains resumable; use a reachable geocoding service or smaller batches.
- 2026-08-28: A follow-up commit failed because the main workspace exposes `.git` as read-only. The timeout note remains uncommitted.
- 2026-08-28: Objectives-document delegation hit the subagent thread limit. Apply the small documentation update locally if needed.
- 2026-08-28: ADNIC official assignments initially included providers outside each plan's emirate scope. The validator caught 850 mismatches; the assignment guard now applies the plan scope to official matches.
- 2026-08-28: The escalated geocoding batch was rejected because it would send provider names and addresses to Nominatim. A single read-only connectivity test succeeded.
- 2026-08-28: The approved geocoding run completed, but staging its outputs failed because the main workspace `.git` remains read-only. Attempt a focused commit through the writable agent workspace.
- 2026-08-28: The focused commit attempt failed because Git could not create `.git/index.lock`; retry with escalated permission.
- 2026-08-28: The objectives commit attempt failed because Git could not create `.git/index.lock` in the read-only repository metadata. Retry with escalated permission.
- 2026-08-28: The requested `.gitignore` commit failed because Git could not create `.git/index.lock`; repository metadata is read-only.
- 2026-08-28: Manual removal of generated geocoder fields left trailing commas in two JSON objects. Validate generated JSON after targeted cleanup.
- 2026-08-28: Direct export of a public Takaful Emarat SharePoint workbook returned HTTP 403; retain the official source link and do not infer network membership.
- 2026-08-28: The full Nominatim retry completed with zero additional accepted coordinates; remaining backlog needs better source data.
- 2026-08-28: The first NAS workbook parser used the wrong header row and extracted zero coordinates. Detect the header row after title rows before parsing spreadsheet columns.
- 2026-08-28: The geocoder backlog count was read before the deduplication fix, reporting 174 instead of the final 189. Rebuild generated data before publishing counts.
- 2026-08-28: Takafol's exact SharePoint link and its resolved `NEXTCARE - GN+.xlsx` path both returned HTTP 403 with `download=1`; link-suffix changes cannot bypass the tenant access policy.
- 2026-08-28: Two direct-link patch attempts missed the existing JavaScript context. Inspect exact source lines before applying a narrow patch.
- 2026-08-28: An older geocoder process overlapped a newer source refresh and overwrote registry state. Do not run concurrent writers against `sources/merged-registry.json`.
- 2026-08-28: The ADNIC accuracy check exposed that official plans still contained all emirate providers instead of only official matches. Keep plan-file membership aligned with official assignment layers.
- 2026-08-29: Node `--check` with process substitution tried to open a transient `/proc` pipe. Extract inline JavaScript to a temporary file before syntax checking.
- 2026-08-29: The first interactive SharePoint navigation exceeded the 60-second browser timeout. Bound page navigation separately and inspect partial page state before retrying.
- 2026-08-29: Browser-agent inspection of the completed workbook download hung and had to be interrupted; the browser confirmed the filename but did not expose a transferable local path.
- 2026-08-29: A Playwright download-event capture hung while clicking Excel Online controls. Use the browser agent’s successful download action, but do not assume its remote path is transferable.
- 2026-08-29: The browser session expired before its remote download could be transferred. Reopen the workbook and inspect the download directory in the same session.
- 2026-08-29: The reopened browser reported a Downloads URL but its Playwright filesystem had no `/home/user/Downloads` directory. Treat the Firecrawl download as remote-only unless the tool exposes an artifact transfer.
- 2026-08-29: Capturing the Office iframe download event timed out even after locating the correct frame. The browser agent can click Download a Copy, but Firecrawl does not reliably expose the resulting binary to the workspace.
- 2026-08-29: The captured Playwright download path was not readable from a later browser interaction, so transferring it through separate calls failed. Capture and read the artifact within one browser execution.
- 2026-08-29: The in-session transfer script reused the persistent REPL binding `fs`, causing a redeclaration error. Use unique binding names for browser transfer variables.
- 2026-08-29: The iframe download-event transfer timed out after the menu item was clicked; Excel’s browser download is not consistently observable by Playwright in this session.
- 2026-08-29: The captured Excel download endpoint returned a 1,466-byte HTML internal-error page with HTTP 200, not an XLSX. Verify MIME/signature before accepting browser downloads.
- 2026-08-29: The general web tool followed a Takafol SharePoint workbook link into a Microsoft login redirect and could not fetch the workbook. Use the rendered Excel browser route for public page inspection.
- 2026-08-29: Local Brave headless navigation hung on the SharePoint workbook and produced no download. The user’s interactive Brave session may succeed because it has a full GUI/private profile unavailable to this agent.
- 2026-08-29: The first local Brave automation script used an incorrect Puppeteer ESM path. Resolve the installed package entry point before launching the batch.
- 2026-08-29: Reusing the `frame` binding in the persistent browser REPL caused a redeclaration syntax error. Use unique binding names for each interaction call.
- 2026-08-28: The first Zavis batch exited without producing its result file. Add a hard timeout and verify the output file before treating a public-directory run as complete.
- 2026-08-28: Direct urllib access to Zavis returned HTTP 403; use the approved browser/scraping path for JS-rendered public pages instead of assuming raw HTTP access.
- 2026-08-28: The general web opener rejected the Zavis query URL as unsafe. Use the Firecrawl CLI for this site instead.
- 2026-08-28: A multi-URL Firecrawl CLI call saved both pages to the same generated filename and did not honor the requested output path. Use one URL per call or isolate output directories.
- 2026-08-28: Concurrent Firecrawl subprocesses produced no batch output, and an isolated subprocess returned an error while the direct CLI invocation worked. Keep Firecrawl calls in the controlling shell and verify each saved artifact.
- 2026-08-29: Chromium Flatpak tests with `--download-directory` and an X11 GUI opened the Excel workbook but produced no local XLSX. Treat the native Excel download action as unresolved until a manually confirmed save is available.
- 2026-08-29: Pi's Playwright browser tool could not initialize because `/opt/google/chrome/chrome` is absent. Do not install a browser for this task; use the existing Chromium CDP session instead.
- 2026-08-29: Retesting Pi's Playwright browser produced the same missing-Chrome initialization error before page navigation.
- 2026-08-29: Attempting to stage the Takafol XLSX was rejected by the intentional `*.xlsx` ignore rule. Keep raw workbooks local and export tracked normalized CSV data.
- 2026-08-29: The user’s live Brave session differs from isolated automation profiles: direct download succeeds interactively, while isolated sessions receive zero-byte artifacts. Attach to the live browser or use its chosen download folder for reliable bulk capture.
- 2026-08-29: The UI flow contract test correctly failed before the separate company selector was implemented; keep the test as the regression contract.
- 2026-08-29: The first post-implementation UI contract run used a selector-variable assertion that did not match the DOM lookup style. Assert the actual event-binding expression.
- 2026-08-29: Opening all Takafol direct-download links together triggered blocking. Process one link at a time with a delay and verify each completed file before continuing.
- 2026-08-29: The first direct Playwright-with-Brave test failed from shell quoting before launch. Use a temporary script for browser tests with nested selectors.
- 2026-08-29: The corrected Playwright-with-Brave script used a named ESM import against a CommonJS package and failed before launch. Use the package default export.
- 2026-08-29: Playwright captured the Excel download in Brave, but `download.saveAs()` pointed to a vanished temporary path. Copy the download stream directly while the browser session is open.
- 2026-08-29: Reading the Playwright download stream immediately returned a zero-byte file. Wait for `download.failure()` and `download.path()` before copying the completed artifact.
- 2026-08-29: Direct `download=1` triggered Brave's download event, but Playwright's temporary artifact path was absent when copied. Test the completed download stream as the transfer path.
- 2026-08-29: The direct SharePoint download event returned zero bytes through Playwright's stream. Check Brave's own download directory separately before classifying the response as empty.
## 2026-08-29

- `python3 -m unittest test_takafol_import.py` failed before the importer existed; the new test correctly exposed the missing implementation.
- A combined documentation patch did not apply because one expected paragraph had changed; no files were modified by that failed patch.
- 2026-08-29: The first documentation commit failed because the sandbox could not create `.git/index.lock`; retry Git metadata operations with elevated permission.
- 2026-08-29: The local HTTP smoke test could not bind a socket because the sandbox denies network listeners. Validate static files directly and run the HTTP check in a permitted environment.
## 2026-08-29

- The `pytest` launcher failed because its interpreter does not exist. Use the
  available Python test runner until the environment is repaired.
