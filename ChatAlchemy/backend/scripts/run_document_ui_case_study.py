from __future__ import annotations

import hashlib
import json
import os
import re
import traceback
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

OUT = Path(os.getenv("CASE_STUDY_OUT", "case-study-output"))
PDF = Path(os.getenv("CASE_STUDY_PDF", "case-study-output/Example_Article.pdf"))
SITE = os.getenv("SITE_URL", "https://chat-alchemy.vercel.app")
EXPECTED = os.getenv("EXPECTED_SHA256", "252803c27fcd7e11754c1f6330c5247168d1db2ccbf1b1dec94f33b614b5f131")


def clean_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", name).strip("-").lower()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256(PDF.read_bytes()).hexdigest()
    if sha != EXPECTED:
        raise RuntimeError(f"PDF checksum mismatch: {sha}")

    report: dict = {
        "site_url": SITE,
        "pdf": {"name": PDF.name, "bytes": PDF.stat().st_size, "sha256": sha},
        "success": False,
        "upload": {},
        "trpv1_focus": {},
        "disease_modals": [],
        "compound_drilldown": {},
        "drawer_chat": {},
        "http_errors": [],
        "console_errors": [],
        "page_errors": [],
        "screenshots": [],
    }

    def write_report() -> None:
        (OUT / "case-study-report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1050},
            color_scheme="light",
            reduced_motion="reduce",
            accept_downloads=True,
        )
        page = context.new_page()
        page.set_default_timeout(15000)

        def screenshot(name: str, full_page: bool = True) -> None:
            page.screenshot(path=str(OUT / name), full_page=full_page, animations="disabled")
            report["screenshots"].append(name)

        def body_text() -> str:
            try:
                return page.locator("body").inner_text(timeout=5000)
            except Exception:
                return ""

        def save_body(name: str) -> None:
            (OUT / name).write_text(body_text(), encoding="utf-8")

        def on_console(msg) -> None:
            if msg.type == "error":
                report["console_errors"].append(msg.text)

        def on_page_error(error) -> None:
            report["page_errors"].append(str(error))

        def on_response(response) -> None:
            if response.status >= 400:
                url = response.url
                if url.startswith(SITE) or "/api/" in url or "opentargets" in url or "pubchem" in url:
                    report["http_errors"].append({"status": response.status, "url": url})

        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        page.on("response", on_response)

        try:
            page.goto(SITE, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(2500)
            screenshot("01-workspace.png")

            page.get_by_role("button", name="Document lab").click()
            page.get_by_text("Connect uploaded literature to live biomedical evidence.").wait_for(timeout=30000)
            screenshot("02-document-lab-empty.png")

            page.locator('input[type=file][accept*=".pdf"]').first.set_input_files(str(PDF.resolve()))
            outcome = "unknown"
            try:
                page.get_by_text("Document analysis ready").wait_for(timeout=240000)
                outcome = "ready"
            except PlaywrightTimeoutError:
                text = body_text()
                outcome = "error" if any(
                    marker in text
                    for marker in ("Could not process document", "Biomedical analysis failed", "Internal Server Error")
                ) else "timeout"

            page.wait_for_timeout(2500)
            upload_text = body_text()
            report["upload"].update(
                {
                    "outcome": outcome,
                    "document_ready": "Document analysis ready" in upload_text,
                    "raw_error_visible": any(
                        marker in upload_text
                        for marker in ("Internal Server Error", "Could not process document", "Biomedical analysis failed")
                    ),
                }
            )
            save_body("03-document-analysis.txt")
            screenshot("03-document-analysis-full.png")
            if outcome != "ready":
                report["upload"]["visible_text_tail"] = upload_text[-4000:]
                raise RuntimeError(f"Document upload did not become ready: {outcome}")

            gene_label = page.get_by_text("Extracted genes", exact=True)
            disease_label = page.get_by_text("Suggested diseases", exact=True)
            report["upload"]["extracted_genes"] = (
                [x.strip() for x in gene_label.locator("xpath=..").locator("button").all_inner_texts() if x.strip()]
                if gene_label.count()
                else []
            )
            report["upload"]["suggested_diseases"] = (
                [x.strip() for x in disease_label.locator("xpath=..").locator("button").all_inner_texts() if x.strip()]
                if disease_label.count()
                else []
            )
            ready_card = page.get_by_text("Document analysis ready", exact=True).locator("xpath=..")
            report["upload"]["ready_card_text"] = ready_card.inner_text() if ready_card.count() else ""

            trpv1 = page.get_by_role("button", name="TRPV1", exact=True)
            report["trpv1_focus"]["clicked"] = bool(trpv1.count())
            if trpv1.count():
                trpv1.first.click()
                try:
                    page.get_by_text("Working through the evidence path").wait_for(state="hidden", timeout=180000)
                except Exception:
                    pass
                page.wait_for_timeout(3000)
                trpv1_text = body_text()
                report["trpv1_focus"]["raw_error_visible"] = any(
                    marker in trpv1_text for marker in ("Internal Server Error", "Biomedical analysis failed")
                )
                save_body("04-trpv1-focused.txt")
                screenshot("04-trpv1-focused.png")

            show_all = page.get_by_role("button", name=re.compile(r"^Show All \("))
            if show_all.count():
                show_all.first.click()
                page.wait_for_timeout(500)

            disease_links = page.locator('button[title^="Open disease information for "]')
            disease_titles = disease_links.evaluate_all(
                "els => [...new Set(els.map(e => e.getAttribute('title')).filter(Boolean))]"
            )
            report["trpv1_focus"]["disease_link_count"] = len(disease_titles)
            report["trpv1_focus"]["disease_link_titles"] = disease_titles[:25]

            first_good = None
            for idx, title in enumerate(disease_titles[:8], start=1):
                entry = {"title": title, "opened": False, "status": "unknown", "text": ""}
                try:
                    button = page.locator(f'button[title="{title}"]').first
                    button.scroll_into_view_if_needed()
                    button.click()
                    page.get_by_text("Disease Information", exact=True).wait_for(timeout=15000)
                    page.wait_for_timeout(3500)
                    modal = page.get_by_text("Disease Information", exact=True).locator("xpath=..")
                    modal_text = modal.inner_text()
                    entry["opened"] = True
                    entry["text"] = modal_text[:5000]
                    entry["status"] = "error" if any(
                        marker in modal_text for marker in ("Could not load", "request failed", "Internal Server Error")
                    ) else "ok"
                    if entry["status"] == "ok" and first_good is None:
                        first_good = title
                    if idx <= 3 or entry["status"] == "error":
                        screenshot(
                            f'05-disease-{idx}-{clean_filename(title.replace("Open disease information for ", ""))}.png',
                            full_page=False,
                        )
                except Exception as exc:
                    entry["status"] = "exception"
                    entry["text"] = f"{type(exc).__name__}: {exc}"
                finally:
                    close = page.get_by_label("Close disease information")
                    if close.count():
                        try:
                            close.last.click()
                            page.wait_for_timeout(300)
                        except Exception:
                            page.keyboard.press("Escape")
                report["disease_modals"].append(entry)

            if first_good:
                page.locator(f'button[title="{first_good}"]').first.click()
                page.get_by_text("Disease Information", exact=True).wait_for(timeout=15000)
                page.wait_for_timeout(2500)
                modal = page.get_by_text("Disease Information", exact=True).locator("xpath=..")
                candidate = None
                for button in modal.locator("button").all():
                    try:
                        text = button.inner_text().strip()
                    except Exception:
                        continue
                    if text and "Close disease information" not in text:
                        candidate = button
                        report["compound_drilldown"]["candidate_button_text"] = text
                        break
                if candidate is not None:
                    candidate.click()
                    page.wait_for_timeout(5500)
                    modal_text = modal.inner_text()
                    report["compound_drilldown"]["status"] = "error" if any(
                        marker in modal_text for marker in ("Could not load", "request failed")
                    ) else "ok"
                    report["compound_drilldown"]["modal_text"] = modal_text[:7000]
                    screenshot("06-disease-compound-drilldown.png", full_page=False)
                else:
                    report["compound_drilldown"]["status"] = "no-drug-candidate"
                close = page.get_by_label("Close disease information")
                if close.count():
                    close.last.click()
                    page.wait_for_timeout(500)
            else:
                report["compound_drilldown"]["status"] = "no-successful-disease-modal"

            page.get_by_role("button", name=re.compile("Continue in research chat")).click()
            page.get_by_text("Document research chat", exact=True).wait_for(timeout=15000)
            drawer = page.get_by_text("Document research chat", exact=True).locator("xpath=../..")
            report["drawer_chat"].update(
                {
                    "opened": True,
                    "url_after_open": page.url,
                    "stayed_on_same_url": page.url.rstrip("/") == SITE.rstrip("/"),
                    "document_lab_still_mounted": page.get_by_text(
                        "Connect uploaded literature to live biomedical evidence."
                    ).count()
                    > 0,
                    "initial_text": drawer.inner_text()[:8000],
                }
            )
            screenshot("07-document-research-chat-drawer.png", full_page=False)

            question = "What is the chemical structure of capsaicin?"
            textarea = drawer.locator('textarea[placeholder="Ask a biomedical research question…"]')
            textarea.fill(question)
            textarea.press("Enter")
            page.get_by_text(question, exact=True).wait_for(timeout=15000)
            try:
                drawer.get_by_text("Working through the evidence path…", exact=True).wait_for(
                    state="hidden", timeout=180000
                )
            except Exception:
                pass
            page.wait_for_timeout(3500)
            final_drawer_text = drawer.inner_text()
            report["drawer_chat"].update(
                {
                    "capsaicin_question": question,
                    "final_text": final_drawer_text[:12000],
                    "raw_error_visible": any(
                        marker in final_drawer_text
                        for marker in ("Internal Server Error", "I could not complete that follow-up workflow")
                    ),
                }
            )
            screenshot("08-capsaicin-followup.png", full_page=False)
            report["success"] = True

        except Exception as exc:
            report["fatal_error"] = f"{type(exc).__name__}: {exc}"
            report["traceback"] = traceback.format_exc()
            try:
                screenshot("99-failure-state.png")
                save_body("99-failure-state.txt")
            except Exception:
                pass
        finally:
            write_report()
            browser.close()

    print((OUT / "case-study-report.json").read_text(encoding="utf-8"))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
