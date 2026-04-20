import requests
import datetime
import json
import time
import re

from pathlib import Path

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

    time.sleep(0.25)
    return wiki_data_id

def get_image_url(title):
    BaseURL = 'https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&piprop=original&titles='
    response = requests.get(f'{BaseURL}{title}')
    response_dict = json.loads(response.text)
    image_url = list(response_dict['query']['pages'].values())[0].get('original', {'source':''})['source']
    return image_url


def get_html_content(revision_id):
    page_title = "Maharashtra_Legislative_Council"

    # api_url =  "https://en.wikipedia.org/w/index.php?title=Maharashtra_Legislative_Council&oldid=757373235
    api_url = f"https://en.wikipedia.org/w/index.php?title={page_title}&oldid={revision_id}"

    # Make the API request
    response = requests.get(api_url)
    return response.text


def get_page_revions_ids(title, num_revisions=500):
    # Define the Wikipedia API endpoint
    api_url = "https://en.wikipedia.org/w/api.php"

    # Define your parameters
    params = {
        "action": "query",
        "format": "json",
        "prop": "revisions",
        "titles": "Maharashtra_Legislative_Council",
        "rvlimit": 500,  # Adjust the limit as needed, 500 is max
        "rvprop": "timestamp|ids",
    }

    all_revisions = []
    num_counts = 0
    # Make the API request
    while True:
        response = requests.get(api_url, params=params)

        # Parse the JSON response
        data = response.json()

        # Extract the revision information
        import pdb

        pdb.set_trace()

        print(num_counts)
        num_counts += 1

        page_id = list(data['query']['pages'])[0]

        assert int(page_id) == data['query']['pages'][page_id]['pageid']
        revisions = data['query']['pages'][page_id]['revisions']
        all_revisions += revisions

        if 'continue' in data:
            params['continue'] = data['continue']['continue']
            params['rvcontinue'] = data['continue']['rvcontinue']
        else:
            return page_id, all_revisions

    return page_id, all_revisions


def get_tables(html_str):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_str, features='html.parser')

    name_links = []
    filtered_tables = []
    for table in soup.findAll("table"):
        table_data = []
        for row in table.find_all('tbody')[0].find_all('tr'):
            if '<th' in str(row):
                row_data = [th.text.strip() for th in row.find_all('th')]
            else:
                row_data = [td.text.strip() for td in row.find_all('td')]
                name_links += [(td.text.strip(), td.a['href']) for td in row.find_all('td') if td.a]
            table_data.append(row_data)

        first_row = '|'.join(c.strip() for c in table_data[0])

        if 'Member' in first_row or 'Constituency' in first_row:
            print(f'\t{first_row}')
            filtered_tables.append(table_data)

    # print(f'Found tables: {len(filtered_tables)}')
    return filtered_tables, name_links


