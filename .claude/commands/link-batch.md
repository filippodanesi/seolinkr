Batch process a directory of articles through the SEO internal linking pipeline.

## Instructions

1. Ask the user for:
   - The directory path containing article files
   - The sitemap URL(s)
   - File pattern to match (default: `*.md`)
   - Optional: GSC site, max links, top N

2. Find all matching files:
   ```
   find <directory> -name "<pattern>" -not -name "*_linked*"
   ```

3. Process each file sequentially:
   ```
   seo-linker process --file <path> --sitemap <url> [options]
   ```

4. After all files are processed:
   - Show a summary table: filename | links inserted | audit issues
   - Run audit on each `*_linked.md` output
   - Highlight any files that failed audit checks

5. Report total stats: files processed, total links inserted, pass/fail ratio.

## Arguments
$ARGUMENTS
