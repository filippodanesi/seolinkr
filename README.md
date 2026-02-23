# SEO Internal Linker

CLI tool for automated internal link insertion into blog articles (Markdown, DOCX, XLSX). Uses sitemap data, multilingual embeddings, Google Search Console metrics, and the Claude API to place semantically relevant internal links.

Built for multi-market e-commerce content workflows.

## Features

- **Embedding-based candidate matching** — multilingual sentence embeddings (`intfloat/multilingual-e5-small`) identify the most semantically relevant pages from your sitemap
- **Claude-powered link insertion** — Claude reads the article, selects natural anchor text, and inserts markdown links with reasoning for each placement
- **Google Search Console integration** — optional GSC data enriches candidates with impressions, clicks, and position to prioritize pages that benefit most from link equity
- **Atomic CLI commands** — composable pipeline (`candidates` → `link` → `audit`) that can be orchestrated by Claude Code or used individually
- **Cross-link detection** — finds linking opportunities between blog articles based on shared GSC search queries
- **Link audit** — validates output against configurable rules (minimum links, anchor text quality, heading restrictions, duplicate URLs)
- **Multi-format support** — Markdown, DOCX, and XLSX input/output
- **Caching** — page metadata (24h) and GSC data (48h) cached locally to minimize API calls

## Installation

```bash
# Basic install (no GSC)
pip install -e .

# With Google Search Console support
pip install -e ".[gsc]"
```

Requires Python 3.10+.

## Quick Start

### 1. Configure

```bash
# Set Anthropic API key
seo-linker config --api-key YOUR_KEY

# Save a sitemap for reuse
seo-linker add-sitemap my-site https://www.example.com/sitemap_index.xml

# Optional: configure GSC
seo-linker config --gsc-service-account /path/to/service-account.json
```

### 2. Process an article (one-shot)

```bash
seo-linker process article.md --sitemap my-site --max-links 10
```

This runs the full pipeline: parse → fetch sitemap → enrich pages → embedding prefilter → Claude linking → write output.

Output: `article_linked.md`

### 3. Composable workflow (for Claude Code orchestration)

```bash
# Step 1: Find and rank candidate pages
seo-linker candidates article.md --sitemap my-site --gsc-site "https://www.example.com/" --format json > candidates.json

# Step 2: Insert links using pre-computed candidates
seo-linker link article.md --candidates candidates.json --max-links 10

# Step 3: Audit the result
seo-linker audit article_linked.md --format json
```

## Commands

### Core pipeline

| Command | Description |
|---------|-------------|
| `process FILE` | Full pipeline — parse, match, link, write (backward-compatible) |
| `candidates FILE` | Find and rank candidate pages without inserting links |
| `link FILE --candidates JSON` | Insert links using a pre-computed candidates list |
| `audit FILE` | Validate links against CLAUDE.md rules |

### GSC intelligence

| Command | Description |
|---------|-------------|
| `opportunities --gsc-site SITE` | Show pages that benefit most from internal links |
| `cross-gaps --gsc-site SITE` | Find cross-linking opportunities between blog articles |
| `gsc-clear-cache` | Clear cached GSC data |

### Configuration

| Command | Description |
|---------|-------------|
| `config` | Set API key, model, GSC credentials, defaults |
| `add-sitemap NAME URL` | Save a sitemap with a short name |
| `remove-sitemap NAME` | Remove a saved sitemap |
| `list-sitemaps` | List all saved sitemaps |
| `analyze-sitemap URL` | Preview a sitemap's contents |

## GSC Integration

Google Search Console data adds an intelligence layer to candidate scoring:

- **Opportunity scoring** — pages with high impressions at position 4-15 get the highest scores (link equity can push them to top 3)
- **Cross-link detection** — finds pairs of blog articles that share search queries, indicating they should link to each other
- **Zero-cost enrichment** — GSC data is fetched in bulk (max 2 API calls per site), cached for 48 hours, and enrichment uses local lookup only

### Setup

