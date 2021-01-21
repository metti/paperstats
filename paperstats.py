#!/usr/bin/env python3
#
# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Autor: Matthias Maennich <matthias@maennich.net>
#

from collections import defaultdict
import concurrent.futures
import re
import sys

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.nature.com"
QUERY_URL = BASE_URL + "/nrdp/articles?type=primer&year=2020"


def main():
  r = requests.get(QUERY_URL)
  soup = BeautifulSoup(r.content, "html.parser")

  articles = sorted(
      soup.find_all("article"),
      key=lambda x: x.select_one("time").get("datetime"))

  urls = [
      BASE_URL + a.find(attrs={
          "data-track-action": "view article"
      }).get("href") for a in articles
  ]

  futures = []
  with concurrent.futures.ThreadPoolExecutor() as executor:

    for url in urls:
      futures.append(executor.submit(parse_article, url))

    global_stats = defaultdict(int)

    for future in futures:
      out, stats = future.result()
      print(out)
      print()

      for country, count in stats.items():
        global_stats[country] += count

  print("\n\n-- TOTAL --\n\n")

  for country, count in sorted(global_stats.items()):
    print("\t{:20s}\t{}".format(country.upper(), count))


def parse_article(url):
  r = requests.get(url)
  soup = BeautifulSoup(r.content, "html.parser")

  date = soup.select_one("time", attrs={"itemprop": "datePublished"}).string
  title = soup.select_one(".c-article-title").string
  out = "{}\n  {} - {}\n\n".format(date, title, url)

  # abusing the order of a dict and None values to have an ordered set
  author_map = defaultdict(dict)
  stats = defaultdict(int)

  l = soup.select_one(".c-article-author-affiliation__list")
  for aff in l.select("li"):
    address = aff.select_one(".c-article-author-affiliation__address").string
    country = address.rsplit(",", 1)[1].strip()
    authors = aff.select_one(
        ".c-article-author-affiliation__authors-list").string
    authors = [author.strip() for author in re.split(",|&", authors)]

    if "Netherlands" in country:
      country = "The Netherlands"

    for author in authors:
      author_map[author][country] = None

  for author, countries in sorted(author_map.items()):
    out += "\t{:30s}\t{}\n".format(author, ", ".join(countries.keys()))

    stats[list(countries)[0]] += 1

  out += "\n"

  for country, count in sorted(stats.items()):
    out += "\t{:20s}\t{}\n".format(country, count)

  return out, stats


if __name__ == "__main__":
  main()
