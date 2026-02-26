Process a single article through the full SEO internal linking pipeline.

## Instructions

1. Ask the user for:
   - The article file path (markdown, docx, or xlsx)
   - The sitemap URL(s) — check `seo-linker config` for saved sitemaps first
   - Optional: current URL of the article, GSC site, max links, top N candidates

2. Run the pipeline:
   ```
   seo-linker process --file <path> --sitemap <url> [--max-links N] [--top-n N] [--current-url URL] [--gsc-site SITE]
   ```

3. After the pipeline completes:
   - Show the link report (anchor text → target URL + reasoning)
   - Run `seo-linker audit` on the output file to verify CLAUDE.md compliance
   - If audit issues exist, summarize them and suggest fixes

4. If the user wants HTML output or content rewriting, add the appropriate flags:
   - `--rewrite` for content optimization before linking
   - `--generate-html` for SEO title and meta description

## Arguments
$ARGUMENTS
