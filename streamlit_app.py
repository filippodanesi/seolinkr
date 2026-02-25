"""Streamlit web app for SEO Internal Linker."""

from __future__ import annotations

import base64
import json
import tempfile
from dataclasses import asdict
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Helpers: persist/restore results to survive session resets
# ---------------------------------------------------------------------------

RESULTS_DIR = Path.home() / ".seo-linker" / "results"


def _save_results_to_disk(process_result: dict) -> None:
    """Persist process results to disk so they survive session resets."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    serializable = {
        "is_bulk": process_result["is_bulk"],
        "results": [],
    }
    for r in process_result["results"]:
        entry = dict(r)
        if entry.get("file_data"):
            entry["file_data"] = base64.b64encode(entry["file_data"]).decode("ascii")
        serializable["results"].append(entry)
    (RESULTS_DIR / "latest.json").write_text(json.dumps(serializable, indent=2))


def _load_results_from_disk() -> dict | None:
    """Load persisted results from disk, or None if unavailable."""
    path = RESULTS_DIR / "latest.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        for r in data["results"]:
            if r.get("file_data"):
                r["file_data"] = base64.b64decode(r["file_data"])
        return data
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Helpers: config from st.secrets
# ---------------------------------------------------------------------------


def _build_config() -> "Config":
    """Build a Config object from st.secrets + sidebar overrides."""
    from seo_linker.config import Config

    cfg = Config()
    cfg.api_key = st.session_state.get("api_key", "") or st.secrets.get("ANTHROPIC_API_KEY", "")
    cfg.default_model = st.session_state.get("model", cfg.default_model)
    cfg.max_links = st.session_state.get("max_links", cfg.max_links)
    cfg.top_n = st.session_state.get("top_n", cfg.top_n)
    cfg.embedding_model = st.session_state.get("embedding_model", cfg.embedding_model)

    # Sitemaps from secrets
    if "sitemaps" in st.secrets:
        cfg.sitemaps = dict(st.secrets["sitemaps"])

    return cfg


def _get_brand_guidelines() -> str | None:
    """Load brand guidelines from secrets, or None."""
    val = st.secrets.get("brand_guidelines", None)
    return str(val) if val else None


def _get_gsc_client():
    """Create a GSC client from st.secrets service account JSON, or None."""
    if "gsc_service_account_json" not in st.secrets:
        return None

    sa_dict = dict(st.secrets["gsc_service_account_json"])
    # Write to temp file for the GSC auth module
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(sa_dict, tmp)
    tmp.flush()
    tmp.close()

    from seo_linker.gsc.client import GSCClient

    return GSCClient(service_account_path=tmp.name)


@st.cache_data(ttl=300)
def _list_gsc_properties() -> list[str]:
    """Fetch GSC properties available to the service account."""
    client = _get_gsc_client()
    if client is None:
        return []
    try:
        response = client._service.sites().list().execute()
        return sorted(
            entry["siteUrl"] for entry in response.get("siteEntry", [])
        )
    except Exception:
        return []


def _save_upload(uploaded_file) -> Path:
    """Save an uploaded file to a temp path and return the Path."""
    suffix = Path(uploaded_file.name).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.getvalue())
    tmp.close()
    return Path(tmp.name)


@st.cache_resource
def _get_embedding_model(model_name: str):
    """Cache the sentence-transformers model across reruns."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="SEO Internal Linker", page_icon="🔗", layout="wide")
