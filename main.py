import argparse
import datetime
import json
from collections import Counter, defaultdict
from functools import partial

import matplotlib.pyplot as plt
import streamlit as st
from google.cloud import storage
from google.oauth2 import service_account

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('--file',
                        help='A file with extrinsics in json format. Optional and mainly used for development.'
                             'If missing, a default GCP bucket file would be used.',
                        default=None,
                        required=False)
ARGS = arg_parser.parse_args()

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
DEED_TYPE_TO_ID = {'Common': 'LNDDC', 'Rare': 'LNDDR', 'Epic': 'LNDDE'}
DEED_ID_TO_TYPE = {v: k for k, v in DEED_TYPE_TO_ID.items()}


# class Colors(enum.Enum):
#     COMMON = '#70DE66' # as in LE bird
#     RARE = '#61D8FB' # as in Rare bird
#     EPIC = '#ECC1FB' # as in Founder bird

# Plot the main distribution for types of deeds
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


def load_extrinsics():
    """
    A helper method to load previously scraped extrinsics from a file.
    If the file was provided as command line argument it would be loaded from local storage.
    Otherwise, a GCP bucket file is loaded by default.

    :return: A json object with all the extrinsics from the provided file.
    """
    _file_load = None

    if ARGS.file:
        def _read_file(file_name):
            with open(file_name) as f:
                return f.read()
        _file_load = partial(_read_file, file_name=ARGS.file)
    else:
        # To be loaded from a bucket
        BURN_FILE = "lnddbrns.json"

        credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
        storage_client = storage.Client(credentials=credentials)

        @st.experimental_memo(ttl=600)
        def _read_file(bucket_name, file_path):
            bucket = storage_client.bucket(bucket_name)
            content = bucket.blob(file_path).download_as_string().decode("utf-8")
            return content

        _file_load = partial(_read_file, bucket_name="rmrk-extrinsics-bucket", file_path=BURN_FILE)

    with st.spinner("Loading extrinsics..."):
        burn_extrinsics = _file_load()
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
ax.bar_label(p2)
ax.legend()
st.pyplot(fig)


# Plot daily burned deeds by type
burned_by_day = defaultdict(list)
for extrinsic in burned:
    timestamp = extrinsic['extrinsic']['block_timestamp']
    date = datetime.date.fromtimestamp(timestamp)
    burned_by_day[date].append(extrinsic)

deeds = defaultdict(dict)
for type_of_deed in ['LNDDC', 'LNDDR', 'LNDDE']:
    def _filter_by_type(extrinsic):
        return extrinsic['rmrk_call'].split('-')[-2] == type_of_deed

    deeds[type_of_deed] = {date: list(filter(_filter_by_type, burned))
                           for date, burned in burned_by_day.items()}


fig, ax = plt.subplots()

common_deeds_per_day = [len(d) for d in deeds['LNDDC'].values()]
rare_deeds_per_day = [len(d) for d in deeds['LNDDR'].values()]
epic_deeds_per_day = [len(d) for d in deeds['LNDDE'].values()]
b1 = ax.bar(list(deeds['LNDDC'].keys()), common_deeds_per_day,
            label='Common')
b2 = ax.bar(list(deeds['LNDDR'].keys()), rare_deeds_per_day,
            bottom=common_deeds_per_day,
            label='Rare')
b3 = ax.bar(list(deeds['LNDDE'].keys()), epic_deeds_per_day,
            bottom=list(map(sum, zip(common_deeds_per_day, rare_deeds_per_day))),
            label='Epic')
ax.set_title('Burned deeds per day')
ax.legend()
plt.xticks(rotation=45)
st.pyplot(fig)


#
# Display top EVM addresses and search for an address.
#
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

