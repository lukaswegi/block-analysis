import os
import json
from datetime import datetime
import web3
import pandas as pd

web3_erigon = web3.Web3(web3.Web3.HTTPProvider("http://127.0.0.1:8545", request_kwargs={'timeout': 3600}))

df = pd.DataFrame(index=["block_number", "tx_hash", "from", "to", "value", "gas", "gas_price"])

for index, filename in enumerate(sorted(os.listdir("../blocks_json"))):
    f = open("../blocks_json/" + filename)
    data = json.load(f)
    miner_ = data['Header']['miner']
    ts_ = int((data['Header']['timestamp']), 16)

    transactions_ = data['Body']['Transactions']
    datetime.utcfromtimestamp(ts_).strftime('%Y-%m-%d %H:%M:%S'),

    for tx in transactions_:
        # ts_t = int((tx['timestamp']), 16)
        # timestamps.append(ts_t)
        tx_status = web3_erigon.eth.getTransactionByHash(tx['hash'])
        print(tx_status)


