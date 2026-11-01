#!/usr/bin/env python3
"""Bounded new-template browser checks. Existing Playwright/Chromium only.

Serves only three authored HTML strings on an ephemeral loopback port. Does not
read source packets, install browsers, contact providers, or change user data.
"""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

def run(args):
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    template = ROOT / 'skills/idea-talks/assets/template.html'
    fixture = ROOT / 'evals/dev/repair-club-talk.html'
    pages = {'/template': template.read_text(), '/fixture': fixture.read_text()}
    report = {'schema': 'idea-talks-original-template-browser/v1', 'at': datetime.now(timezone.utc).isoformat(),
              'checks': [], 'external_requests': [], 'page_errors': [],
              'template_sha256': hashlib.sha256(template.read_bytes()).hexdigest(),
              'fixture_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(),
              'scope': 'Actual Chromium software interactions only; no model, audience, human-learning or quality measurement.'}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in pages:
                self.send_response(404); self.end_headers(); return
            body = pages[self.path].encode()
            self.send_response(200); self.send_header('Content-Type', 'text/html;charset=utf-8')
            self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
        def log_message(self, *_):
            pass

    def check(name, value, **details):
        report['checks'].append({'name': name, 'passed': bool(value), **details})
        (out / 'RESULT.partial.json').write_text(json.dumps(report, indent=2) + '\n')
        if not value:
            raise AssertionError(name)

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=args.chromium,
                                        args=['--disable-background-networking'])
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
            def route(request):
                if request.request.url.startswith(base + '/'):
                    request.continue_()
                else:
                    report['external_requests'].append(request.request.url); request.abort()
            context.route('**/*', route)
            page = context.new_page(); page.on('pageerror', lambda e: report['page_errors'].append(str(e)))
            page.goto(base + '/template', wait_until='networkidle')
            check('nine source slides and one active', page.locator('section.slide').count() == 9 and page.locator('.slide.active').count() == 1)
            check('accessible controls have explicit labels', all(page.locator('#' + key).inner_text().strip() for key in ['download', 'edit-button', 'notes-button', 'overview-button', 'previous', 'next']))
            page.keyboard.press('ArrowRight'); check('keyboard next', page.locator('#human-moment').evaluate("e=>e.classList.contains('active')"))
            page.keyboard.press('Home'); page.locator('#overview-button').click()
            check('overview dialog contains all nine choices', page.locator('#overview').evaluate('e=>e.open') and page.locator('#overview-grid button').count() == 9)
            page.keyboard.press('Escape'); check('overview escape returns focus', page.locator('#overview-button').evaluate('e=>e===document.activeElement'))
            page.locator('#edit-button').click(); title = page.locator('[data-edit="title"]')
            title.fill('A local edited idea'); title.press('ArrowRight')
            check('typing does not navigate', page.locator('#opening').evaluate("e=>e.classList.contains('active')"))
            page.locator('#notes-button').click(); page.locator('#note-editor').fill('Private draft note: review before sharing.'); page.locator('#note-editor').press('End')
            check('notes typing does not navigate', page.locator('#opening').evaluate("e=>e.classList.contains('active')"))
            page.locator('#source-reference').fill('Fictional S1, lines 2–4'); page.locator('#source-status').select_option('reported')
            for bad in ['javascript:alert(1)', 'data:text/html,<script>alert(1)</script>', 'file:///private/example', '//example.com', 'https://user:password@example.com/', 'https://exa\tmple.com']:
                page.locator('#source-url').fill(bad)
                check('unsafe source URL rejected: ' + bad.split(':')[0], page.locator('#source-url').get_attribute('aria-invalid') == 'true' and page.locator('#source-link').get_attribute('href') is None and page.evaluate('IdeaTalks.exportHTML()') is None)
            page.locator('#source-url').fill('https://example.org/evidence?q=one&part=two')
            check('safe source URL retained without automatic request', page.locator('#source-link').get_attribute('href') == 'https://example.org/evidence?q=one&part=two')
            for value in ['NaN', 'Infinity', '-1', '9', '1.5', '"1"']:
                check('invalid navigation index refused: ' + value, page.evaluate('value => IdeaTalks.goTo(value)', float('nan') if value == 'NaN' else float('inf') if value == 'Infinity' else -1 if value == '-1' else 9 if value == '9' else 1.5 if value == '1.5' else '1') is False)
            page.evaluate("document.querySelector('[data-edit=opening-source-url]').textContent='\\nhttps://example.org/'")
            check('stored source URL with leading control refused', page.evaluate('IdeaTalks.exportHTML()') is None)
            page.locator('#source-url').fill('https://example.org/evidence?q=one&part=two')
            page.locator('[data-edit=audience]').fill(''); check('empty audience blocks export', page.evaluate('IdeaTalks.exportHTML()') is None and 'audience' in page.locator('#status').inner_text())
            page.locator('[data-edit=audience]').fill('Fictional reviewers')
            title.fill(''); check('empty heading blocks export', page.evaluate('IdeaTalks.exportHTML()') is None and 'heading' in page.locator('#status').inner_text())
            previous_saved = page.evaluate("localStorage.getItem('idea-talks.draft.v1:'+document.body.dataset.deckId)")
            title.fill('x' * 300)
            check('oversized author text preserved and invalid draft not saved', len(title.inner_text()) == 300 and 'Draft not saved' in page.locator('#status').inner_text() and page.evaluate("localStorage.getItem('idea-talks.draft.v1:'+document.body.dataset.deckId)") == previous_saved)
            check('oversized export is blocked', page.evaluate('IdeaTalks.exportHTML()') is None)
            hostile = '</h1><script>window.injected=1</script><img src=https://invalid.example/x onerror=alert(1)>'
            title.fill(hostile); check('HTML-like input stays text', title.inner_text() == hostile and page.evaluate('window.injected === undefined'))
            with page.expect_download() as info:
                page.locator('#download').click()
            dest = out / 'exported-talk.html'; info.value.save_as(dest); exported = dest.read_text(); pages['/exported'] = exported
            check('export includes notes and exact source text', 'Private draft note: review before sharing.' in exported and 'Fictional S1, lines 2–4' in exported)
            check('export retains template code license and separate content rights', 'Copyright (c) 2026 Idea Talks contributors' in exported and 'Permission is hereby granted, free of charge' in exported and 'authored content retain their own rights' in exported)
            check('export escapes authored markup', '&lt;script&gt;window.injected=1&lt;/script&gt;' in exported and '<script>window.injected=1</script>' not in exported)
            exported_page = context.new_page(); exported_page.on('pageerror', lambda e: report['page_errors'].append(str(e)))
            exported_page.goto(base + '/exported', wait_until='networkidle')
            check('export reopens independently', exported_page.locator('section.slide').count() == 9 and exported_page.locator('[data-edit="title"]').inner_text() == hostile)
            check('export fresh identity and edit reset', exported_page.locator('body').get_attribute('data-deck-id') != page.locator('body').get_attribute('data-deck-id') and exported_page.locator('#edit-button').get_attribute('aria-pressed') == 'false' and exported_page.locator('#note-editor').get_attribute('readonly') is not None)
            check('export cannot execute edited markup', exported_page.evaluate('window.injected === undefined') and exported_page.locator('img').count() == 0)
            page.reload(wait_until='networkidle'); check('original local draft restores', page.locator('[data-edit="title"]').inner_text() == hostile)
            other = context.new_page(); other.goto(base + '/fixture', wait_until='networkidle'); check('different talk has independent browser draft', other.locator('[data-edit="title"]').inner_text() == 'Try one clearer first question')
            # Use the adequate template snapshot for responsive/readability checks.
            page.evaluate('localStorage.clear()'); page.reload(wait_until='networkidle')
            for width in [1440, 390, 360]:
                page.set_viewport_size({'width': width, 'height': 1000}); overflows=[]
                for i in range(9):
                    page.evaluate('i=>IdeaTalks.goTo(i)', i)
                    if page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'): overflows.append(i)
                check('no horizontal overflow at ' + str(width), not overflows, failed_slides=overflows)
                page.evaluate('IdeaTalks.goTo(0)'); page.screenshot(path=str(out / ('desktop.png' if width == 1440 else 'phone-' + str(width) + '.png')), full_page=True)
            page.emulate_media(media='print'); check('print shows nine slides and notes', page.locator('section.slide').evaluate_all("els=>els.filter(e=>getComputedStyle(e).display!=='none').length") == 9 and page.locator('.slide-notes').first.is_visible())
            page.pdf(path=str(out/'talk-print.pdf'), landscape=True, print_background=True)
            nojs = browser.new_context(java_script_enabled=False, viewport={'width': 360, 'height': 1000}); nojs.route('**/*', route)
            reading = nojs.new_page(); reading.goto(base+'/template', wait_until='networkidle')
            check('no-JavaScript shows nine readable slides and source notes', reading.locator('section.slide').evaluate_all("els=>els.filter(e=>getComputedStyle(e).display!=='none').length") == 9 and reading.locator('.slide-notes').first.is_visible())
            check('no-JavaScript no horizontal overflow', not reading.evaluate('document.documentElement.scrollWidth > innerWidth + 1'))
            check('no external document requests', not report['external_requests'], requests=report['external_requests'])
            check('no page JavaScript errors', not report['page_errors'], errors=report['page_errors'])
            browser.close()
    except Exception as error:
        report['terminal_error'] = str(error)
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)
    report['passed'] = all(c['passed'] for c in report['checks']) and 'terminal_error' not in report
    report['passed_checks'] = sum(c['passed'] for c in report['checks']); report['total_checks'] = len(report['checks'])
    (out/'RESULT.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['passed','passed_checks','total_checks']}))
    return 0 if report['passed'] else 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='New receipt directory; refuses overwrite')
    parser.add_argument('--chromium', help='Already installed Chromium; never downloaded')
    raise SystemExit(run(parser.parse_args()))