st.title("SEO Internal Linker")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Configuration")

    api_key_default = st.secrets.get("ANTHROPIC_API_KEY", "")
    api_key = st.text_input(
        "Anthropic API Key",
        value=api_key_default,
        type="password",
        key="api_key",
    )

    model = st.selectbox(
        "Claude Model",
        ["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5"],
        index=0,
        key="model",
    )

    max_links = st.slider("Max links to insert", 1, 30, 10, key="max_links")
    top_n = st.slider("Top-N candidates (embedding pre-filter)", 5, 100, 40, key="top_n")

    st.divider()
    st.header("Sitemaps")

    sitemaps: dict[str, str] = {}
    if "sitemaps" in st.secrets:
        sitemaps = dict(st.secrets["sitemaps"])

    if sitemaps:
        for name, url in sitemaps.items():
            st.caption(f"**{name}**: {url}")
    else:
        st.info("No sitemaps configured. Add them in `.streamlit/secrets.toml`.")

    st.divider()
    st.header("Brand Guidelines")
    if _get_brand_guidelines():
        st.success("Brand guidelines loaded from secrets")
    else:
        st.caption("No brand guidelines configured (optional). Add `brand_guidelines` key in secrets.")

    gsc_available = "gsc_service_account_json" in st.secrets
    if gsc_available:
        st.success("GSC service account configured")
        gsc_properties = _list_gsc_properties()
    else:
        st.caption("GSC not configured (optional)")
        gsc_properties = []


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_process, tab_candidates, tab_audit, tab_gsc, tab_gaps = st.tabs(
    ["Process", "Candidates", "Audit", "GSC Opportunities", "Cross-Link Gaps"]
)

# ---- Tab 1: Process ------------------------------------------------------

