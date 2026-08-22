from __future__ import annotations

import hashlib
import json
import os
import re
import traceback
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(os.getenv("CASE_STUDY_OUT", "case-study-output"))
PDF = Path(os.getenv("CASE_STUDY_PDF", "case-study-output/Example_Article.pdf"))
SITE = os.getenv("SITE_URL", "https://chat-alchemy.vercel.app")
EXPECTED = os.getenv("EXPECTED_SHA256", "252803c27fcd7e11754c1f6330c5247168d1db2ccbf1b1dec94f33b614b5f131")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256(PDF.read_bytes()).hexdigest()
    if sha != EXPECTED:
        raise RuntimeError(f"PDF checksum mismatch: {sha}")

    report = {
        "schema": "ChatAlchemyDocumentBrowserCaseStudy/v2",
        "site_url": SITE,
        "pdf": {"name": PDF.name, "bytes": PDF.stat().st_size, "sha256": sha},
        "success": False,
        "upload": {},
        "trpv1": {},
        "capsaicin_path": {},
        "drawer_chat": {},
        "http_errors": [],
        "console_errors": [],
        "page_errors": [],
        "screenshots": [],
    }

    def save_report():
        (OUT / "case-study-report-v2.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1050}, color_scheme="light", reduced_motion="reduce")
        page = context.new_page()
        page.set_default_timeout(20000)

        def shot(name: str, full_page: bool = False):
            page.screenshot(path=str(OUT / name), full_page=full_page, animations="disabled")
            report["screenshots"].append(name)

        page.on("console", lambda msg: report["console_errors"].append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: report["page_errors"].append(str(err)))
        page.on("response", lambda r: report["http_errors"].append({"status": r.status, "url": r.url}) if r.status >= 500 and r.url.startswith(SITE) else None)

        try:
            page.goto(SITE, wait_until="domcontentloaded", timeout=90000)
            page.get_by_role("button", name="Document lab").click()
            page.get_by_text("Connect uploaded literature to live biomedical evidence.").wait_for(timeout=30000)

            page.locator('input[type="file"]').first.set_input_files(str(PDF.resolve()))
            page.get_by_text("Document analysis ready", exact=True).wait_for(timeout=240000)
            page.wait_for_timeout(2500)

            gene_label = page.get_by_text("Extracted genes", exact=True)
            disease_label = page.get_by_text("Suggested diseases", exact=True)
            genes = [x.strip() for x in gene_label.locator("xpath=..").locator("button").all_inner_texts() if x.strip()]
            diseases = [x.strip() for x in disease_label.locator("xpath=..").locator("button").all_inner_texts() if x.strip()]
            ready_card = page.get_by_text("Document analysis ready", exact=True).locator("xpath=..")
            report["upload"] = {
                "ready": True,
                "extracted_genes": genes,
                "suggested_diseases": diseases,
                "ready_card_text": ready_card.inner_text(),
            }
            shot("01-document-analysis.png")

            trpv1 = page.get_by_role("button", name="TRPV1", exact=True)
            if not trpv1.count():
                raise RuntimeError(f"TRPV1 not available among extracted genes: {genes}")
            trpv1.first.click()
            page.wait_for_timeout(8000)
            page.get_by_text("Gene Details", exact=True).wait_for(timeout=30000)
            report["trpv1"]["ready_card_text"] = ready_card.inner_text()
            shot("02-trpv1-focused.png")

            network_heading = page.get_by_text("Evidence network", exact=True)
            if network_heading.count():
                network_heading.first.scroll_into_view_if_needed()
                page.wait_for_timeout(1200)
                network_section = network_heading.first.locator("xpath=../..").first
                network_section.screenshot(path=str(OUT / "03-trpv1-evidence-network.png"), animations="disabled")
                report["screenshots"].append("03-trpv1-evidence-network.png")
                report["trpv1"]["network_captured"] = True
            else:
                report["trpv1"]["network_captured"] = False

            target_disease = "MONDO_0005578"
            disease_button = page.locator(f'button[title="Open disease information for {target_disease}"]').first
            if not disease_button.count():
                raise RuntimeError(f"Expected TRPV1 disease link {target_disease} was not rendered")
            disease_button.scroll_into_view_if_needed()
            disease_button.click()
            page.get_by_text("Disease Information", exact=True).wait_for(timeout=20000)
            page.wait_for_timeout(2500)
            modal = page.get_by_text("Disease Information", exact=True).locator("xpath=..").first
            disease_text = modal.inner_text()
            report["capsaicin_path"]["disease_id"] = target_disease
            report["capsaicin_path"]["disease_modal_text"] = disease_text[:8000]
            shot("04-arthritic-joint-disease.png")

            capsaicin_button = modal.get_by_role("button", name=re.compile(r"^CAPSAICIN\b"))
            if not capsaicin_button.count():
                raise RuntimeError("CAPSAICIN was not returned as an Open Targets candidate for MONDO_0005578")
            capsaicin_button.first.click()
            page.get_by_text("Canonical SMILES", exact=True).wait_for(timeout=30000)
            page.wait_for_timeout(1800)
            compound_text = modal.inner_text()
            report["capsaicin_path"]["compound_modal_text"] = compound_text[:10000]
            report["capsaicin_path"]["pubchem_visible"] = "PubChem CID" in compound_text and "Canonical SMILES" in compound_text
            shot("05-capsaicin-pubchem.png")

            close = page.get_by_label("Close disease information")
            if close.count():
                close.last.click()
                page.wait_for_timeout(500)

            page.get_by_role("button", name=re.compile("Continue in research chat")).click()
            page.get_by_text("Document research chat", exact=True).wait_for(timeout=20000)
            report["drawer_chat"].update({
                "opened": True,
                "url_after_open": page.url,
                "stayed_on_same_url": page.url.rstrip("/") == SITE.rstrip("/"),
                "document_lab_still_mounted": page.get_by_text("Connect uploaded literature to live biomedical evidence.").count() > 0,
            })
            shot("06-document-chat-drawer.png")

            textarea = page.locator('textarea[placeholder="Ask a biomedical research question..."]').last
            if not textarea.count():
                textarea = page.locator("textarea").last
            question = "What is the chemical structure of capsaicin?"
            textarea.fill(question)
            textarea.press("Enter")
            page.get_by_text(question, exact=True).wait_for(timeout=20000)
            page.wait_for_timeout(12000)
            drawer_text = page.locator("body").inner_text()
            report["drawer_chat"]["question"] = question
            report["drawer_chat"]["capsaicin_answer_visible"] = "Canonical SMILES" in drawer_text or "PubChem" in drawer_text
            report["drawer_chat"]["raw_error_visible"] = "Internal Server Error" in drawer_text
            shot("07-capsaicin-followup.png")

            report["success"] = (
                report["upload"].get("ready")
                and "TRPV1" in genes
                and report["capsaicin_path"].get("pubchem_visible")
                and report["drawer_chat"].get("stayed_on_same_url")
                and not report["http_errors"]
                and not report["page_errors"]
            )
        except Exception as exc:
            report["fatal_error"] = f"{type(exc).__name__}: {exc}"
            report["traceback"] = traceback.format_exc()
            try:
                shot("99-failure-v2.png")
            except Exception:
                pass
        finally:
            save_report()
            browser.close()

    print(json.dumps(report, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
