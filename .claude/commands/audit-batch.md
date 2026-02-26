Batch audit all linked article files for CLAUDE.md compliance.

## Instructions

1. Ask the user for:
   - The directory path (default: current directory)
   - File pattern (default: `*_linked.md`)
   - Optional: site domain for link classification

2. Find all matching files:
   ```
   find <directory> -name "<pattern>"
   ```

3. Run audit on each file:
   ```
   seo-linker audit --file <path> --format json [--site-domain DOMAIN]
   ```

4. Collect results and display a summary table:
   - File | Total Links | Category | Magazine | Issues | Pass/Fail

5. For files with issues, list the top issues grouped by type:
   - `too_few_category_links`: which files need more category links
   - `missing_cross_link`: which files need cross-links
   - `generic_anchor`: which files have generic anchor text
   - `heading_link`: which files have links in headings

6. Report overall compliance rate: X/Y files pass all checks.

## Arguments
$ARGUMENTS
