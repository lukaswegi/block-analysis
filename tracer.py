# Basic PoC script for extracting transaction traces from ethereum.
import argparse

import os
from os import listdir
from os.path import isfile, join
from collections import defaultdict
import sys

import time
import web3
import json
from web3 import Web3

# https://geth.ethereum.org/docs/dapp/custom-tracer
# https://geth.ethereum.org/docs/rpc/ns-debug#debug_tracetransaction

# basic tracer that returns a dict where each entry is the program counter
# height and the value is the relevant interesting data to the opcode we were looking for
tracer = """
{ retVal: {}, 

         byte2Hex: function(byte) { 
           if (byte < 0x10)  
               return "0" + byte.toString(16); 
           return byte.toString(16); 
         }, 

         array2Hex: function(arr) {
           var retVal = ""; 
           for (var i=0; i<arr.length; i++) 
             retVal += this.byte2Hex(arr[i]); 
           return retVal; 
         }, 

         getAddr: function(log) {
           return this.array2Hex(log.contract.getAddress());
         }, 

step: function(log,db) { 

if(log.op.toNumber() == 0x40) { 
            ret = {};
            ret.pc = log.getPC();
            ret.opcode = "BLOCKHASH";
            ret.op = log.op.toNumber();
            ret.current_addr = this.getAddr(log);
            ret.caller = this.array2Hex(log.contract.getCaller());
            this.retVal[ret.pc] = ret;
            this.retVal["has_blockhash"] = true;
        }

},
fault: function(log,db) {this.retVal.fault = JSON.stringify(log)},
result: function(ctx,db) {
                this.retVal.block = ctx.block;
                this.retVal.txHash = this.array2Hex(ctx.txHash);
                this.retVal.from = this.array2Hex(ctx.from);
                this.retVal.to = this.array2Hex(ctx.to);
                return this.retVal
            }
}
"""


def prepare_output_dir(output_dir: str) -> bool:
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)


def blockrange(start: int, end: int):
    if end < start:
        raise argparse.ArgumentTypeError('invalid block range')
    return


def fixErrorTransaction(filePath):
    try:
        base = os.path.basename(filePath)
        root_ext = os.path.splitext(base)
        if root_ext[1] == ".error":
            # check if there already is a non-error trace.

            print("Attempting to fix error txn " + root_ext[0])
            # 45m should be more than enough for fixing!
            tx_trace = w3.manager.request_blocking("debug_traceTransaction", [root_ext[0],
                                                                              {"disableStorage": args.disableStorage,
                                                                               "disableMemory": args.disableMemory,
                                                                               "disableStack": args.disableStack,
                                                                               "timeout": str(timeout) + "s",
                                                                               "tracer": tracer, }])
            json_tx_trace = Web3.toJSON(tx_trace)
            with open(os.path.join(os.path.dirname(filePath), root_ext[0] + ".json"), 'w', encoding='utf-8') as f:
                f.write(json_tx_trace)
            # if file successfully written delete error one
            os.remove(filePath)
    except Exception as e:
        print("Error {0}, could not fix transaction {1}".format(str(e), base))


def fixErrorTransactions(outputDir):
    # go through all block folders and check if we have txns that errored out
    # TODO -> dumpTransaction should check if a dump already exists and if its non-erronous and only try to re-download if errored out!
    for path in listdir(outputDir):
        subdir = join(outputDir, path)
        for file in listdir(subdir):
            file_path = join(subdir, file)
            fixErrorTransaction(file_path)


def dumpTransaction(tx, outputDir):
    tries = 2
    for i in range(tries):
        try:
            tx_trace = w3.manager.request_blocking("debug_traceTransaction", [tx.hex(),
                                                                              {"disableStorage": args.disableStorage,
                                                                               "disableMemory": args.disableMemory,
                                                                               "disableStack": args.disableStack,
                                                                               "timeout": str(timeout) + "s",
                                                                               "tracer": tracer, }])

            if 'has_blockhash' in tx_trace:
                # convert to json
                print("dumping tx %s" % tx.hex())
                json_tx_trace = Web3.toJSON(tx_trace)

                # write txns to disk.
                prepare_output_dir(outputDir)

                with open(os.path.join(outputDir, tx.hex() + ".json"), 'w', encoding='utf-8') as f:
                    f.write(json_tx_trace)
        except Exception as e:
            if i < tries - 1:
                continue
            else:
                # raise e
                # try to indicate which transaction parsing failed
                prepare_output_dir(outputDir)
                with open(os.path.join(outputDir, tx.hex() + ".error"), 'w', encoding='utf-8') as f:
                    f.write(str(e))
        break


# TODO proper argparsing

my_parser = argparse.ArgumentParser(
    description='Extract transaction traces containing BLOCKHASH from a geth archive node')

# Note: it appears that having . directories in the file path leads to the ipcprovider not resolving properly...
my_parser.add_argument('--ipcFile', action='store', type=str, default='geth.ipc',
                       help='provide the path to the unix domain socket from geth, note that folders starting with. may not resolve properly')

my_parser.add_argument('--outputDir', help='output directory', type=str, default=os.path.curdir)

my_parser.add_argument('--blockRange', action='store', type=int, nargs=2)
my_parser.add_argument('--toBlockFolders', action='store_true')
my_parser.add_argument('--disableStorage', action='store_true')
my_parser.add_argument('--disableMemory', action='store_true')
my_parser.add_argument('--disableStack', action='store_true')
my_parser.add_argument('--fixErrorTxns', action='store_true')
my_parser.add_argument('--fixErrorTx', type=str, help='full path to erro transaction')
my_parser.add_argument('--timeout', action='store', type=int, default=600, help='timout in seconds')

args = my_parser.parse_args()

ipc_file = args.ipcFile

if not os.path.exists(ipc_file):
    print('The ipc file specified does not exist')
    sys.exit()

# timeout = 600
timeout = args.timeout

provider = Web3.IPCProvider('geth.ipc', timeout)
w3 = Web3(provider)
if not w3.isConnected():
    print('could not connect to web3 provider')
    sys.exit()

if args.fixErrorTxns:
    fixErrorTransactions(args.outputDir)
elif args.fixErrorTx is not None:
    fixErrorTransaction(args.fixErrorTx)
else:
    if args.blockRange[1] < args.blockRange[0]:
        raise argparse.ArgumentTypeError('invalid block range')
        sys.exit()
    # dump transactions that contain blockhash opcode
    for i in range(args.blockRange[0], args.blockRange[1] + 1):
        block = w3.eth.get_block(i)
        for tx in block.transactions:
            dumpTransaction(tx, args.outputDir)
            # todo does it make sense to wait to avoid node from being too taxed?
            # time.sleep(0.1)

# block.transactions

# tx = block.transactions[0]
# dumpTransaction(tx,args.outputDir)
# dumpBlock(block,args.outputDir)