with tab_process:
    st.subheader("Insert internal links into documents")

    uploaded_files = st.file_uploader(
        "Upload one or more files (.md, .docx, .xlsx)",
        type=["md", "markdown", "docx", "xlsx"],
        key="process_upload",
        accept_multiple_files=True,
    )

    sitemap_names = list(sitemaps.keys())
    with st.form("process_form"):
        selected_sitemaps = st.multiselect(
            "Select sitemaps",
            options=sitemap_names,
            default=sitemap_names[:1] if sitemap_names else [],
        )

        extra_sitemap = st.text_input("Or paste a sitemap URL")

        col1, col2 = st.columns(2)
        with col1:
            gsc_options = ["(none)"] + gsc_properties
            gsc_site_idx = st.selectbox("GSC property (optional)", options=gsc_options, index=0)
            gsc_site = gsc_site_idx if gsc_site_idx != "(none)" else ""
        with col2:
            current_url = st.text_input("Current page URL (optional)", placeholder="https://...")

        st.divider()
        enable_rewrite = st.checkbox("Rewrite/optimize content before linking")
        rw_col1, rw_col2 = st.columns(2)
        with rw_col1:
            content_type = st.radio(
                "Content type",
                ["Existing article", "Rough draft"],
                horizontal=True,
            )
        with rw_col2:
            rewrite_instructions = st.text_area(
                "Custom rewrite instructions (optional)",
                placeholder="e.g. Focus on trail running, keep a casual tone...",
                height=80,
            )

        submitted = st.form_submit_button("Run Pipeline", type="primary")

    if submitted:
        if not uploaded_files:
            st.error("Please upload at least one file.")
        else:
            sitemap_urls = [sitemaps[n] for n in selected_sitemaps]
            if extra_sitemap.strip():
                sitemap_urls.append(extra_sitemap.strip())

            if not sitemap_urls:
                st.error("Select at least one sitemap.")
            else:
                cfg = _build_config()
                from seo_linker.pipeline import PipelineError, run_pipeline

                ct_value = "rough_draft" if content_type == "Rough draft" else "existing_article"
                is_bulk = len(uploaded_files) > 1

                if is_bulk:
                    # -------------------------------------------------------
                    # Bulk mode: shared prep + sequential per-file processing
                    # -------------------------------------------------------
                    from seo_linker.models import TargetPage
                    from seo_linker.sitemap.enricher import enrich_pages
                    from seo_linker.sitemap.fetcher import fetch_sitemap

                    prep_status = st.status("Preparing shared resources...", expanded=True)
                    prep_log_area = prep_status.empty()
                    prep_lines: list[str] = []

                    def _prep_log(msg: str) -> None:
                        prep_lines.append(msg)
                        prep_log_area.text("\n".join(prep_lines))

                    try:
                        pages: list[TargetPage] = []
                        for sitemap_url in sitemap_urls:
                            _prep_log(f"Fetching sitemap from {sitemap_url}...")
                            sitemap_pages = fetch_sitemap(sitemap_url)
                            _prep_log(f"  Found {len(sitemap_pages)} URLs")
                            pages.extend(sitemap_pages)

                        # Deduplicate
                        seen: set[str] = set()
                        unique: list[TargetPage] = []
                        for p in pages:
                            if p.url not in seen:
                                seen.add(p.url)
                                unique.append(p)
                        pages = unique

                        # Filter product pages
                        before = len(pages)
                        pages = [p for p in pages if not p.url.rstrip("/").endswith(".html")]
                        if before != len(pages):
                            _prep_log(f"  Filtered {before - len(pages)} product pages, {len(pages)} remaining")

                        # Enrich once for all files
                        _prep_log("Enriching pages with metadata...")
                        pages = enrich_pages(pages, cfg.cache_ttl_hours)
                        enriched_count = sum(1 for p in pages if p.title)
                        _prep_log(f"  Enriched {enriched_count}/{len(pages)} pages")

                        prep_status.update(label="Shared resources ready", state="complete")
                    except Exception as e:
                        prep_status.update(label="Preparation failed", state="error")
                        st.error(f"Failed to prepare shared resources: {e}")
                        st.stop()

                    # Create GSC client once for all files
                    gsc_client = _get_gsc_client() if gsc_site else None

                    progress = st.progress(0, text="Starting bulk processing...")
                    all_results: list[dict] = []

                    for i, uf in enumerate(uploaded_files):
                        progress.progress(
                            i / len(uploaded_files),
                            text=f"Processing {uf.name} ({i + 1}/{len(uploaded_files)})...",
                        )

                        file_status = st.status(f"Processing {uf.name}...", expanded=False)
                        file_log_area = file_status.empty()
                        file_lines: list[str] = []

                        def _file_log(msg: str, _lines=file_lines, _area=file_log_area) -> None:
                            _lines.append(msg)
                            _area.text("\n".join(_lines))

                        try:
                            input_path = _save_upload(uf)
                            suffix = input_path.suffix
                            output_path = input_path.with_name(f"output_linked_{i}{suffix}")

                            result = run_pipeline(
                                input_path=input_path,
                                sitemap_urls=sitemap_urls,
                                output_path=output_path,
                                max_links=cfg.max_links,
                                top_n=cfg.top_n,
                                model=cfg.default_model,
                                current_url=None,
                                config=cfg,
                                gsc_site=gsc_site or None,
                                log_fn=_file_log,
                                brand_guidelines=_get_brand_guidelines(),
                                gsc_client=gsc_client,
                                enable_rewrite=enable_rewrite,
                                content_type=ct_value,
                                rewrite_instructions=rewrite_instructions.strip() or None,
                                prefetched_pages=pages,
                            )

                            with open(output_path, "rb") as f:
                                file_data = f.read()

                            all_results.append({
                                "file_name": f"{Path(uf.name).stem}_linked{suffix}",
                                "file_data": file_data,
                                "insertions": [
                                    {"anchor_text": ins.anchor_text, "target_url": ins.target_url, "reasoning": ins.reasoning}
                                    for ins in result.insertions
                                ],
                                "rewritten_text": result.rewritten_text,
                                "error": None,
                            })

                            file_status.update(
                                label=f"{uf.name} — {len(result.insertions)} links inserted",
                                state="complete",
                            )
                        except Exception as e:
                            all_results.append({
                                "file_name": uf.name,
                                "file_data": None,
                                "insertions": [],
                                "rewritten_text": "",
                                "error": str(e),
                            })
                            file_status.update(label=f"{uf.name} — FAILED", state="error")

                        # Rate-limit safety: pause between Anthropic API calls
                        if i < len(uploaded_files) - 1:
                            import time
                            time.sleep(1)

                    progress.progress(1.0, text="All files processed!")

                    st.session_state["process_result"] = {
                        "is_bulk": True,
                        "results": all_results,
                    }
                    _save_results_to_disk(st.session_state["process_result"])

                else:
                    # -------------------------------------------------------
                    # Single file (original flow, unchanged)
                    # -------------------------------------------------------
                    uploaded = uploaded_files[0]
                    input_path = _save_upload(uploaded)
                    suffix = input_path.suffix
                    output_path = input_path.with_name(f"output_linked{suffix}")

                    status = st.status("Running pipeline...", expanded=True)
                    log_area = status.empty()
                    log_lines: list[str] = []

                    def _log(msg: str) -> None:
                        log_lines.append(msg)
                        log_area.text("\n".join(log_lines))

                    try:
                        result = run_pipeline(
                            input_path=input_path,
                            sitemap_urls=sitemap_urls,
                            output_path=output_path,
                            max_links=cfg.max_links,
                            top_n=cfg.top_n,
                            model=cfg.default_model,
                            current_url=current_url or None,
                            config=cfg,
                            gsc_site=gsc_site or None,
                            log_fn=_log,
                            brand_guidelines=_get_brand_guidelines(),
                            gsc_client=_get_gsc_client() if gsc_site else None,
                            enable_rewrite=enable_rewrite,
                            content_type=ct_value,
                            rewrite_instructions=rewrite_instructions.strip() or None,
                        )
                        status.update(label="Pipeline completed!", state="complete")

                        with open(output_path, "rb") as f:
                            st.session_state["process_result"] = {
                                "is_bulk": False,
                                "results": [{
                                    "file_name": f"{Path(uploaded.name).stem}_linked{suffix}",
                                    "file_data": f.read(),
                                    "insertions": [
                                        {"anchor_text": ins.anchor_text, "target_url": ins.target_url, "reasoning": ins.reasoning}
                                        for ins in result.insertions
                                    ],
                                    "rewritten_text": result.rewritten_text,
                                    "error": None,
                                }],
                            }
                            _save_results_to_disk(st.session_state["process_result"])
                    except PipelineError as e:
                        status.update(label="Pipeline failed", state="error")
                        st.error(str(e))

    # Restore results from disk if the session was reset (e.g. tab switch)
    if "process_result" not in st.session_state:
        _restored = _load_results_from_disk()
        if _restored:
            st.session_state["process_result"] = _restored
            st.info("Results restored from a previous session.")

    # Display results from session_state (persists across reruns)
    if "process_result" in st.session_state:
        pr = st.session_state["process_result"]

        if pr.get("is_bulk"):
            results = pr["results"]
            ok = [r for r in results if not r["error"]]
            failed = [r for r in results if r["error"]]
            total_links = sum(len(r["insertions"]) for r in ok)

            st.success(f"Processed **{len(ok)}/{len(results)}** files — **{total_links}** links inserted total")

            if failed:
                for r in failed:
                    st.error(f"**{r['file_name']}**: {r['error']}")

            for r in ok:
                with st.expander(f"{r['file_name']} — {len(r['insertions'])} links"):
                    if r["rewritten_text"]:
                        st.markdown("**Rewritten content (before linking):**")
                        st.markdown(r["rewritten_text"][:500] + "...")
                    if r["insertions"]:
                        for ins in r["insertions"]:
                            st.markdown(f"- [{ins['anchor_text']}]({ins['target_url']}) — {ins['reasoning']}")
                    st.download_button(
                        f"Download {r['file_name']}",
                        data=r["file_data"],
                        file_name=r["file_name"],
                        mime="application/octet-stream",
                        key=f"dl_{r['file_name']}",
                    )

            # ZIP download for all successful files
            if len(ok) > 1:
                import io
                import zipfile

                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for r in ok:
                        zf.writestr(r["file_name"], r["file_data"])
                zip_buf.seek(0)

                st.download_button(
                    "Download all as ZIP",
                    data=zip_buf.getvalue(),
                    file_name="linked_files.zip",
                    mime="application/zip",
                    key="dl_bulk_zip",
                )

        else:
            r = pr["results"][0]
            st.success(f"Inserted **{len(r['insertions'])}** links")

            if r["rewritten_text"]:
                with st.expander("View rewritten content (before linking)"):
                    st.markdown(r["rewritten_text"])

            if r["insertions"]:
                st.markdown("**Link report:**")
                for ins in r["insertions"]:
                    st.markdown(f"- [{ins['anchor_text']}]({ins['target_url']}) — {ins['reasoning']}")

            st.download_button(
                label=f"Download {r['file_name']}",
                data=r["file_data"],
                file_name=r["file_name"],
                mime="application/octet-stream",
            )

