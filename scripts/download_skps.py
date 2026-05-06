import argparse
import asyncio
import json
import logging
import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import Browser, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@dataclass
class Args:
    urls: Path
    out: Path


def existing_path(value: str):
    path = Path(value)

    if not path.exists():
        raise argparse.ArgumentTypeError('path does not exist')

    return path


def parse_args() -> Args:
    parser = argparse.ArgumentParser()
    parser.add_argument('urls', type=existing_path)
    parser.add_argument('out', type=Path)

    return Args(**vars(parser.parse_args()))


async def dump_skp(
    browser: Browser,
    semaphore: asyncio.Semaphore,
    name: str,
    url: str,
    path: Path,
    timeout: int,
    wait_for: int,
):
    async with semaphore:
        context = await browser.new_context()
        page = await context.new_page()

        logger.info(f'{name} - opening {url}')
        try:
            await page.goto(url, timeout=timeout, wait_until='domcontentloaded')
            await page.wait_for_timeout(wait_for)

            logger.info(f'{name} - dumping skps')

            output_dir = json.dumps(str(path.absolute()))
            await page.evaluate(f'chrome.gpuBenchmarking.printToSkPicture({output_dir})')
            logger.info(f'{name} - skps dumped')
        except PlaywrightTimeoutError as exc:
            logger.error(f'{name} - timeout loading page {exc}')
        except Exception as exc:
            logger.error(f'{name} - failed to dump skp {exc}')
        finally:
            await page.close()
            await context.close()


async def dump_skps_in_par(
    urls: list[tuple[str, str, Path]],
    workers: int,
    timeout: int,
    wait_for: int,
):
    semaphore = asyncio.Semaphore(max(1, workers))

    async with async_playwright() as pw:
        logger.info('starting up Chrome')
        browser = await pw.chromium.launch(
            headless=True, args=['--no-sandbox', '--enable-gpu-benchmarking']
        )

        try:
            tasks = [
                asyncio.create_task(
                    dump_skp(browser, semaphore, name, url, path, timeout, wait_for)
                )
                for name, url, path in urls
            ]

            await asyncio.gather(*tasks)
        finally:
            logger.info('closing Chrome')
            await browser.close()


def flatten_skps_in_place(skps_root: Path) -> None:
    moves: list[tuple[Path, Path]] = []

    for site_dir in skps_root.iterdir():
        if not site_dir.is_dir():
            continue

        site_name = site_dir.name
        for skp_file in site_dir.glob('*.skp'):
            dst = skps_root / f'{site_name}__{skp_file.name}'
            moves.append((skp_file, dst))

    for src, dst in moves:
        src.rename(dst)

    for site_dir in skps_root.iterdir():
        if site_dir.is_dir():
            site_dir.rmdir()


def main():
    args = parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    skps = args.out / 'skps'
    skps.mkdir(parents=True, exist_ok=True)

    with args.urls.open('rb') as fp:
        urls = tomllib.load(fp)

    urls_to_dump: list[tuple[str, str, Path]] = []
    for name, url in urls.items():
        output_path = skps / name
        output_path.mkdir(parents=True, exist_ok=True)

        url = url if url.startswith('http://') or url.startswith('https://') else 'https://' + url

        urls_to_dump.append((name, url, output_path))

    asyncio.run(
        dump_skps_in_par(
            urls_to_dump,
            max(1, min(4, os.cpu_count() or 1)),
            60000,
            2000,
        )
    )

    flatten_skps_in_place(skps)

    logger.info('flattened skps')


if __name__ == '__main__':
    main()
