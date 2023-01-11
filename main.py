import json
from datetime import datetime
import os
import web3

miners = dict()
blocks = []

web3 = web3.Web3(web3.Web3.HTTPProvider("http://127.0.0.1:8545", request_kwargs={'timeout': 3600}))


class Transaction:
    def __int__(self, block_number, hash, sender, receiver, value, gas, gas_price):
        self.block_number = block_number
        self.hash = hash
        #self.sender = sender
        #self.receiver = receiver
        #self.value = value
        #self.gas = gas
        #self.gas_price = gas_price
        self.status = None


class Block:
    def __init__(self, number, timestamp, difficulty, miner, ts, hash, transactions):
        self.number = number
        self.timestamp = timestamp
        self.difficulty = difficulty
        self.miner = miner
        self.ts = ts
        self.hash = hash
        self.transaction_hashes = transactions
        self.tx_failed = 0
        self.tx_success = 0
        self.transactions = []

    def checkTransactionStatus(self, tx):
        tx_status = None
        try:
            tx_status = web3.eth.get_transaction(tx['hash'])
        except Exception as ex:
            print("failed")

        transaction = Transaction(self.number, tx['hash'])

        if tx_status is None:
            transaction.status = False
            self.tx_failed += 1
        else:
            transaction.status = True
            self.tx_success += 1
        self.transactions.append(transaction)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return str(self.number) + " " + self.timestamp + " " + str(self.transactions)


for index, filename in enumerate(sorted(os.listdir("blocks_json"))):
    f = open("blocks_json/" + filename)
    data = json.load(f)
    miner_ = data['Header']['miner']
    ts_ = int((data['Header']['timestamp']), 16)
    difficulty_ = int((data['Header']['difficulty']), 16)
    number_ = int((data['Header']['number']), 16)
    hash_ = data['Header']['hash']
    transactions_ = data['Body']['Transactions']
    block = Block(number_,
                  datetime.utcfromtimestamp(ts_).strftime('%Y-%m-%d %H:%M:%S'),
                  difficulty_,
                  miner_,
                  ts_,
                  hash_,
                  len(transactions_))

    for tx in transactions_:
        block.checkTransactionStatus(tx)

    blocks.append(block)

    if miner_ in miners:
        miners[miner_] += 1
    else:
        miners[miner_] = 1