# ---- Tab 2: Candidates ---------------------------------------------------

with tab_candidates:
    st.subheader("Find candidate pages for linking (no links inserted)")

    uploaded_c = st.file_uploader(
        "Upload a file (.md, .docx, .xlsx)",
        type=["md", "markdown", "docx", "xlsx"],
        key="candidates_upload",
    )

    with st.form("candidates_form"):
        selected_sitemaps_c = st.multiselect(
            "Select sitemaps",
            options=sitemap_names,
            default=sitemap_names[:1] if sitemap_names else [],
        )
        submitted_c = st.form_submit_button("Find Candidates", type="primary")

    if submitted_c:
        if not uploaded_c:
            st.error("Please upload a file.")
        elif not selected_sitemaps_c:
            st.error("Select at least one sitemap.")
        else:
            input_path = _save_upload(uploaded_c)
            cfg = _build_config()

            with st.spinner("Fetching sitemaps, enriching pages, computing embeddings..."):
                from seo_linker.matching.prefilter import prefilter_pages
                from seo_linker.parsers.detector import detect_parser
                from seo_linker.sitemap.enricher import enrich_pages
                from seo_linker.sitemap.fetcher import fetch_sitemap

                parser = detect_parser(input_path)
                sections = parser.parse(input_path)

                pages = []
                for name in selected_sitemaps_c:
                    pages.extend(fetch_sitemap(sitemaps[name]))

                # Deduplicate
                seen: set[str] = set()
                pages = [p for p in pages if p.url not in seen and not seen.add(p.url)]
                pages = [p for p in pages if not p.url.rstrip("/").endswith(".html")]

                pages = enrich_pages(pages, cfg.cache_ttl_hours)
                candidates = prefilter_pages(sections, pages, cfg.top_n, cfg.embedding_model)

            import pandas as pd

            df = pd.DataFrame(
                [
                    {"URL": p.url, "Title": p.title, "Meta Description": p.meta_description}
                    for p in candidates
                ]
            )
            st.dataframe(df, width="stretch")

            st.download_button(
                "Download candidates JSON",
                data=json.dumps(
                    [{"url": p.url, "title": p.title, "meta_description": p.meta_description} for p in candidates],
                    indent=2,
                ),
                file_name="candidates.json",
                mime="application/json",
            )

