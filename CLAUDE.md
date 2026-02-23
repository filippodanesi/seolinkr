## 17. INTERNAL LINKING RULES

These rules apply to all Triumph Magazine articles. They govern how internal links are placed, what they point to, and how anchor text is written. The seo-linker tool enforces these rules programmatically; human writers and Claude Code should also follow them when creating or reviewing content.

### 17.1 Link targets — minimum requirements

- **Every article: minimum 3 links to category pages** (e.g. /bhs, /bhs/ohne-buegel, /bralette)
- **Every article: minimum 1 link to another magazine article** (cross-link)
- **Every product mention in "Top Picks" / "Unsere Top-Empfehlungen": direct PDP link** with clear CTA (e.g. "Entdecken →" or "[Product Name] entdecken →")
- **Bra size calculator link**: include in every article that discusses fit, sizing, or finding the right bra — link to the market-specific calculator URL

### 17.2 Anchor text

- **Descriptive, 2-4 words preferred**, containing the target page's primary keyword or a natural variation
- **Never generic**: "hier klicken", "mehr erfahren", "click here", "learn more" are never acceptable
- **Vary across the article**: mix exact-match keywords, partial matches, contextual phrases, and long-tail variations. If linking to /bhs/ohne-buegel, don't always use "BHs ohne Bügel" — also use "bügellose Modelle", "bequeme BHs ohne Bügel", "wire-free options"
- **Never rewrite sentences to create keyword-rich anchors**. Use phrases already present in the text

### 17.3 Placement

- **First internal link within the first 200 words** of the article
- **Maximum 2 links per paragraph, 1 link per sentence**
- **Never in headings** (H1-H6 / lines starting with #)
- **Concentrate links in the top two-thirds** of the article — readers scroll less in the bottom third, and link equity distribution favours earlier links
- **Links in FAQ answers are acceptable** but should be secondary to body-text links

### 17.4 Cross-linking between magazine articles

- **Every article must link to at least 1 related magazine article** in the same market
- **Cross-links are based on**: shared GSC queries (when data is available), thematic relevance (always), and complementary topics (e.g. cotton bra guide ↔ lace bra guide as comfort vs. aesthetics)
- **Place cross-links in the section most relevant** to the linked article's topic, not in a generic "related articles" block at the bottom
- **Cross-links should feel editorial, not mechanical**: integrate them into the narrative flow. Example: "For women who find cotton too plain, our [Spitzen-BH Guide](URL) explores how lace can deliver both beauty and comfort"

### 17.5 Market-specific rules

- **DE articles link to de.triumph.com URLs only**
- **UK articles link to uk.triumph.com URLs only**
- **EU, CH, SE, ES, PT, PL articles link to their respective subdomains**
- **Product recommendations may differ by market** — verify product availability on the target domain before linking to a PDP
- **Bra size calculator URL differs by market**:
  - DE: /bh-groessen-rechner-passform-guide
  - UK: /bra-size-calculator-fitting-guide
  - Verify the correct path for other markets

### 17.6 GSC-informed linking (when data is available)

- **Prioritize pages with opportunity score > 0.5** (high impressions + position 4-15) — these benefit most from internal link equity
- **Use GSC top queries as relevance signals**: if a candidate page's top queries overlap with the article's topic, it's a strong cross-link candidate
- **Pages with position < 4 are already strong**: link to them when semantically relevant, but don't prioritise them over pages that need the boost
- **GSC data is supplementary, not mandatory**: when no GSC data is available, use semantic relevance alone

---

## Pre-Publish Checklist — Internal Linking

- [ ] Are there at least 3 links to category pages?
- [ ] Is there at least 1 link to another magazine article (cross-link)?
- [ ] Does every product mention in "Top Picks" include a direct PDP link?
- [ ] Is the first internal link within the first 200 words?
- [ ] Are all anchor texts descriptive (no "hier klicken" or "mehr erfahren")?
- [ ] Are anchor texts varied (not all exact-match keywords)?
- [ ] Are there zero links inside headings?
- [ ] Do all links point to the correct market subdomain?
- [ ] Has the article passed `seo-linker audit --format json`?
