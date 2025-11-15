"""
{
    "year": "2014",
    "house": "assembly",
    "name": "Govardhan Sharma",
    "myneta_url": "https://myneta.info/maharashtra2014/candidate.php?candidate_id=886",
    "constituency": "AAKOLA WEST",
    "image_urls": []
  },
   {
    "year": "2014",
    "house": "assembly",
    "tcpdID": "AEMH100252",
    "name": "BHUMRE SANDIPANRAO AASARAM",
    "party": "SHIV SENA",
    "gender": "Male",
    "constituency": "PAITHAN",
    "constituency_type": "GEN",
    "image_url": "https://suvidha.eci.gov.in/uploads/candprofile/E4/2019/AC/S13/Bhuma-2019-20191008051948.png",
    "votes": "66991",
    "vote_share_percentage": "34.52",
    "vote_margin": "25039",
    "vote_margin_percentage": "12.9",
    "age": "52"
  },

  {
    "year": "2014",
    "house": "assembly",
    "name": "K. C. Padavi",
    "wiki_url": "https://en.wikipedia.org/wiki/Kagda_Chandya_Padvi",
    "wikiID": "Q18750303",
    "constituency": "Akkalkuwa",
    "constituency_url": "https://en.wikipedia.org/wiki/Akkalkuwa_Assembly_constituency",
    "constituency_wikiID": "Loading...",
    "constituency_idx": 1,
    "image_url": ""
  },
"""
import json
from pathlib import Path

import yaml


def load_simple_hierarchy(input_file):
    constituency_list = yaml.load(Path(input_file).read_text(), Loader=yaml.FullLoader)
    constituency_dict = {}
    for c_dict in constituency_list["assembly_contituencies"]:
        c = c_dict["name"].lower()
        constituency_dict[c] = c
        for a in c_dict["alias"]:
            constituency_dict[a.lower()] = c
    return constituency_dict


def load_json(file_path):
    return json.loads(Path(file_path).read_text())


def merge_assembly_legislators(myneta, tcpd, wiki, constituency_dict):
    # wikiID -> wiki_dict

    assembly_legis_dict, cy_dict = {}, {}
    cd = constituency_dict

    for legis in wiki:
        a_legis = assembly_legis_dict.get(legis["wikiID"], None)
        if a_legis is None:
            a_legis = assembly_legis_dict.setdefault(legis["wikiID"], legis)
            a_legis["constituency"] = constituency_dict[a_legis["constituency"].lower()]
            a_legis["alias"] = []
        else:
            assert a_legis["wiki_url"] == legis["wiki_url"], f'Unmatched wiki_url {a_legis["wikiID"]} {a_legis["wiki_url"]} <> {legis["wiki_url"]}'
            if a_legis["name"] != legis["name"]:
                a_legis["alias"].append(legis["name"])
        cy_dict[(a_legis['constituency'], a_legis['year'])] = legis['wikiID']

    for legis in myneta:
        if legis["name"] == "" or legis["house"] != "assembly":
            continue

        wikiID = cy_dict[(legis["constituency"], legis["year"])]
        assembly_legis_dict[wikiID].setdefault("myneta_urls", []).append(legis["myneta_url"])

    for legis in tcpd:
        if legis["name"] == "" or legis["house"] != "assembly":
            continue

        wikiID = cy_dict[(legis["constituency"], legis["year"])]
        a_legis = assembly_legis_dict[wikiID]

        a_legis.setdefault("tcpdIDs", []).append(legis["tcpdID"])
        a_legis.setdefault("genders", []).append(legis["gender"])
        a_legis.setdefault("image_urls", []).append(legis["image_url"])

        e_fields = [
            "year",
            "constituency",
            "constituency_type",
            "votes",
            "votes_share_percentage",
            "vote-margin",
            "votes_margin_percentage",
        ]

        election_result = dict((k, legis(k)) for k in e_fields)
        election_result["constituency"] = constituency_dict[election_result["constituency"]]

        a_legis.sedefaule("election_results", []).append(election_result)
    return assembly_legis_dict


myneta_legislators = load_json("input/myneta_legislators.json")
tcpd_legislators = load_json("input/tcpd_legislators.json")
wiki_assembly_legislators = load_json("input/wiki_assembly_legislators.json")
wiki_council_legislators = load_json("input/wiki_council_legislators.json")

constituency_dict = load_simple_hierarchy("conf/constituency.yml")

assembly_legis_dict = merge_assembly_legislators(
    myneta_legislators, tcpd_legislators, wiki_assembly_legislators, constituency_dict
)
