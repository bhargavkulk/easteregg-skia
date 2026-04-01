#!/usr/bin/env python3
import argparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Print browser version used by Playwright Chromium launcher.'
    )
    parser.parse_args()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                print('channel=playwright-bundled-chromium')
                print(f'executable_path={p.chromium.executable_path}')
                print(f'browser_version={browser.version}')
            finally:
                browser.close()
    except PlaywrightError as exc:
        print(f'Failed to launch browser: {exc}')
        raise SystemExit(1)


if __name__ == '__main__':
    main()
