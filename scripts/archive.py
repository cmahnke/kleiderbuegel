#!/usr/bin/env python

import os, argparse, pathlib, sys, asyncio, httpcore
from urllib.parse import urlparse
from dateutil.parser import parse
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
from termcolor import cprint

archive_prefix = "https://web.archive.org/save/"
available_prefix = "http://archive.org/wayback/available?url="
default_dir = "./docs"
exclude = ['localhost', 'projektemacher.org', 'de.wikipedia.org', 'en.wikipedia.org', 'github.com', 'gohugo.io', 'archive.org']
max_age = 60

def check_availability(url):
    available_url = f"{available_prefix}{url}"
    req = httpx.get(available_url)
    json = req.json()
    if req.status_code == 200 and "archived_snapshots" in json and json["archived_snapshots"]:
        last = json["archived_snapshots"]["closest"]["timestamp"]
        last = parse(last, fuzzy=True)
        age = datetime.now() - last
        if age.days > max_age:
            cprint(f"URL {url} snapshot is older then {max_age}!", 'yellow')
            return False
        cprint(f"URL {url} has been archived within the last {max_age}!", 'green')
        return True
    else:
        cprint(f"URL {url} is not archived!", 'yellow')
        return False

async def archive(urls, client):
    async_reqs = []
    for url in urls:
        archive_url = f"{archive_prefix}{url}"
        try:
            if not check_availability(url):
                async def req(url):
                    try:
                        resp = await client.get(url)
                        resp.raise_for_status()
                    except (httpx.ReadTimeout, httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError, httpcore.ReadTimeout) as error:
                        cprint(f"", 'red')
                async_reqs.append(req(archive_url))
                print(f"Saving {archive_url}")
        except:
            cprint(f"Failed to check availability of {url}", 'red')
    return async_reqs

def filter_links(links):
    def url_filter(item):
        if item.startswith('http'):
            up = urlparse(item)
            if not up.hostname in exclude:
                return item

    flat = sum(links, [])
    unique = list(set(flat))

    return list(filter(url_filter, unique))

def extract_links(file):
    urls = []
    with open(file, "r") as handle:
        soup = BeautifulSoup(handle.read(), 'html.parser')
        for link in soup.find_all('a'):
            urls.append(link.get('href'))
    return urls

def build_file_list(dir):
    htmls = []
    for path, dirnames, files in os.walk(dir):
        for file in files:
            (base, ext) = os.path.splitext(file)
            if ext != '' and ext in ('.html'):
                htmls.append(os.path.join(path, file))
    return htmls

def build_url_list(dir):
    files = build_file_list(dir)
    urls = []
    for file in files:
        urls.append(extract_links(file))
    urls = filter_links(urls)
    return urls

async def main() -> int:
    parser = argparse.ArgumentParser(prog='archive.py')
    parser.add_argument('--dir', '-d', type=pathlib.Path, help='Path to posts to process')
    parser.add_argument('--exclude', '-e', nargs='+', help='Host names to exclude')

    args = parser.parse_args()

    if args.dir is not None:
        dir = args.dir
    else:
        dir = default_dir

    if args.exclude is not None:
        for excl in args.exclude:
            exclude.extend(excl.split(','))
        cprint(f"Excluding {exclude}", 'green')

    urls = build_url_list(dir)

    client = httpx.AsyncClient(timeout=120)
    async_reqs = await archive(urls, client)
    await asyncio.gather(*async_reqs)
    await client.aclose()
    cprint(f"Saved {len(async_reqs)} URLs", 'green')

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
