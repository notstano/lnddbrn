"""
A simple transformation of batch_all extrinsics fetched with Subscrape.
The extrinsics are filtered to contain 2 remarks - the first one must contain RMRK::BURN::2 and KANCHAMP - those are
the extrinsics used to burn Land Deeds (for Skybreach).

This file is with broken imports for Subscrape since it's not yet production ready, I think:
 * there is no version in PyPi
 * there is no setup.py file so I can't install it from local directory as well
Therefore the way I use this file is by placing it in the Subscrape project itself and run it from there. You need:
 * Subscan Api key, follow the instructions in Subscrape

The script is tracked this repo as is for historical purposes, reference and means of replication.
"""
import csv
import dataclasses
import json
import logging
from collections import Counter

import subscrape
from subscrape.db.subscrape_db import SubscrapeDB

CONFIG = {
    "kusama": {
        "extrinsics": {
            "_filter": [{"block_timestamp": [{">": 1644796800}]}],
            "utility": ["batch_all"]
        }
    }
}

DB = SubscrapeDB("Kusama")


@dataclasses.dataclass(frozen=True)
class Burn:
    extrinsic_id: str
    rmrk_call: str
    burn_memo: str


def load_batch_all(db: SubscrapeDB):
    return db.extrinsics_iter(call_module='utility', call_name='batch_all')


def filter_rmrk2_burn(extrinsic: dict):
    params = json.loads(extrinsic['params'])[0]

    if not params or not params['value']:
        return False

    values = [v for v in params['value']
              if v['call_index'] == '0001'
              and v['call_module'] == 'System'
              and v['call_name'] == 'remark']

    if len(values) != 2:
        # our target extrinsics only have 2 values (calls) - one for the RMRK::BURN remark and one for the the burn memo
        return False

    rmrk_call = values[0]
    if 'RMRK::BURN::2' not in rmrk_call['params'][0]['value']:
        return False

    if 'KANCHAMP' not in rmrk_call['params'][0]['value']:
        return False

    return True


def transform_extrinsic(extrinsic: dict):
    params = json.loads(extrinsic['params'])[0]
    values = [v for v in params['value']]
    rmrk_call = values[0]['params'][0]['value']
    burn_memo = values[1]['params'][0]['value']

    return Burn(extrinsic['extrinsic_index'], rmrk_call, burn_memo)


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    logging.info('Loading data')
    subscrape.scrape(CONFIG)

    logging.info('Transforming remarks')
    extrinsics = [extrinsic for _, extrinsic in load_batch_all(DB)]
    burned = [e for e in extrinsics if filter_rmrk2_burn(e)]
    result = [transform_extrinsic(extrinsic) for extrinsic in burned]

    logging.info(f'Deeds burned: {Counter([r.rmrk_call.split("-")[-2] for r in result]).most_common()}')

    logging.info('Saving results')
    with open('lnddbrns.json', 'w+') as f:
        json.dump([r.__dict__ for r in result], f)
    logging.info("Done")


if __name__ == '__main__':
    main()
