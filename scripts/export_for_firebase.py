"""Export roster data only; never export Django accounts, sessions or images."""
import argparse
import json
from pathlib import Path
import sqlite3
from contextlib import closing

ROOT = Path(__file__).resolve().parent.parent
TYPES = ['fire', 'water', 'electric', 'grass', 'ice', 'fighting', 'poison', 'ground', 'flying',
         'psychic', 'bug', 'rock', 'ghost', 'dragon', 'dark', 'steel', 'fairy', 'normal']


def export(database, output):
    database, output = Path(database).resolve(), Path(output).resolve()
    if not database.is_file():
        raise ValueError('Database not found')
    if output.exists():
        raise ValueError('Output already exists; choose another filename')
    members = []
    with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as connection:
        connection.execute('BEGIN')
        for member_id, name, notes in connection.execute('SELECT id, name, notes FROM roster_member ORDER BY id'):
            ratings = {f'{kind}_{category}': {'status': 'no', 'condition': ''}
                       for kind in TYPES for category in ['physical', 'special']}
            for kind, category, status, condition in connection.execute(
                    'SELECT pokemon_type, category, status, condition FROM roster_participation WHERE member_id=?', (member_id,)):
                if f'{kind}_{category}' in ratings:
                    ratings[f'{kind}_{category}'] = {'status': status, 'condition': condition}
            members.append({'name': name, 'notes': notes, 'ratings': ratings})
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump({'version': 1, 'members': members}, stream, ensure_ascii=False, indent=2)
    return len(members)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', type=Path, default=ROOT / 'db.sqlite3')
    parser.add_argument('--output', required=True, type=Path)
    arguments = parser.parse_args()
    try:
        count = export(arguments.database, arguments.output)
    except (ValueError, sqlite3.Error) as error:
        parser.error(str(error))
    print(f'Exported {count} roster rows. Accounts, sessions and images were excluded.')
