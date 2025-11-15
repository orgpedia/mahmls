import csv
import json
import sys
from pathlib import Path

# pid,Assembly_No,Poll_No,Year,Candidate,Candidate_Type,State_Name,Constituency_Name,Constituency_Type,Party,Last_Party,Votes,Sex,Position,Contested,Turncoat,Incumbent,Vote_Share_Percentage,Margin,Margin_Percentage,Age,Alliance,Terms,Terms_Contested # noqa

def read_csv_file(csv_file_path):
    with open(csv_file_path, 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        data = [row for row in csv_reader]
    header = data.pop(0)
    return header, data

def get_gender(gender_value):
    if gender_value:
        return {'m': 'Male', 'f': 'Female', '': 'Not Given'}[gender_value[0].lower()]
    else:
        return ''


assembly_file_dict = {
    '2014': 'mh-incumbency-12.csv',
    '2019': 'mh-incumbency-13.csv',
}


input_dir = Path(sys.argv[1])
output_dir = Path(sys.argv[2])

picture_header, picture_data = read_csv_file( input_dir / 'mh-pids.csv' )
picture_dict = dict((tcpd_id, picture_url) for (tcpd_id, picture_url) in picture_data)

party_header, party_names = read_csv_file( input_dir / 'mh-party-expanded.csv' )
party_names = dict(party_names)


legislators = []
for (year, csv_file_name) in assembly_file_dict.items():
    header, data = read_csv_file( input_dir / csv_file_name )
    for row in data:
        row_dict = dict(zip(header, row))

        if row_dict['Position'] != '1' or row_dict['Year'] != year:
            continue

        legislator = {'year': year, 'house': 'assembly'}

        legislator['tcpdID'] = row_dict['pid']
        legislator['name'] = row_dict['Candidate']
        legislator['party'] = party_names[row_dict['Party']]
        legislator['gender'] = get_gender(row_dict['Sex'])
        legislator['constituency'] = row_dict['Constituency_Name']
        legislator['constituency_type'] = row_dict['Constituency_Type']
        legislator['image_url'] = picture_dict.get(legislator['tcpdID'], '')
        legislator['votes'] = row_dict['Votes']
        legislator['vote_share_percentage'] = row_dict['Vote_Share_Percentage']
        legislator['vote_margin'] = row_dict['Margin']
        legislator['vote_margin_percentage'] = row_dict['Margin_Percentage']
        legislator['age'] = row_dict['Age']



        
        legislators.append(legislator)

Path(output_dir / 'tcpd_legislators.json').write_text(json.dumps(legislators))
"""
{
    "year": "2014",
    "house": "assembly",
    "tcpdID": "AEMH100024",
    "name": "LAHANE HARIBHAN VITHALRAO",
    "party": "SHS",
    "gender": "M",
    "constituency": "PATHRI",
    "constituency_type": "GEN",
    "image_url": "",
    "votes": "37437",
    "vote_share_percentage": "42.83",
    "vote_margin": "14717",
    "vote_margin_percentage": "16.84",
    "age": ""
  },

(0, 'pid')
(1, 'Assembly_No')
(2, 'Poll_No')
(3, 'Year')
(4, 'Candidate')
(5, 'Candidate_Type')
(6, 'State_Name')
(7, 'Constituency_Name')
(8, 'Constituency_Type')
(9, 'Party')
(10, 'Last_Party')
(11, 'Votes')
(12, 'Sex')
(13, 'Position')
(14, 'Contested')
(15, 'Turncoat')
(16, 'Incumbent')
(17, 'Vote_Share_Percentage')
(18, 'Margin')
(19, 'Margin_Percentage')
(20, 'Age')
(21, 'Alliance')
(22, 'Terms')
(23, 'Terms_Contested')


"""
