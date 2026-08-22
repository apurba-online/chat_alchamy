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

    report: dict = {
        "site_url": SITE,
        "pdf_sha256": sha,
        "success": False,
        "captures": [],
        "capsaicin": {},
        "http_errors": [],
        "console_errors": [],
        "page_errors": [],
    }

    def save_locator(locator, name: str) -> None:
        locator.scroll_into_view_if_needed()
        locator.screenshot(path=str(OUT / name), animations="disabled")
        report["captures"].append(name)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1050},
            color_scheme="light",
            reduced_motion="reduce",
        )
        page = context.new_page()
        page.set_default_timeout(20000)

        page.on(
            "console",
            lambda msg: report["console_errors"].append(msg.text) if msg.type == "error" else None,
        )
        page.on("pageerror", lambda err: report["page_errors"].append(str(err)))

        def on_response(response) -> None:
            if response.status >= 400 and (
                response.url.startswith(SITE)
                or "/api/" in response.url
                or "opentargets" in response.url
                or "pubchem" in response.url
            ):
                report["http_errors"].append({"status": response.status, "url": response.url})

        page.on("response", on_response)

        try:
            page.goto(SITE, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(2000)
            page.get_by_role("button", name="Document lab").click()
            page.get_by_text("Connect uploaded literature to live biomedical evidence.").wait_for(timeout=30000)
            page.locator('input[type=file][accept*=".pdf"]').first.set_input_files(str(PDF.resolve()))
            page.get_by_text("Document analysis ready").wait_for(timeout=240000)
            page.wait_for_timeout(2500)

            trpv1 = page.get_by_role("button", name="TRPV1", exact=True)
            if not trpv1.count():
                raise RuntimeError("TRPV1 was not surfaced by document extraction")
            trpv1.first.click()
            page.wait_for_timeout(6000)

            # Manuscript panel: focused gene table and associated diseases.
            gene_table = page.get_by_text("Gene Details", exact=True).locator("xpath=ancestor::div[contains(@class,'overflow-x-auto')]")
            if gene_table.count():
                save_locator(gene_table.first, "09-manuscript-trpv1-gene-table.png")

            literature = page.get_by_text(re.compile(r"^LITERATURE CONTEXT$", re.I)).locator("xpath=ancestor::section")
            if literature.count():
                save_locator(literature.first, "10-manuscript-literature-context.png")

            evidence_synthesis = page.get_by_text(re.compile(r"^EVIDENCE SYNTHESIS$", re.I)).locator("xpath=ancestor::section")
            if evidence_synthesis.count():
                save_locator(evidence_synthesis.first, "11-manuscript-evidence-synthesis.png")

            shared = page.get_by_text("Shared disease evidence", exact=True).locator("xpath=ancestor::section")
            if shared.count():
                save_locator(shared.first, "12-manuscript-shared-disease-evidence.png")

            network = page.get_by_text("Evidence network", exact=True).locator("xpath=ancestor::section")
            if network.count():
                page.wait_for_timeout(2500)
                save_locator(network.first, "13-manuscript-evidence-network.png")

            # Deliberately choose the TRPV1-linked arthritic joint disease entry because
            # its current Open Targets candidate list contains CAPSAICIN.
            target_disease = page.locator('button[title="Open disease information for MONDO_0005578"]').first
            target_disease.scroll_into_view_if_needed()
            target_disease.click()
            page.get_by_text("Disease Information", exact=True).wait_for(timeout=20000)
            page.wait_for_timeout(3500)

            modal = page.get_by_text("Disease Information", exact=True).locator("xpath=ancestor::div[contains(@class,'max-w-5xl')]")
            modal_text = modal.inner_text()
            report["capsaicin"]["disease_modal"] = "arthritic joint disease" in modal_text.lower()
            report["capsaicin"]["capsaicin_candidate_visible"] = "CAPSAICIN" in modal_text
            save_locator(modal, "14-manuscript-arthritic-disease-candidates.png")

            capsaicin_button = modal.get_by_role("button", name=re.compile(r"^CAPSAICIN\b"))
            if not capsaicin_button.count():
                raise RuntimeError("CAPSAICIN candidate was not available in the selected Open Targets disease view")
            capsaicin_button.first.click()
            page.wait_for_timeout(6500)
            modal_text = modal.inner_text()
            report["capsaicin"].update(
                {
                    "compound_loaded": "PubChem CID" in modal_text and "Canonical SMILES" in modal_text,
                    "modal_text": modal_text[:8000],
                }
            )
            save_locator(modal, "15-manuscript-capsaicin-structure.png")

            # Reconfirm the in-page drawer while the focused document remains mounted.
            page.get_by_label("Close disease information").click()
            page.wait_for_timeout(500)
            page.get_by_role("button", name=re.compile("Continue in research chat")).click()
            page.get_by_text("Document research chat", exact=True).wait_for(timeout=20000)
            drawer = page.get_by_text("Document research chat", exact=True).locator("xpath=ancestor::aside")
            report["drawer_stays_in_document_lab"] = (
                page.url.rstrip("/") == SITE.rstrip("/")
                and page.get_by_text("Connect uploaded literature to live biomedical evidence.").count() > 0
            )
            save_locator(drawer, "16-manuscript-document-chat-drawer.png")

            report["success"] = True
        except Exception as exc:
            report["fatal_error"] = f"{type(exc).__name__}: {exc}"
            report["traceback"] = traceback.format_exc()
            try:
                page.screenshot(path=str(OUT / "98-manuscript-capture-failure.png"), full_page=True)
            except Exception:
                pass
        finally:
            (OUT / "manuscript-capture-report.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            browser.close()

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
