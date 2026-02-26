Generate a GSC intelligence report with opportunities and cross-link gaps.

## Instructions

1. Ask the user for:
   - The GSC site URL (e.g., `sc-domain:example.com`)
   - Optional: days lookback (default 28), min impressions (default 100)
   - Optional: URL pattern for cross-link analysis (default `/magazine/|/magazin/`)

2. Fetch opportunities:
   ```
   seo-linker gsc opportunities --site <url> [--days N] [--min-impressions N]
   ```

3. Fetch cross-link gaps:
   ```
   seo-linker gsc cross-gaps --site <url> [--url-pattern PATTERN] [--days N]
   ```

4. Present the report in two sections:

   **Opportunity Ranking:**
   - Top 20 pages sorted by opportunity score
   - Group by priority: high, quick_win, medium
   - For each: URL, position, impressions, score, recommendation

   **Cross-Link Gaps:**
   - Top 20 cross-link opportunities sorted by relevance score
   - For each: source → target, shared queries, target metrics
   - Actionable suggestions: "In article X, add a link to article Y in the section about Z"

5. End with a summary: total high-priority opportunities, total cross-link gaps found, and recommended next actions.

## Arguments
$ARGUMENTS