def build_members_info(revision_id, revision_date, page_tables):
    def extract_assembly_elected(table):
        small_table = True if len(table[0]) == 4 else False
        member_infos = []
        header_row = table.pop(0) # noqa
        for row in table:
            member_info = dict((k, '') for k in member_fields.split(','))
            member_info['revision_id'], member_info['revision_date'] = revision_id, str(revision_date)
            member_info['elected_type'] = 'assembly_elected'

            if len(row) == 6:
                row.pop(2)
            
            member_info['name'] = row[1]
            member_info['party'] = row[2]
            if not small_table:
                member_info['start_date'] = row[3]
                member_info['end_date'] = row[4]
            else:
                member_info['term'] = row[3]
            members.append(member_info)
        return members

    def extract_constituency_elected(table, table_idx):
        small_table = True if len(table[0]) == 5 else False        
        member_infos = []
        header_row = table.pop(0) # noqa

        
        for row in table:
            member_info = dict((k, '') for k in member_fields.split(','))
            member_info['revision_id'], member_info['revision_date'] = revision_id, str(revision_date)
            member_info['constituency'] = row[1]
            member_info['name'] = row[2]
            if member_info['name'] == 'Vacant':
                continue

            if len(row) == 7:
                row.pop(2)
                
            member_info['party'] = row[3]
            member_info['elected_type'] = ['', 'local_authorities', 'teachers', 'graduates']

            if not small_table:
                member_info['start_date'] = row[4]
                member_info['end_date'] = row[5]
            else:
                member_info['term'] = row[4]

            members.append(member_info)
        return members

    def extract_governor_nominated(table):
        small_table = True if len(table[0]) == 4 else False

        member_infos = []
        header_row = table.pop(0) # noqa
        for row in table:
            member_info = dict((k, '') for k in member_fields.split(','))
            member_info['revision_id'], member_info['revision_date'] = revision_id, str(revision_date)
            member_info['elected_type'] = 'governor_nominated'
            member_info['name'] = row[1]
            if member_info['name'] == 'Vacant':
                continue
            
            member_info['party'] = row[2]
            if not small_table:
                member_info['start_date'] = row[3]
                member_info['end_date'] = row[4]
            else:
                member_info['term'] = row[3]
            members.append(member_info)
        return members

    def clean_fields(member):
        member['name'] =  re.sub(r'\[[^\]]*\]', '', member['name'])
        return member

    print(revision_date, revision_id, len(page_tables))    
    if not page_tables:
        print('\tNo TABLES !!')
        return []

    if len(page_tables[0][0]) == 2:
        print('\tRemoving first table')
        page_tables.pop(0)

    member_fields = (
        'name,party,start_date,end_date,elected_type,constituency,revision_id,revision_date'
    )

    members = []
    for table_idx, table in enumerate(page_tables):
        if table_idx == 0:
            members += extract_assembly_elected(table)
        elif table_idx < 4:
            members += extract_constituency_elected(table, table_idx)
        else:
            members += extract_governor_nominated(table)
            
    members = [ clean_fields(m) for m in members ]
    return members


revisions_file = Path('revisions.json')
if not revisions_file.exists():
    page_title = 'Maharashtra_Legislative_Council'
    page_id, revisions = get_page_revions_ids(page_title)
    revisions_file.write_text(json.dumps(revisions))
else:
    revisions = json.loads(revisions_file.read_text())


current_month, current_year = -1, -1
name_link_dict, members = {}, []
for revision in revisions:
    rev_date = datetime.datetime.strptime(revision['timestamp'], "%Y-%m-%dT%H:%M:%SZ")
    if rev_date.year < 2015:
        break

    # if rev_date.month != current_month:
    #     current_month = rev_date.month

    if current_year == rev_date.year:
        continue

    current_year = rev_date.year

    revision_html = get_html_content(revision['revid'])
    page_tables, name_links = get_tables(revision_html)

    new_dict = dict((k, v) for (k,v) in name_links if k and v.startswith('/wiki/'))
    name_link_dict = {**name_link_dict, **new_dict}

    members += build_members_info(revision['revid'], rev_date, page_tables)

    time.sleep(1)

#end for

en_names = Path('names.en.txt').read_text().split('\n')
mr_names = Path('names.mr.txt').read_text().split('\n')
name_trans_dict = dict((e,m) for (e, m) in zip(en_names, mr_names))
title_wikiID_dict = {}

for member in members:
    member['mr_name'] = name_trans_dict[member['name']]
    
    name_link = name_link_dict.get(member['name'], '')
    if name_link and 'red_link' not in name_link:
        name_title = name_link[6:]
        if name_title not in title_wikiID_dict:
            member['wikiID'] = fetch_wikidata_id(name_title)
            title_wikiID_dict[name_title] = member['wikiID']
            print(f'\t name_title: {name_title} wikiID: {member["wikiID"]}')
        else:
            member['wikiID'] = title_wikiID_dict[name_title]

        member['wiki_url'] = f'https://en.wikipedia.org{name_link}'
        member['image_url'] = get_image_url(name_title)
    else:
        member['wiki_url'] = ''
        member['wikiID'] = ''
        member['image_url'] = ''


Path('wiki_council_legislators.json').write_text(json.dumps(members))
