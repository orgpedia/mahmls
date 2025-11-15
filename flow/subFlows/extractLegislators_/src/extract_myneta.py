import json
import sys
from pathlib import Path


Stubs = ['2014-assembly', '2019-assembly', 'current-council', 'earlier-council']
def build_legislators(input_dir):
    legislators = []
    for stub in Stubs:
        winners = (input_dir / f'{stub}-winners.txt').read_text().split('\n')
        winners_links = (input_dir / f'{stub}-winners-links.txt').read_text().split('\n')
        const = (input_dir / f'{stub}-constituency.txt').read_text().split('\n')

        assert len(winners) == len(winners_links) == len(const)
    
        for idx in range(len(winners)):
            year, house = stub.split('-')
            if house == 'assembly':
                legislator = lr = {'year': year, 'house': house}  # noqa
            else:
                legislator = lr = {'period': year, 'house': house}  # noqa
    
            w, wl, c = winners[idx], winners_links[idx], const[idx]
    
            lr['name'], lr['myneta_url'], lr['constituency'] = w, wl, c
            lr['image_urls'] = []
            
            legislators.append(lr)

    return legislators

def main():
    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    legislators_file = output_dir / 'myneta_legislators.json'
    if not legislators_file.exists():
        legislators = build_legislators(input_dir)
        legislators_file.write_text(json.dumps(legislators))
    else:
        legislators = json.loads(legislators_file.read_text())

main()
