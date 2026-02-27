// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
/* Typed fetch client and SSE consumer for the FastAPI backend. */

import type {
  AppConfig,
  AuditResult,
  CandidatePage,
  CrossLinkOpportunity,
  Opportunity,
  SSEEvent,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

/* ── Health check ────────────────────────────────────────────── */

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

/* ── Audit ───────────────────────────────────────────────────── */

export async function auditFile(
  file: File,
  siteDomain?: string
): Promise<AuditResult> {
  const form = new FormData();
  form.append("file", file);
  if (siteDomain) form.append("site_domain", siteDomain);
  return fetchJSON<AuditResult>("/audit", { method: "POST", body: form });
}

/* ── Candidates ──────────────────────────────────────────────── */

export async function getCandidates(
  file: File,
  sitemaps: string,
  topN = 40,
  gscSite?: string
): Promise<CandidatePage[]> {
  const form = new FormData();
  form.append("file", file);
  form.append("sitemaps", sitemaps);
  form.append("top_n", String(topN));
  if (gscSite) form.append("gsc_site", gscSite);
  return fetchJSON<CandidatePage[]>("/candidates", {
    method: "POST",
    body: form,
  });
}

/* ── Pipeline (SSE) ──────────────────────────────────────────── */

export async function runPipeline(
  file: File,
  sitemaps: string,
  opts: {
    maxLinks?: number;
    topN?: number;
    model?: string;
    currentUrl?: string;
    gscSite?: string;
    brandGuidelines?: string;
    enableRewrite?: boolean;
    contentType?: string;
    rewriteInstructions?: string;
    generateHtml?: boolean;
    brandName?: string;
    signal?: AbortSignal;
  },
  onEvent: (event: SSEEvent) => void,
  onDone: () => void
): Promise<void> {
  const form = new FormData();
  form.append("file", file);
  form.append("sitemaps", sitemaps);
  if (opts.maxLinks) form.append("max_links", String(opts.maxLinks));
  if (opts.topN) form.append("top_n", String(opts.topN));
  if (opts.model) form.append("model", opts.model);
  if (opts.currentUrl) form.append("current_url", opts.currentUrl);
  if (opts.gscSite) form.append("gsc_site", opts.gscSite);
  if (opts.brandGuidelines)
    form.append("brand_guidelines", opts.brandGuidelines);
  if (opts.enableRewrite) form.append("enable_rewrite", "true");
  if (opts.contentType) form.append("content_type", opts.contentType);
  if (opts.rewriteInstructions)
    form.append("rewrite_instructions", opts.rewriteInstructions);
  if (opts.generateHtml) form.append("generate_html", "true");
  if (opts.brandName) form.append("brand_name", opts.brandName);

  const res = await fetch(`${API_BASE}/process`, {
    method: "POST",
    body: form,
    signal: opts.signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(`API ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = line.slice(6);
      if (payload === "[DONE]") {
        onDone();
        return;
      }
      try {
        onEvent(JSON.parse(payload) as SSEEvent);
      } catch {
        // skip malformed JSON
      }
    }
  }
  onDone();
}

/* ── Sitemap ─────────────────────────────────────────────────── */

export async function listSitemaps(): Promise<Record<string, string>> {
  return fetchJSON<Record<string, string>>("/sitemaps");
}

export async function analyzeSitemap(
  url: string
): Promise<{
  url: string;
  total_pages: number;
  sample_urls: string[];
  has_products: boolean;
  product_count: number;
  category_count: number;
}> {
  return fetchJSON("/sitemaps/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
}

/* ── GSC ─────────────────────────────────────────────────────── */

export async function getOpportunities(
  siteUrl: string,
  days = 28,
  minImpressions = 100
): Promise<Opportunity[]> {
  const params = new URLSearchParams({
    site_url: siteUrl,
    days: String(days),
    min_impressions: String(minImpressions),
  });
  return fetchJSON<Opportunity[]>(`/gsc/opportunities?${params}`);
}

export async function getCrossGaps(
  siteUrl: string,
  urlPattern = "/magazine/|/magazin/",
  days = 28,
  minSharedQueries = 2
): Promise<CrossLinkOpportunity[]> {
  const params = new URLSearchParams({
    site_url: siteUrl,
    url_pattern: urlPattern,
    days: String(days),
    min_shared_queries: String(minSharedQueries),
  });
  return fetchJSON<CrossLinkOpportunity[]>(`/gsc/cross-gaps?${params}`);
}

/* ── Config ──────────────────────────────────────────────────── */

export async function getConfig(): Promise<AppConfig> {
  return fetchJSON<AppConfig>("/config");
}

export async function updateConfig(
  updates: Partial<AppConfig>
): Promise<void> {
  await fetchJSON("/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
}
