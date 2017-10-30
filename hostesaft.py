#!/usr/bin/env python3
import argparse
import asyncio
import sys
import socket

import aiohttp


class Log(object):
    def __init__(self, resp, host):
        self.host = host
        self.url = resp.url
        self.status = resp.status
        self.location = resp.headers['Location'] if 301 <= resp.status <= 303 else None
    
    def __str__(self):
        if self.location:
            return "{} :: {} --> {}".format(self.host, self.status, self.location)
        else:
            return "{} :: {}".format(self.host, self.status)


async def fetch_url(session, url, host):
    headers = {"Host": host}
    async with session.get(url, headers=headers, allow_redirects=False) as resp:
        return Log(resp, host)


async def main(url, hosts):
    conn = aiohttp.TCPConnector(verify_ssl=False, limit_per_host=4, family=socket.AF_INET)
    async with aiohttp.ClientSession(connector=conn) as session:
        futures = [ fetch_url(session, url, host) for host in hosts ]
        logs = await asyncio.gather(*futures)
        logs.sort(key=lambda x: x.status)
        print('\n'.join(map(str, logs)))


# TODO:
# Compare output to default host
# Compare output to actual host if it resolves

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    parser.add_argument("-f", "--hosts", type=argparse.FileType('r'), required=True)

    args = parser.parse_args()
    hosts = [ host.strip() for host in args.hosts.readlines() ]
    url = args.target
    if not url.startswith("http"):
        url = "https://"+url

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(url, hosts))