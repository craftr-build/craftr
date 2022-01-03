"""
A tiny client for the [DejaCode license library][1].

  [1]: https://enterprise.dejacode.com/licenses/
"""

import argparse
import re
import textwrap
import typing as t

import bs4
import requests

BASE_URL = 'https://enterprise.dejacode.com/licenses/public/{}/'


def _get_table_value_by_key(soup, key):
  regex = re.compile('\s*' + re.escape(key) + '\s*')
  item = soup.find('span', text=regex)
  if item is None:
    raise ValueError('<span/> for {!r} not found'.format(key))
  value = item.parent.findNext('dd').find('pre').text
  if value == '\xa0':
    value = ''
  return value or None


def _get_license_text(soup):
  tab = soup.find(id='tab_license-text')
  if tab is None:
    raise ValueError('#tab_license-text not found')
  pre = soup.find('div', {'class': 'clipboard'}).find('pre')
  return pre.text


def get_license_metadata(license_name):
  """ Retrives the HTML metadata page for the specified license from the
  DejaCode website and extracts information such as the name, category,
  license type, standard notice and license text. """

  url = BASE_URL.format(license_name.replace(' ', '-').lower())
  response = requests.get(url)
  response.raise_for_status()
  html = response.text
  soup = bs4.BeautifulSoup(html, 'html.parser')

  extract_keys = [
    'Key', 'Name', 'Short Name', 'Category', 'License type', 'License profile', 'License style', 'Owner',
    'SPDX short identifier', 'Keywords', 'Standard notice', 'Special obligations', 'Publication year', 'URN',
    'Dataspace', 'Homepage URL', 'Text URLs', 'OSI URL', 'FAQ URL', 'Guidance URL', 'Other URLs'
  ]

  data = {}
  for key in extract_keys:
    data[key.replace(' ', '_').lower()] = _get_table_value_by_key(soup, key)
  data['publication_year'] = int(data['publication_year'])
  if data['standard_notice']:
    data['standard_notice'] = textwrap.dedent(data['standard_notice'])
  data['license_text'] = _get_license_text(soup)

  return data


def wrap_license_text(license_text: str, width: int = 79) -> str:
  lines = []
  for raw_line in license_text.split('\n'):
    line = raw_line.split(' ')
    length = sum(map(len, line)) + len(line) - 1
    if length > width:
      words: t.List[str] = []
      length = -1
      for word in line:
        if length + 1 + len(word) >= width:
          lines.append(' '.join(words))
          words = []
          length = -1
        else:
          words.append(word)
          length += len(word) + 1
      if words:
        lines.append(' '.join(words))
    else:
      lines.append(' '.join(line))
  return '\n'.join(lines)


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('license')
  parser.add_argument('--json', action='store_true')
  parser.add_argument('-w', '--width', type=int, default=79)
  args = parser.parse_args()
  license = get_license_metadata(args.license)
  if args.json:
    import json
    print(json.dumps(license, indent=2))
  else:
    print(wrap_license_text(license['license_text'], args.width))