1. Enable the [Search Console API](https://console.cloud.google.com/apis/library/searchconsole.googleapis.com) in Google Cloud Console
2. Create a service account and download the JSON key
3. Add the service account email as a user in your GSC property
4. Configure:

```bash
seo-linker config --gsc-service-account /path/to/service-account.json
```

### Usage

```bash
# Prioritized pages — which pages need internal links most?
seo-linker opportunities --gsc-site "https://www.example.com/" --format json

# Cross-linking gaps — which blog articles should link to each other?
seo-linker cross-gaps --gsc-site "https://www.example.com/" --url-pattern "/blog/" --format json

# Enrich candidates with GSC data
seo-linker candidates article.md --sitemap my-site --gsc-site "https://www.example.com/" --format json

# Full pipeline with GSC enrichment
seo-linker process article.md --sitemap my-site --gsc-site "https://www.example.com/"
```

## JSON Output

All new commands support `--format json` for machine consumption. When `--format json` is used, structured JSON goes to stdout and status messages go to stderr.

### `opportunities --format json`

```json
[
  {
    "url": "https://www.example.com/shoes/running",
    "impressions": 27137,
    "clicks": 850,
    "position": 7.6,
    "ctr": 0.031,
    "opportunity_score": 0.913,
    "priority": "high",
    "reason": "High impressions (27,137) at position 7.6 — link equity can push to top 3"
  }
]
```

### `candidates --format json`

```json
[
  {
    "url": "https://www.example.com/shoes/trail",
    "title": "Trail Running Shoes — Example Store",
    "meta_description": "Durable trail running shoes for all terrains...",
    "impressions": 51643,
    "clicks": 1686,
    "avg_position": 3.9,
    "opportunity_score": 0.82
  }
]
```

### `audit --format json`

```json
{
  "file": "article_linked.md",
  "total_links": 7,
  "category_links": 4,
  "magazine_links": 1,
  "product_links": 2,
  "external_links": 0,
  "issues": [],
  "links": [
    {
      "anchor_text": "trail running shoes",
      "target_url": "https://www.example.com/shoes/trail",
      "link_type": "category"
    }
  ]
}
```

## Project Structure

```
src/seo_linker/
├── cli.py                    # Click CLI — all commands
├── config.py                 # Config with JSON persistence (~/.seo-linker/)
├── models.py                 # TargetPage, ContentSection, LinkInsertion, LinkingResult
├── pipeline.py               # Full pipeline orchestrator
├── gsc/                      # Google Search Console module
│   ├── auth.py               # OAuth + service account authentication
│   ├── cache.py              # 48h TTL cache for GSC data
│   ├── client.py             # Bulk fetch, local lookup
│   ├── opportunities.py      # Page opportunity scoring
│   └── cross_linker.py       # Query overlap analysis
├── audit/
│   └── checker.py            # Link validation rules
├── linking/
│   ├── claude_linker.py      # Claude API integration
│   └── prompt_builder.py     # System + user prompt construction
├── matching/
│   ├── embeddings.py         # SentenceTransformer wrapper
│   └── prefilter.py          # Cosine similarity pre-filtering
├── parsers/                  # MD, DOCX, XLSX input parsers
├── sitemap/
│   ├── fetcher.py            # Recursive XML sitemap fetch
│   └── enricher.py           # Async page metadata enrichment
└── writers/                  # MD, DOCX, XLSX output writers
```

## Configuration

Config is stored at `~/.seo-linker/config.json`:

| Field | Default | Description |
|-------|---------|-------------|
| `api_key` | `""` | Anthropic API key (or set `ANTHROPIC_API_KEY` env var) |
| `default_model` | `claude-opus-4-6` | Claude model for link insertion |
| `max_links` | `10` | Maximum links per article |
| `top_n` | `40` | Candidate pages from embedding prefilter |
| `embedding_model` | `intfloat/multilingual-e5-small` | Sentence embedding model |
| `cache_ttl_hours` | `24` | Page metadata cache TTL |
| `gsc_service_account` | `""` | Path to GSC service account JSON |
| `gsc_oauth_secrets` | `""` | Path to GSC OAuth client secrets |
| `gsc_cache_ttl` | `48` | GSC data cache TTL (hours) |

## Testing

```bash
pip install pytest
pytest tests/ -v
```

Tests cover:
- GSC cache read/write/expiry/clear
- Opportunity scoring with known inputs
- Cross-link query overlap detection
- Audit rule validation
- Model `opportunity_score` property
- CLI JSON output validation

## Internal Linking Rules

See [CLAUDE.md](CLAUDE.md) for the complete internal linking ruleset that governs:
- Minimum link targets (3 category + 1 magazine cross-link)
- Anchor text requirements (descriptive, varied, never generic)
- Placement rules (first link within 200 words, never in headings)
- Market-specific domain restrictions
- GSC-informed prioritization

## License

MIT