# ---- Tab 3: Audit --------------------------------------------------------

with tab_audit:
    st.subheader("Audit internal links in a document")

    uploaded_a = st.file_uploader(
        "Upload a markdown file (.md)",
        type=["md", "markdown"],
        key="audit_upload",
    )

    with st.form("audit_form"):
        audit_domain = st.text_input("Expected domain (optional)", placeholder="www.example.com")
        submitted_a = st.form_submit_button("Run Audit", type="primary")

    if submitted_a:
        if not uploaded_a:
            st.error("Please upload a markdown file.")
        else:
            input_path = _save_upload(uploaded_a)

            with st.spinner("Auditing..."):
                from seo_linker.audit.checker import audit_file

                result = audit_file(input_path, audit_domain or None)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total links", result.total_links)
            col2.metric("Category", result.category_links)
            col3.metric("Magazine", result.magazine_links)
            col4.metric("Product", result.product_links)

            if result.issues:
                st.warning(f"Found {len(result.issues)} issue(s)")
                for issue in result.issues:
                    icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(issue.severity, "⚪")
                    st.markdown(f"{icon} **{issue.severity.upper()}**: {issue.message}")
            else:
                st.success("No issues found!")

            if result.links:
                import pandas as pd

                df = pd.DataFrame(
                    [{"Anchor": lnk.anchor, "URL": lnk.url, "Type": lnk.link_type} for lnk in result.links]
                )
                st.dataframe(df, width="stretch")

