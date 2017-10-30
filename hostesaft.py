#!/usr/bin/env python3
import argparse
import asyncio
import sys
import socket

import aiohttp


class Response(object):
    def __init__(self, resp, host):
        self.host = host
        self.url = resp.url
        self.status = resp.status
        self.full_status = str(self.status)
        if resp.reason:
            self.full_status += " " + resp.reason
        self.location = resp.headers['Location'] if 301 <= resp.status <= 303 else None
    
    def __str__(self):
        if self.location:
            return "{} :: {}\n\t--> {}".format(self.host, self.full_status, self.location)
        else:
            return "{} :: {}".format(self.host, self.full_status)


async def fetch_url(session, url, host):
    headers = {"Host": host}
    async with session.get(url, headers=headers, allow_redirects=False) as resp:
        return Response(resp, host)


async def main(url, hosts, cookies):
    jar = aiohttp.CookieJar(unsafe=True)
    jar.update_cookies(cookies)

    conn = aiohttp.TCPConnector(verify_ssl=False, limit_per_host=4, family=socket.AF_INET)
    async with aiohttp.ClientSession(connector=conn, cookie_jar=jar) as session:
        futures = [ fetch_url(session, url, host) for host in hosts ]
        responses = await asyncio.gather(*futures)
        responses.sort(key=lambda x: x.status)
        print('\n'.join(map(str, responses)))


# TODO:
# Compare output to default host
# Compare output to actual host if it resolves

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    parser.add_argument("-f", "--hosts", type=argparse.FileType('r'), required=True)
    parser.add_argument("-c", "--cookies")

    args = parser.parse_args()

    hosts = [ host.strip() for host in args.hosts.readlines() ]

    url = args.target
    if not url.startswith("http"):
        url = "https://"+url

    if args.cookies:
        cookies = dict( c.strip().split('=', 1) for c in args.cookies.split(';') )
    else:
        cookies = {}

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(url, hosts, cookies))
