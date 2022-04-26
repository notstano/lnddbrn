import argparse
import json

from collections import Counter
from google.oauth2 import service_account
from google.cloud import storage
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
import streamlit as st

st.title("Land deeds")
st.markdown('''
A simple exploration of Skybreach Land Deeds
 * types of deeds and their counts
 * amount of deeds burned, per type
 * search for burn memos, e.g. evm addresses
 
 ---
''')

# Hardcoded, found earlier by querying and parsing the result once.
DEED_COUNTS = {'Common': 7308,
               'Rare': 721,
               'Epic': 149}
DEED_TYPES = list(DEED_COUNTS.keys())

parser = argparse.ArgumentParser(description='Track on-chain burns of Skybreach land deeds')
parser.add_argument('--burn_exts_file', required=True,
                    help="Path to a json file in GCP bucket with burn extrinsics saved at a previous step")
args = parser.parse_args()

st.header('Land deed types')
st.markdown(f'''
* Common: {DEED_COUNTS['Common']}
* Rare: {DEED_COUNTS['Rare']}
* Epic: {DEED_COUNTS['Epic']}
Total: {sum(DEED_COUNTS.values())}
''')
fig, (ax1, ax2) = plt.subplots(ncols=2)
# fig.suptitle('Land deed types')
bars = ax1.bar(list(DEED_COUNTS.keys()), DEED_COUNTS.values(), align='center')
ax1.bar_label(bars, fmt='%.0f')
ax2.pie(DEED_COUNTS.values(), labels=DEED_COUNTS.keys(),
        autopct='%1.0f%%', startangle=90)
ax2.axis('equal')
st.pyplot(fig)


BURN_FILE = args.burn_exts_file


def load_extrinsics():
    credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
    storage_client = storage.Client(credentials=credentials)

    @st.experimental_memo(ttl=600)
    def _read_file(bucket_name, file_path):
        bucket = storage_client.bucket(bucket_name)
        content = bucket.blob(file_path).download_as_string().decode("utf-8")
        return content

    with st.spinner("Loading extrinsics..."):
        burn_extrinsics = _read_file(bucket_name="rmrk-extrinsics-bucket",
                                     file_path=BURN_FILE)
        burn_extrinsics = json.loads(burn_extrinsics)
        return burn_extrinsics



burned = load_extrinsics()
burned_by_type = Counter([item['rmrk_call'].split('-')[-2]
                          for item in burned])
st.header("Burned Deeds")
st.markdown(f'''
Found {len(burned)} burned deeds:
* Common: {burned_by_type['LNDDC']}
* Rare: {burned_by_type['LNDDR']}
* Epic: {burned_by_type['LNDDE']}
''')

fig, ax = plt.subplots()
p1 = ax.bar(DEED_TYPES,
            list(burned_by_type.values()),
            color='r', label='Burned Deeds')
p2 = ax.bar(DEED_TYPES,
            [total-burned for total, burned in zip(DEED_COUNTS.values(), burned_by_type.values())],
            # TODO the difference is here
            bottom=list(burned_by_type.values()), label='Total deeds')
ax.set_ylabel('Number of deeds')
ax.set_title('Number of burned deed per type')
ax.bar_label(p1, label_type='center')
# ax.bar_label(p2, label_type='center')
ax.bar_label(p2)
ax.legend()
st.pyplot(fig)

st.header("Most used EVM addresses")
st.markdown("EVM address mapped to the number of burn memos it's encountered in.")
topN_evm = Counter([item['burn_memo'] for item in burned])
addresses = [f'{addr[:4]}....{addr[-4:]} -> {count}'
             for index, (addr, count) in enumerate(topN_evm.most_common(n=10))]
st.code('\n'.join(addresses))


st.markdown("---")
search_address = st.text_input(label="Search for an evm address",
                               help='An EVM address or part of it')
search_address = search_address.lstrip('0x')
if search_address:
    addresses = [f'{addr[:4]}....{addr[-4:]} -> {count}'
                 for (addr, count) in topN_evm.items()
                 if search_address in addr]
    if addresses:
        st.code('\n'.join(addresses))
    else:
        st.warning('None found')

