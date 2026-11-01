PYTHON ?= python3
.PHONY: build check eval
build:
	$(PYTHON) scripts/check.py --build
check:
	$(PYTHON) scripts/check.py
eval:
	$(PYTHON) scripts/test_template_browser.py --output .eval-output --chromium "$(CHROMIUM)"
