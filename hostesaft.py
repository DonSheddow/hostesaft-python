#!/usr/bin/env python3
import argparse
import asyncio
import difflib
import random
import string
import sys
import socket

import aiohttp


class Response(object):
    @classmethod
    async def get(cls, session, url, host=None):
        self = Response()
        self.url = url
        self.host = host
        self.interesting = False

        headers = {"Host": host} if host else {}
        async with session.get(url, headers=headers, allow_redirects=False, timeout=10) as resp:
            self.status = resp.status
            self.full_status = str(resp.status)
            if resp.reason:
                self.full_status += " " + resp.reason
            self.location = resp.headers['Location'] if 301 <= resp.status <= 303 else None
            self.bytes = await resp.read()

        return self

    def __str__(self):
        note = "[!!] " if self.interesting else ""
        if self.location:
            return "{}{} :: {}\n\t--> {}".format(note, self.host, self.full_status, self.location)
        else:
            return "{}{} :: {}".format(note, self.host, self.full_status)

    def is_equal_to(self, other):
        if other is None:
            return False
        if self.status != other.status:
            return False
        if 301 <= self.status <= 303:
            return self.location == other.location

        s = difflib.SequenceMatcher(None, self.bytes, other.bytes)
        return s.ratio() > 0.95



async def fetch_url(session, url, host, default_resp):
    try:
        normal_resp = await Response.get(session, 'https://'+host)
    except:
        normal_resp = None

    response = await Response.get(session, url, host)

    if not response.is_equal_to(normal_resp) and not response.is_equal_to(default_resp):
        response.interesting = True

    return response


async def main(url, hosts, cookies):
    jar = aiohttp.CookieJar(unsafe=True)
    jar.update_cookies(cookies)

    conn = aiohttp.TCPConnector(verify_ssl=False, limit_per_host=4, family=socket.AF_INET)
    async with aiohttp.ClientSession(connector=conn, cookie_jar=jar) as session:

        random_host = ''.join(random.choice(string.ascii_lowercase) for _ in range(20))
        default_resp = await Response.get(session, url, random_host)

        futures = [ fetch_url(session, url, host, default_resp) for host in hosts ]
        responses = await asyncio.gather(*futures)
        responses.sort(key=lambda x: x.status)
        print('\n'.join(map(str, responses)))


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