# ---- Tab 4: GSC Opportunities --------------------------------------------

with tab_gsc:
    st.subheader("Pages that would benefit most from internal links")

    if not gsc_available:
        st.info("Configure `gsc_service_account_json` in secrets to enable this feature.")
    else:
        gsc_site_opp = st.selectbox("GSC property", options=gsc_properties, key="opp_gsc_site")
        col1, col2 = st.columns(2)
        with col1:
            opp_days = st.number_input("Lookback days", value=28, min_value=1, max_value=90, key="opp_days")
        with col2:
            opp_min_imp = st.number_input("Min impressions", value=100, min_value=0, key="opp_min_imp")

        if st.button("Compute Opportunities", type="primary", key="opp_run"):
            with st.spinner("Fetching GSC data and computing scores..."):
                from seo_linker.gsc.opportunities import compute_opportunities

                gsc_client = _get_gsc_client()
                opps = compute_opportunities(gsc_client, gsc_site_opp, opp_days, opp_min_imp)

            if not opps:
                st.info("No opportunities found.")
            else:
                import pandas as pd

                df = pd.DataFrame(
                    [
                        {
                            "Priority": o.priority,
                            "URL": o.url,
                            "Impressions": o.impressions,
                            "Clicks": o.clicks,
                            "Avg Position": round(o.position, 1),
                            "CTR": f"{o.ctr:.1%}",
                            "Score": o.opportunity_score,
                            "Reason": o.reason,
                        }
                        for o in opps
                    ]
                )
                st.dataframe(df, width="stretch", height=600)

# ---- Tab 5: Cross-Link Gaps ----------------------------------------------

with tab_gaps:
    st.subheader("Cross-linking opportunities between blog articles")

    if not gsc_available:
        st.info("Configure `gsc_service_account_json` in secrets to enable this feature.")
    else:
        gsc_site_gap = st.selectbox("GSC property", options=gsc_properties, key="gap_gsc_site")
        col1, col2, col3 = st.columns(3)
        with col1:
            gap_pattern = st.text_input("URL pattern (regex)", value="/magazine/|/magazin/", key="gap_pattern")
        with col2:
            gap_days = st.number_input("Lookback days", value=28, min_value=1, max_value=90, key="gap_days")
        with col3:
            gap_min_shared = st.number_input("Min shared queries", value=2, min_value=1, key="gap_min_shared")

        if st.button("Find Cross-Link Gaps", type="primary", key="gap_run"):
            with st.spinner("Analysing query overlaps..."):
                from seo_linker.gsc.cross_linker import find_cross_link_gaps

                gsc_client = _get_gsc_client()
                gaps = find_cross_link_gaps(
                    gsc_client, gsc_site_gap, gap_pattern, gap_days, gap_min_shared
                )

            if not gaps:
                st.info("No cross-linking gaps found.")
            else:
                import pandas as pd

                df = pd.DataFrame(
                    [
                        {
                            "Suggestion": g.suggestion,
                            "Source URL": g.source_url,
                            "Target URL": g.target_url,
                            "Shared Queries": ", ".join(g.shared_queries[:5]),
                            "Shared Count": g.shared_query_count,
                            "Target Impressions": g.target_impressions,
                            "Relevance Score": round(g.relevance_score, 1),
                        }
                        for g in gaps
                    ]
                )
                st.dataframe(df, width="stretch", height=600)
