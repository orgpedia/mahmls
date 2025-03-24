import json
import sys
import time
from pathlib import Path

import requests


def fetch_wikidata_id(title):
    BaseURL = 'https://en.wikipedia.org/w/api.php?action=query&prop=pageprops&ppprop=wikibase_item&redirects=1&format=json&titles='
    response = requests.get(f'{BaseURL}{title}')
    response_dict = json.loads(response.text)

    wiki_data_id = ''
    pages_values = list(response_dict['query']['pages'].values())
    if pages_values:
        page_dict = pages_values[0]
        wiki_data_id = page_dict.get('pageprops', {}).get('wikibase_item', '')

    if not wiki_data_id:
        wiki_data_id = f'https://en.wikipedia.org/wiki/{title.replace(" ", "_")}'

    time.sleep(2)
    return wiki_data_id

def get_image_url(title):
    BaseURL = 'https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&piprop=original&titles='
    response = requests.get(f'{BaseURL}{title}')
    response_dict = json.loads(response.text)
    image_url = list(response_dict['query']['pages'].values())[0].get('original', {'source':''})['source']
    return image_url


Stubs = ['2014-assembly', '2019-assembly']
input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
legislators_path = input_dir / 'legislators.json'
legislators = json.loads(legislators_path.read_text())

for legislator in legislators:
    lr = legislator
    if lr['wikiID'][0] != 'Q':
        print(f'missing {lr["year"]}[{lr["constituency_idx"]:3}] {lr["name"]:30} {lr["wiki_url"]}')

    title = lr["wiki_url"].split('/')[-1]
    if title:
        lr['image_url'] = get_image_url(title)
    else:
        lr['image_url'] = ''
    

legislators_path.write_text(json.dumps(legislators, indent=2))





"""
for stub in Stubs:

    winners = (input_dir / f'{stub}-winners.txt').read_text().split('\n')
    winners_links = (input_dir / f'{stub}-winners-links.txt').read_text().split('\n')
    winners_wikiIDs = (input_dir / f'{stub}-winners-wikiID.txt').read_text().split('\n')

    const = (input_dir / f'{stub}-constituency.txt').read_text().split('\n')
    const_links = (input_dir / f'{stub}-constituency-links.txt').read_text().split('\n')
    const_wikiIDs = (input_dir / f'{stub}-constituency-wikiID.txt').read_text().split('\n')

    assert len(winners) == len(winners_links) == len(winners_wikiIDs)
    assert len(const) == len(const_links) == len(const_wikiIDs) == len(winners)


    for idx in range(len(winners)):
        year, house = stub.split('-')
        legislator = lr = {'year': year, 'house': house}

        w, wl, ww = winners[idx], winners_links[idx], winners_wikiIDs[idx]
        c, cl, cw = const[idx], const_links[idx], const_wikiIDs[idx]

        lr['name'], lr['wiki_url'], lr['wikiID'] = w, wl, ww
        lr['constituency'], lr['constituency_url'], lr['constituency_wikiID'] = c, cl, cw
        lr['constituency_idx'] = idx + 1
        lr['image_urls'] = []


        legislators.append(lr)

        if ww and ww[0] == 'Q':
            continue

        if 'redlink' in wl:
            print(f'{w:40} ** {wl}')
            continue

        if not wl:
            print(f'{w:40} ** Add')
            continue


        name = wl.replace('https://en.wikipedia.org/wiki/', '')
        new_ww = fetch_wikidata_id(name)

        print(f'{w}: {new_ww}')
        lr['wikiID'] = new_ww
        lr['name'] = name
"""
