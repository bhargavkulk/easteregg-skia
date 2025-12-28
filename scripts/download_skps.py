import argparse
import tomllib
from pathlib import Path
from typing import Any

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


class SkpDumpError(RuntimeError):
    """Raised when generating an SKP for a URL fails."""


def dump_skp(browser, name: str, url: str, out_root: Path) -> None:
    site_dir = out_root / name
    site_dir.mkdir(parents=True, exist_ok=True)
    page = browser.new_page()
    try:
        full_url = url if url.startswith('https://') else f'https://{url}'
        try:
            page.goto(full_url, timeout=60000)
        except PlaywrightTimeoutError as exc:
            raise SkpDumpError(f'[{name}] timeout loading page: {exc}') from exc
        except PlaywrightError as exc:
            raise SkpDumpError(f'[{name}] failed to load page: {exc}') from exc

        page.wait_for_timeout(5000)

        try:
            page.evaluate(f"chrome.gpuBenchmarking.printToSkPicture('{site_dir.absolute()}')")
        except PlaywrightError as exc:
            raise SkpDumpError(f'[{name}] failed to dump SKP: {exc}') from exc

    finally:
        page.close()


def process_urls(urls: dict[str, Any], out_dir: Path) -> None:
    try:
        with sync_playwright() as playwright:
            print('[*] starting Chrome')
            browser = playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--enable-gpu-benchmarking'],
            )
            try:
                for name, url in urls.items():
                    print(f'[*] processing {name}')
                    site_dir = out_dir / name
                    dump_skp(browser, name, url, out_dir)
                    for layer in site_dir.glob('*.skp'):
                        target = out_dir / f'{name}__{layer.name}'
                        layer.rename(target)
                    site_dir.rmdir()
            finally:
                print('[*] closing browser')
                browser.close()
    except SkpDumpError as exc:
        print(f'[error] {exc}')
        raise SystemExit(1)
    except PlaywrightError as exc:
        print(f'[error] Playwright failed to start Chrome: {exc}')
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description='Dump SKPs from Chrome via Playwright.')
    parser.add_argument('input_file', type=Path, help='TOML file containing url = value entries')
    parser.add_argument('skp_folder', type=Path, help='Directory to place SKP outputs')
    args = parser.parse_args()

    with args.input_file.open('rb') as handle:
        urls = tomllib.load(handle)

    process_urls(urls, args.skp_folder)


if __name__ == '__main__':
    main()
