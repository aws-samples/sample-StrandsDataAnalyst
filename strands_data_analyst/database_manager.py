import pathlib
import json
import logging

from strands_data_analyst.databases import DATABASES

DATABASES_DIR = pathlib.Path(__file__).parent.resolve() / ".." / "data" / "databases"


class LocalDatabaseManager:
    def __init__(self):
        self.dbs = {}
        for db in DATABASES_DIR.iterdir():
            info_file = db / 'info.json'
            if not info_file.exists():
                continue

            db_info = json.load(open(info_file))
            if db_info['type'] not in DATABASES:
                logging.warning(f"Unknown database type: {db_info['type']}")
                continue
            
            self.dbs[db.name] = db_info

            if db_info['type'] == 'sqlite':
                db_info['db_location'] = str(db / db_info['filename'])

    def init_db(self, db_id):
        db_info = self.dbs[db_id]
        return DATABASES[db_info['type']](db_info)

    def get_list(self):
        return list(self.dbs.keys())
    
    def get_info(self, db_id):
        return self.dbs[db_id]
