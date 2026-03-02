[![License](https://img.shields.io/badge/license-GPLv3-green.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-README-blue)](https://github.com/gokgokdak/tornadocash-py#readme)
[![GitHub stars](https://img.shields.io/github/stars/gokgokdak/tornadocash-py?style=flat)](https://github.com/gokgokdak/tornadocash-py/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/gokgokdak/tornadocash-py)](https://github.com/gokgokdak/tornadocash-py/issues)
[![Python application](https://github.com/gokgokdak/tornadocash-py/actions/workflows/python-app.yml/badge.svg?branch=main)](https://github.com/gokgokdak/tornadocash-py/actions/workflows/python-app.yml)


*__Security Warnings__*  
* *Only run the __AUDITED__ open source code and scripts locally or binaries compiled on your machine*  
* *Do not trust or use __ANY__ Tornado Cash service from the webpage or IPFS*  
* *There’s no longer any such thing as an "official website" after the sanctions*  
* *Any websites that claim themselves as "official" are 100% __FAKE__*  
* *See 👉 [[Block Domain] Fake ethereum Tornado cash websites Phishing](https://github.com/MetaMask/eth-phishing-detect/issues/13826)*


*__Compliance Statement__*  
*This project provides open-source client software to interact with on-chain smart contracts.*  
*It does not custody funds, relay transactions for others, run a mixing service, or charge fees.*  
*The code is offered as-is for educational and interoperability purposes only.*  
*By using this software, you are solely responsible for how you use it. You must:*  

* *Comply with all applicable laws and regulations in your jurisdiction (e.g., AML/CFT, sanctions/export controls).*
* *Avoid interacting with sanctioned persons, entities, or addresses, and perform your own due diligence.*
* *Use at your own risk; no warranties or guarantees are provided.*  

*Nothing here constitutes legal advice. If you are unsure about your obligations, consult qualified counsel before using this software.*  


# TornadoCash-py

A Python implementation to interact with Tornado Cash smart contracts.  

Similar to the original [tornado-cli](https://github.com/tornadocash/tornado-cli), but more features and better experience


- [Preparations](#preparations)
  - [Download Code](#download-code)
  - [Download Database](#download-database)
  - [Sync Blockchain](#sync-blockchain)
  - [RPC Service](#rpc-service)
  - [Proxy Configuration (Optional)](#proxy-configuration-optional)
  - [Node.js Runtime (Optional)](#nodejs-runtime-optional)
- [Running Unittests](#running-unittests)
- [Functionality Testing](#functionality-testing)
- [Usage & Tutorial](#usage--tutorial)
  - [Deposit](#deposit)
  - [Batch Deposit](#batch-deposit)
  - [Offline Deposit](#offline-deposit)
  - [Withdraw](#withdraw)
  - [Batch Withdraw](#batch-withdraw)
  - [Query Deposit Age](#query-deposit-age)
- [Known Relayers](#known-relayers)
- [Supported Deployments](#supported-deployments)


## Preparations

### Download Code

Required minimum Python version `3.10+`, recommend `3.13`  

Clone this repository and install dependencies    
    
```bash
git clone https://github.com/gokgokdak/tornadocash-py.git
cd tornadocash-py
pip install -r requirements.txt
```
  
### Download Database
According to the Tornado Cash protocol, to initiate a withdrawal, the user is required to rebuild the merkle tree with the contract's **ALL** historical commitments to calculate the latest tree root, which means we have to save a copy of all contract events locally.  

Download the database cache for the first startup to accelerate this process.  
Put all `.sqlite` files under the `./db` directory.    

```bash
# Under the tornadocash-py root directory
cd db
git clone https://github.com/gokgokdak/tornadocash-db.git cache
mv cache/*.sqlite .
rm -rf cache
```

### Sync Blockchain

The downloaded database has about 1~15 days delay, to make sure the data is up-to-date, please sync the blockchain data before the first use.  
`python cli.py --sync <chain> <symbol> <unit>`  

Or, sync all deployments:  
`python cli.py --sync_all`    

It is recommended to keep the program running to stay synchronized with the blockchain, simply add a `--keep` option to `--sync` or `--sync_all` command.  

### RPC Service

If RPC error `ADDRESS_SANCTIONED` occurs during deposit or withdrawal, or any RPC errors during the syncing process, please change to another RPC provider manually, replace the `RPC_URLS` variable in `config.py` with your own endpoint.  

![](/assets/readme_rpc.png)


### Proxy Configuration (Optional)

If you need to route all network requests through a proxy server, you can configure the `RPC_PROXY_URL` variable in `config.py`.    

Supported proxy protocols:  
- **HTTP**: `http://host:port` or `http://username:password@host:port`  
- **HTTPS**: `https://host:port` or `https://username:password@host:port`  
- **SOCKS5**: `socks5://host:port` or `socks5://username:password@host:port`  

When a proxy is configured, the CLI will print the visible IP address at startup and ask you to confirm it is as expected:
```log
[I 2026-03-02 10:00:00:000 tid=12345 cli] Proxy configured: socks5://127.0.0.1:1080
[I 2026-03-02 10:00:01:000 tid=12345 cli] Proxy visible IP: 203.0.113.42
Is this your expected proxy IP? (y/n): y
```

#### Using Tor as a Proxy

This project does not bundle Tor, but if you have a running Tor service (default `127.0.0.1:9050`) or Tor Browser (default `127.0.0.1:9150`), you can route traffic through it:
```python
RPC_PROXY_URL = 'socks5://127.0.0.1:9050'
```

> **Note:**  
> Routing through Tor will significantly increase latency and blockchain synchronization time, especially for the initial sync.
> It is recommended to use a fast and stable proxy if you choose to use one.


### Node.js Runtime (Optional)

Node.js runtime is required, version 14 or above is recommended.  

Setup boolean variable `BUNDLED_NODE_JS` to specify the runtime.  

If `True`, will try to use the Node.js runtime on your machine if found, please make sure command `node` is available in your PATH environment, otherwise use the bundled binary under the `./zk/bin/` directory.  
If `False`, only the bundled binary under the `./zk/bin/` directory will be used.  

![](/assets/readme_nodejs.png)

See 👉 [Node.js official website](https://nodejs.org/en/download) for installation if you don't want to use the bundled binary.  


## Running Unittests

It is **HIGHLY** recommended to run all unit tests before using this program, to make sure the mathematics and cryptographic calculations are correct on your machine.  
```bash
python -m unittest discover -s test -p "test_*.py"
# Or
pytest -q
```


## Functionality Testing
To test the deposit and withdrawal functionalities, you can use the Ethereum Sepolia testnet to try it out.  
Here are some faucets to obtain Sepolia ETH without account registration:

Alchemy 👉 [https://www.alchemy.com/faucets/ethereum-sepolia](https://www.alchemy.com/faucets/ethereum-sepolia)    
Chainlink 👉 [https://faucets.chain.link/sepolia](https://faucets.chain.link/sepolia)  
Google 👉 [https://cloud.google.com/application/web3/faucet/ethereum/sepolia](https://cloud.google.com/application/web3/faucet/ethereum/sepolia)    
QuickNode 👉 [https://faucet.quicknode.com/ethereum/sepolia](https://faucet.quicknode.com/ethereum/sepolia)  


## Usage & Tutorial

### Deposit

The private key is used to provide ETHs for deposit and pay for gas fees, make sure it has enough balance.
```bash
# python cli.py --deposit <key> <chain> <symbol> <unit>
# <key>   : Private key to provide ETHs for deposit and pay the gas fee, hex string, '0x' prefix is optional
# <chain> : Name of the chain, values: ethereum, optimism, bsc, polygon, arbitrum, avalanche, sepolia. Case insensitive
# <symbol>: Name of the token, values: eth, bnb, pol, avax, dai, cdai, usdt, usdc, wbtc. Case insensitive
# <unit>  : Tornado unit of coins, eg: 0.1, 1, 10, ...

> python cli.py --deposit 0x0f36dead4beafdead4beafdead4beafdead4beafdead4beafdead4beafde9a66 sepolia eth 0.1
```

If succeeded, you will see logs like below, and the generated note will be printed to the console and saved to a backup file under the `./backup` directory.  
The `note` has full access to the deposited funds, please keep it private and secure.
```log
[I 2025-10-10 10:22:21:477 tid=43284 cli] Depositing Sepolia 0.1 eth (cli.py:357)
[I 2025-10-10 10:22:21:570 tid=43284 cli] IMPORTANT: Please save the note text below and keep it private (cli.py:377)
[I 2025-10-10 10:22:21:570 tid=43284 cli] IMPORTANT: sepolia-eth-0.1-d27c296fdb802bea47c3675b296a67a72daf9ad7398f4c5ba57c897d2e3215-0a2cda03f6c56f7e3b65cef86fb228db9ab6e5630078101d77fb80a93fe81f (cli.py:378)
[I 2025-10-10 10:22:26:970 tid=43284 Tornado] deposit(from=0xA09CBdDb54c7bD239F80b252d25002001580BafF) succeed, tx hash: 9607560ad3795d860e1be630ba32c121540f88c0d662d1782ede29eb46b0afe5 (core.py:271)
[I 2025-10-10 10:22:26:971 tid=43284 cli] IMPORTANT: Note backup saved to /home/nova/tornadocash-py/backup/2025-10-10_10.22.21.570_sepolia_eth_0.1.txt (cli.py:388)
```

### Batch Deposit

A very convenient way if you have multiple addresses on different chains that holds multiple kinds of assets, this feature do it at once :)  

```bash
# python cli.py --deposit_batch <key> <json>
# <key> : Private key to provide ETHs for deposit and pay the gas fee, hex string, '0x' prefix is optional
# <json>: JSON string to describe a batch, eg:
#         {"ethereum": {"eth": {"10": 100, "100": 20}}, "polygon": {"pol": {"100000": 1000}}}'

> python cli.py --deposit_batch 0x0f36dead4beafdead4beafdead4beafdead4beafdead4beafdead4beafde9a66 "{'sepolia':{'eth':{'0.1':3}}}"
```


### Offline Deposit

Create a note on the offline machine, scan the QR code or copy the invoice text to the online machine  
```bash
# python cli.py --create_note <chain> <symbol> <unit>
# <chain> : Name of the chain, values: ethereum, optimism, bsc, polygon, arbitrum, avalanche, sepolia. Case insensitive
# <symbol>: Name of the token, values: eth, bnb, pol, avax, dai, cdai, usdt, usdc, wbtc. Case insensitive
# <unit>  : Tornado unit of coins, eg: 0.1, 1, 10, ...

> python cli.py --create_note sepolia eth 0.1
[I 2025-10-10 09:46:45:111 tid=39724 stdout]  ▄▄▄▄▄▄▄ ▄▄▄         ▄ ▄▄▄  ▄  ▄▄▄▄▄▄▄ 
[I 2025-10-10 09:46:45:111 tid=39724 stdout]  █ ▄▄▄ █  █▄█ ▀ ███ █▄█▀▄█▀▄▄█ █ ▄▄▄ █ 
[I 2025-10-10 09:46:45:112 tid=39724 stdout]  █ ███ █ ██ █▄▀█▄█▄  █ ████ █▀ █ ███ █ 
[I 2025-10-10 09:46:45:112 tid=39724 stdout]  █▄▄▄▄▄█ █ █ █ ▄ ▄ █▀▄▀▄ █▀▄ █ █▄▄▄▄▄█ 
[I 2025-10-10 09:46:45:113 tid=39724 stdout]  ▄   ▄ ▄▄█▄▀█▄▄▄███▄▄▀█▄ ▀ ▄▀█▄▄▄▄▄  ▄ 
[I 2025-10-10 09:46:45:113 tid=39724 stdout]   ▄██▄█▄▄ ▄█▀█▄ ▄ ▄  █▄▄█▀▀ █▄▀ █▀█▄▀  
[I 2025-10-10 09:46:45:113 tid=39724 stdout]  ▀  ▄▀▀▄▀ ██  ▀▄▀▀█▀█▄█▀█▄ █ █▄▄▄  █▄▄ 
[I 2025-10-10 09:46:45:114 tid=39724 stdout]  █ ▄  ▀▄    ▀ █▄█▀▄▀ ▄ ▀█▄▀▄█▄▀ ▄▀▄▄█  
[I 2025-10-10 09:46:45:114 tid=39724 stdout]    ▀ ▄ ▄ █ ██▀  ▀ █ ▄ █▀▀▀ █▄ ▀▄█▀ ██▄ 
[I 2025-10-10 09:46:45:114 tid=39724 stdout]  █     ▄▀▀ █ ▀ ▄ █ █ ▀███▀█ ██▀ ▄█     
[I 2025-10-10 09:46:45:114 tid=39724 stdout]  ▄█▀ ▀▀▄▄█▀▀▄▀ █▄▄█▄▄▄█ ▀█ ▄  █▄▄ ██ █ 
[I 2025-10-10 09:46:45:114 tid=39724 stdout]  █  ▀█ ▄   ▄▄▄  █     ▄▀█ ▀▄█▄▄ █▀▀▀   
[I 2025-10-10 09:46:45:114 tid=39724 stdout]  ▀█▀▄▄█▄   █▀▄▀▄███▀█ █ ▀  ▀▀██▄▄  ██▄ 
[I 2025-10-10 09:46:45:115 tid=39724 stdout]  ▀▀▀ ██▄▀ ▄▄ ▄█ ▄  ▀ ▀███▀█▀█ ▄▄ ▀▄▄▀  
[I 2025-10-10 09:46:45:115 tid=39724 stdout]  ▄▄▄▄▄ ▄▄▀▀▄▄█▀▄▀██▄▄▀█▀ ▀  ▀██▄▄▄██▀▄ 
[I 2025-10-10 09:46:45:115 tid=39724 stdout]  ▄▄▄▄▄▄▄ █ ▀▄▄▄██▄   █ █████▀█ ▄ ███   
[I 2025-10-10 09:46:45:115 tid=39724 stdout]  █ ▄▄▄ █ ▄   ▄▄   ▀▄ ▄█▄    ▀█▄▄▄█ █▄▄ 
[I 2025-10-10 09:46:45:115 tid=39724 stdout]  █ ███ █  ▄█ ▀▄█ █ █ ▄▄ █▀▀█▀ ▄██ ▀ ▀▀ 
[I 2025-10-10 09:46:45:116 tid=39724 stdout]  █▄▄▄▄▄█ ▄▄ █▄▀▀▄▄█▄▄ █▀ █ ▀█ █ █ ███▄ 
[I 2025-10-10 09:46:45:116 tid=39724 stdout]                                        
[I 2025-10-10 09:46:45:116 tid=39724 cli] Scan the QR code to transfer the invoice to online machine (cli.py:532)
[I 2025-10-10 09:46:45:116 tid=39724 cli] IMPORTANT: Please save the note text below and keep it private (cli.py:533)
[I 2025-10-10 09:46:45:116 tid=39724 cli] Note     : sepolia-eth-0.1-e7d384e9ee682ea4c209893b0d618094bedfb7b580400686fc6ef350514667-bb5654636d95ffb21235a79cb504a847f4c0eba695346491fa105761e7a0f8 (cli.py:534)
[I 2025-10-10 09:46:45:116 tid=39724 cli] Invoice  : sepolia-eth-0.1-122ec0ef7098492ae61f26695edd4c070ca40ca6b1455ff64843f53ad03780cb (cli.py:535)
[I 2025-10-10 09:46:45:116 tid=39724 cli] IMPORTANT: Note backup saved to /home/nova/tornadocash-py/backup/2025-10-10_09.46.45.105_sepolia_eth_0.1.txt (cli.py:536)
```


On the online machine, use the `--deposit_invoice` command to make the deposit.  
```bash
# python cli.py --deposit_invoice <key> <invoice>
# <key>    : Private key to pay the gas fee, hex string, '0x' prefix is optional
# <invoice>: Tornado note invoice text generated by '--create_note' or '--note_detail'
             
> python cli.py --deposit_invoice 0x0f36dead4beafdead4beafdead4beafdead4beafdead4beafdead4beafde9a66 sepolia-eth-0.1-122ec0ef7098492ae61f26695edd4c070ca40ca6b1455ff64843f53ad03780cb
[I 2025-10-10 09:48:57:807 tid=35492 cli] Depositing Sepolia 0.1 eth (cli.py:357)
[I 2025-10-10 09:49:03:674 tid=35492 Tornado] deposit(from=0xA09CBdDb54c7bD239F80b252d25002001580BafF) succeed, tx hash: b16ed68f119b80e8e8a3a3df65bf590917fa4262518b5ed2ff680c8511490bca (core.py:271)
```


### Withdraw

The private key is used to pay for gas fees, make sure it has enough ETH.
```bash
# python cli.py --withdraw <note> <recipient> <key/relayer_url>
# <note>           : Tornado note text
# <recipient>      : Recipient address
# <key/relayer_url>: Relayer URL, or a private key to pay the gas fee in hex string, '0x' prefix is optional
     
> python cli.py --withdraw \
    sepolia-eth-0.1-e7d384e9ee682ea4c209893b0d618094bedfb7b580400686fc6ef350514667-bb5654636d95ffb21235a79cb504a847f4c0eba695346491fa105761e7a0f8 \
    0xA09CBdDb54c7bD239F80b252d25002001580BafF \
    0x0f36dead4beafdead4beafdead4beafdead4beafdead4beafdead4beafde9a66
```

With a relayer service, the private key is not required, but the relayer will charge a fee from the withdrawn amount.
```bash
> python cli.py --withdraw \
    sepolia-eth-0.1-e7d384e9ee682ea4c209893b0d618094bedfb7b580400686fc6ef350514667-bb5654636d95ffb21235a79cb504a847f4c0eba695346491fa105761e7a0f8 \
    0xA09CBdDb54c7bD239F80b252d25002001580BafF \
    https://eth.t-relayer.com
```

Rebuilding the merkle tree may take a while depending on your CPU performance, please be patient.  
The withdrawal takes about 30 seconds with the prefetched database cache, the larger the database size, the longer it takes.  

If succeeded, you will see logs like below.  
```log
[I 2025-10-10 09:54:27:646 tid=44584 Tornado] Rebuilding merkle tree from database, please wait... (core.py:76)
[I 2025-10-10 09:54:27:873 tid=44584 MerkleTree.Memory] Level 0 rebuilt, size: 730 (merkle_tree.py:128)
[I 2025-10-10 09:54:27:982 tid=44584 MerkleTree.Memory] Level 1 rebuilt, size: 365 (merkle_tree.py:128)
[I 2025-10-10 09:54:28:036 tid=44584 MerkleTree.Memory] Level 2 rebuilt, size: 183 (merkle_tree.py:128)
[I 2025-10-10 09:54:28:063 tid=44584 MerkleTree.Memory] Level 3 rebuilt, size: 92 (merkle_tree.py:128)
[I 2025-10-10 09:54:28:076 tid=44584 MerkleTree.Memory] Level 4 rebuilt, size: 46 (merkle_tree.py:128)
[I 2025-10-10 09:54:28:084 tid=44584 MerkleTree.Memory] Level 5 rebuilt, size: 23 (merkle_tree.py:128)
[I 2025-10-10 09:54:28:088 tid=44584 MerkleTree.Memory] Level 6 rebuilt, size: 12 (merkle_tree.py:128)
[I 2025-10-10 09:54:28:089 tid=44584 MerkleTree.Memory] Level 7 rebuilt, size: 6 (merkle_tree.py:128)
[I 2025-10-10 09:54:28:091 tid=44584 MerkleTree.Memory] Level 8 rebuilt, size: 3 (merkle_tree.py:128)
[I 2025-10-10 09:54:28:091 tid=44584 MerkleTree.Memory] Level 9 rebuilt, size: 2 (merkle_tree.py:128)
[I 2025-10-10 09:54:28:092 tid=44584 MerkleTree.Memory] Level 10 rebuilt, size: 1 (merkle_tree.py:128)
[I 2025-10-10 09:54:28:093 tid=44584 MerkleTree.Memory] Level 11 rebuilt, size: 1 (merkle_tree.py:128)
[I 2025-10-10 09:54:28:094 tid=44584 MerkleTree.Memory] Level 12 rebuilt, size: 1 (merkle_tree.py:128)
[I 2025-10-10 09:54:28:094 tid=44584 MerkleTree.Memory] Level 13 rebuilt, size: 1 (merkle_tree.py:128)
[I 2025-10-10 09:54:28:095 tid=44584 MerkleTree.Memory] Level 14 rebuilt, size: 1 (merkle_tree.py:128)
[I 2025-10-10 09:54:28:096 tid=44584 MerkleTree.Memory] Level 15 rebuilt, size: 1 (merkle_tree.py:128)
[I 2025-10-10 09:54:28:096 tid=44584 MerkleTree.Memory] Level 16 rebuilt, size: 1 (merkle_tree.py:128)
[I 2025-10-10 09:54:28:097 tid=44584 MerkleTree.Memory] Level 17 rebuilt, size: 1 (merkle_tree.py:128)
[I 2025-10-10 09:54:28:097 tid=44584 MerkleTree.Memory] Level 18 rebuilt, size: 1 (merkle_tree.py:128)
[I 2025-10-10 09:54:28:098 tid=44584 MerkleTree.Memory] Level 19 rebuilt, size: 1 (merkle_tree.py:128)
[I 2025-10-10 09:54:28:098 tid=44584 Tornado] Merkle tree ready (core.py:83)
[I 2025-10-10 09:54:28:608 tid=30988 EventPoller] 133 blocks behind, latest block number: 9379475 (blockchain.py:238)
[I 2025-10-10 09:54:30:615 tid=30988 cli] Sepolia@0.1ETH, synced 133 blocks from 9379343 to 9379475, progress: 100.00%, deposits: 1, withdrawals: 1 (cli.py:267)
[I 2025-10-10 09:54:30:615 tid=30988 EventPoller] Synced to block 9379475 (blockchain.py:317)
[I 2025-10-10 09:54:30:615 tid=30988 cli] Sepolia@0.1ETH, catch up to the latest blockchain (cli.py:258)
[I 2025-10-10 09:54:36:408 tid=44584 Tornado] withdraw(to=0xA09CBdDb54c7bD239F80b252d25002001580BafF), proof generated for commitment: 0x122ec0ef7098492ae61f26695edd4c070ca40ca6b1455ff64843f53ad03780cb (core.py:420)
[I 2025-10-10 09:54:38:586 tid=44584 Tornado] withdraw(to=0xA09CBdDb54c7bD239F80b252d25002001580BafF) succeed, tx hash: 0x71fde15c7ff5e84886f664ab5dcf78b9d0a6b607c8d6c52ad37749ec9287bc0b (core.py:532)
```

Somtimes with a relayer, you need to increase the service fee rate in `config.py`, the default is `1.8%`

![](/assets/readme_withdraw.png)


### Batch Withdraw

Similar to batch deposit, you can withdraw multiple notes to one recipient address at once.  
```bash
# python cli.py --withdraw_batch <notes> <recipient> <key/relayer_url>
# <notes>          : Multiple tornado note text separated by comma without whitespace
# <recipient>      : Recipient address
# <key/relayer_url>: Relayer URL or private key in Hex string, '0x' prefix is optional

> python cli.py --withdraw_batch \
    sepolia-eth-0.1-6eb32c15b678855085e7ff524b0ecaf89412b92b66c7f5d8d3b5c3991c7e9c-b6a335ef4ee1bd88460a3fc68b67a30908061a3b8b66160ab39e9aec50d54a,sepolia-eth-0.1-0cb9fc8d22b005fe142abcc225d9826adc789b88c379b7668f712cd7e79b95-71903a81f3926a050f8a88b983769083d6f81c7f9ad8d0ef32abbc66ae629c,sepolia-eth-0.1-50cb4336664d12ebdfb3b83887366435008efb8e7ddd4a24cab1e6296a65e7-a8563b6f1074a19e20fe4a8a43d674835606db89265b69366aeaf7efc516f6
    0xA09CBdDb54c7bD239F80b252d25002001580BafF \
    0x0f36b1371ac961e318c284985c184fbac8b4c91ed1765343d4088f04252f9a66
```


### Query Deposit Age

You can check how many deposits and withdrawals have been made since your deposit, which indicates the anonymity level (mixing depth) of your note.  
The bigger the number, the more anonymity you get.
```bash
# python cli.py --note_age <note/invoice>
# <note/invoice>: The private note, or the invoice of the note

> python cli.py --note_age sepolia-eth-0.1-122ec0ef7098492ae61f26695edd4c070ca40ca6b1455ff64843f53ad03780cb
[I 2025-10-31 00:27:12:515 tid=676076 cli] Since commitment 0x122ec0ef7098492ae61f26695edd4c070ca40ca6b1455ff64843f53ad03780cb (cli.py:732)
[I 2025-10-31 00:27:12:515 tid=676076 cli] Deposit: 54, Withdraw: 31 (cli.py:733)
```


## Known Relayers  

Last updated: March 10, 2026

| ENS                   | Chain     | URL                                         | Reward Address                                                                                                                     |
|-----------------------|-----------|---------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| 0xgm777.eth           | Ethereum  | https://gm777.xyz                           | [0x94596B6A626392F5D972D6CC4D929a42c2f0008c](https://etherscan.io/address/0x94596B6A626392F5D972D6CC4D929a42c2f0008c)              |
| 0xgm777.eth           | BSC       | https://bsc.gm777.xyz                       | [0x03392600086874456E08D2bAc104380BCdEBCfC0](https://bscscan.com/address/0x03392600086874456E08D2bAc104380BCdEBCfC0)               |
| 0xgm777.eth           | Arbitrum  | https://arb.gm777.xyz                       | [0x03392600086874456E08D2bAc104380BCdEBCfC0](https://arbiscan.io/address/0x03392600086874456E08D2bAc104380BCdEBCfC0)               |
| 0xgn777.eth           | Ethereum  | https://gn777.xyz                           | [0x0381DeeE9BBCD701D022b47c81F5b0079F48d38C](https://etherscan.io/address/0x0381DeeE9BBCD701D022b47c81F5b0079F48d38C)              |
| 0xgn777.eth           | BSC       | https://bsc.gn777.xyz                       | [0xD0b9b6674B77beFD88884D2BDeea979c023938E8](https://bscscan.com/address/0xD0b9b6674B77beFD88884D2BDeea979c023938E8)               |
| 0xgn777.eth           | Arbitrum  | https://arb.gn777.xyz                       | [0xD0b9b6674B77beFD88884D2BDeea979c023938E8](https://arbiscan.io/address/0xD0b9b6674B77beFD88884D2BDeea979c023938E8)               |
| bitah.eth             | Ethereum  | https://tornado.bitah.link                  | [0x7E7461889B1cdd10f6929B4a3feA611Df8b45B04](https://etherscan.io/address/0x7E7461889B1cdd10f6929B4a3feA611Df8b45B04)              |
| bitah.eth             | BSC       | https://bsc-tornado.bitah.link              | [0x7E7461889B1cdd10f6929B4a3feA611Df8b45B04](https://bscscan.com/address/0x7E7461889B1cdd10f6929B4a3feA611Df8b45B04)               |
| bitah.eth             | Polygon   | https://polygon-tornado.bitah.link          | [0x7E7461889B1cdd10f6929B4a3feA611Df8b45B04](https://polygonscan.com/address/0x7E7461889B1cdd10f6929B4a3feA611Df8b45B04)           |
| cheap-relayer.eth     | Ethereum  | https://mainnet-tornado.cheap-relayer.xyz   | [0x076D4E32C6A5D888fC4658281539c94E778C796d](https://etherscan.io/address/0x076D4E32C6A5D888fC4658281539c94E778C796d)              |
| cheap-relayer.eth     | BSC       | https://bsc-tornado.cheap-relayer.xyz       | [0x076D4E32C6A5D888fC4658281539c94E778C796d](https://bscscan.com/address/0x076D4E32C6A5D888fC4658281539c94E778C796d)               |
| cheap-relayer.eth     | Polygon   | https://polygon-tornado.cheap-relayer.xyz   | [0x076D4E32C6A5D888fC4658281539c94E778C796d](https://polygonscan.com/address/0x076D4E32C6A5D888fC4658281539c94E778C796d)           |
| cheap-relayer.eth     | Avalanche | https://avalanche-tornado.cheap-relayer.xyz | [0x076D4E32C6A5D888fC4658281539c94E778C796d](https://avascan.info/blockchain/c/address/0x076D4E32C6A5D888fC4658281539c94E778C796d) |
| default-relayer.eth   | Ethereum  | https://eth.default-relayer.com             | [0x5555555731006f71f121144534Ca7C8799F66AA3](https://etherscan.io/address/0x5555555731006f71f121144534Ca7C8799F66AA3)              |
| default-relayer.eth   | BSC       | https://bsc.default-relayer.com             | [0x5555555731006f71f121144534Ca7C8799F66AA3](https://bscscan.com/address/0x5555555731006f71f121144534Ca7C8799F66AA3)               |
| hello-relayer.eth     | Ethereum  | https://hirelay04.xyz                       | [0x213Cfeb89529efC2eAE2a502D4a8253Fe4Ae76eF](https://etherscan.io/address/0x213Cfeb89529efC2eAE2a502D4a8253Fe4Ae76eF)              |
| hello-relayer.eth     | BSC       | https://binance.hirelay04.xyz               | [0x213Cfeb89529efC2eAE2a502D4a8253Fe4Ae76eF](https://bscscan.com/address/0x213Cfeb89529efC2eAE2a502D4a8253Fe4Ae76eF)               |
| hello-relayer.eth     | Arbitrum  | https://arb.hirelay04.xyz                   | SERVICE DOWN                                                                                                                       |
| hello-relayer.eth     | Optimism  | https://op.hirelay04.xyz                    | SERVICE DOWN                                                                                                                       |
| hello-relayer.eth     | Polygon   | https://polygon.hirelay04.xyz               | [0x213Cfeb89529efC2eAE2a502D4a8253Fe4Ae76eF](https://polygonscan.com/address/0x213Cfeb89529efC2eAE2a502D4a8253Fe4Ae76eF)           |
| hello-relayer.eth     | Avalanche | https://avax.hirelay04.xyz                  | [0x213Cfeb89529efC2eAE2a502D4a8253Fe4Ae76eF](https://avascan.info/blockchain/c/address/0x213Cfeb89529efC2eAE2a502D4a8253Fe4Ae76eF) |
| hurricane-relayer.eth | Ethereum  | https://eth.hurricane42.xyz                 | [0x16CB924b5b7ef604139bE95F8762ed817852Db92](https://etherscan.io/address/0x16CB924b5b7ef604139bE95F8762ed817852Db92)              |
| hurricane-relayer.eth | BSC       | https://bsc.hurricane42.xyz                 | [0x16CB924b5b7ef604139bE95F8762ed817852Db92](https://bscscan.com/address/0x16CB924b5b7ef604139bE95F8762ed817852Db92)               |
| hurricane-relayer.eth | Polygon   | https://polygon.hurricane42.xyz             | [0x16CB924b5b7ef604139bE95F8762ed817852Db92](https://polygonscan.com/address/0x16CB924b5b7ef604139bE95F8762ed817852Db92)           |
| k-relayer.eth         | Ethereum  | https://black-hardy.com                     | [0xC49415493eB3Ec64a0F13D8AA5056f1CfC4ce35c](https://etherscan.io/address/0xC49415493eB3Ec64a0F13D8AA5056f1CfC4ce35c)              |
| k-relayer.eth         | BSC       | https://bsc.black-hardy.com                 | SERVICE DOWN                                                                                                                       |
| reltor.eth            | Ethereum  | https://eth.reltor.su                       | [0x4750BCfcC340AA4B31be7e71fa072716d28c29C5](https://etherscan.io/address/0x4750BCfcC340AA4B31be7e71fa072716d28c29C5)              |
| reltor.eth            | BSC       | https://binance.reltor.su                   | [0x4750BCfcC340AA4B31be7e71fa072716d28c29C5](https://bscscan.com/address/0x4750BCfcC340AA4B31be7e71fa072716d28c29C5)               |
| reltor.eth            | Polygon   | https://polygon.reltor.su                   | [0x4750BCfcC340AA4B31be7e71fa072716d28c29C5](https://polygonscan.com/address/0x4750BCfcC340AA4B31be7e71fa072716d28c29C5)           |
| safe-relayer.eth      | Ethereum  | https://safe-relayer.online                 | [0xC7c3C87603c55955100DceCA02443fBff1B15361](https://etherscan.io/address/0xC7c3C87603c55955100DceCA02443fBff1B15361)              |
| safe-relayer.eth      | BSC       | https://bsc.safe-relayer.online             | [0xC7c3C87603c55955100DceCA02443fBff1B15361](https://bscscan.com/address/0xC7c3C87603c55955100DceCA02443fBff1B15361)               |
| safe-torn.eth         | Ethereum  | https://eth3.safetorn.ovh                   | [0x0A5B2bF3cCfB44C1D22F07Eed9553eCba752D4aD](https://etherscan.io/address/0x0A5B2bF3cCfB44C1D22F07Eed9553eCba752D4aD)              |
| safe-torn.eth         | BSC       | https://bsc3.safetorn.ovh                   | [0x0A5B2bF3cCfB44C1D22F07Eed9553eCba752D4aD](https://bscscan.com/address/0x0A5B2bF3cCfB44C1D22F07Eed9553eCba752D4aD)               |
| safe-torn.eth         | Polygon   | https://poly3.safetorn.ovh                  | [0x0A5B2bF3cCfB44C1D22F07Eed9553eCba752D4aD](https://polygonscan.com/address/0x0A5B2bF3cCfB44C1D22F07Eed9553eCba752D4aD)           |
| sky-relayer.eth       | Ethereum  | https://sky-relayer.xyz                     | [0xEE4C45Cc5eAa535CB8a8ffdc92f2839A601fe226](https://etherscan.io/address/0xEE4C45Cc5eAa535CB8a8ffdc92f2839A601fe226)              |
| sky-relayer.eth       | BSC       | https://bsc.sky-relayer.xyz                 | [0xEE4C45Cc5eAa535CB8a8ffdc92f2839A601fe226](https://bscscan.com/address/0xEE4C45Cc5eAa535CB8a8ffdc92f2839A601fe226)               |
| torn-city.eth         | Ethereum  | http://torncity.fun                         | [0xd04e9f0945DEA8373D882C730e2c93a74B591796](https://etherscan.io/address/0xd04e9f0945DEA8373D882C730e2c93a74B591796)              |
| torn-city.eth         | BSC       | https://bsc.torncity.fun                    | [0xd04e9f0945DEA8373D882C730e2c93a74B591796](https://bscscan.com/address/0xd04e9f0945DEA8373D882C730e2c93a74B591796)               |
| t-relayer.eth         | Ethereum  | https://eth.t-relayer.com                   | [0x000000Cd6521Ed1a65FAe0678eA15aF4EEAD74fe](https://etherscan.io/address/0x000000Cd6521Ed1a65FAe0678eA15aF4EEAD74fe)              |
| t-relayer.eth         | BSC       | https://bsc.t-relayer.com                   | [0x000000Cd6521Ed1a65FAe0678eA15aF4EEAD74fe](https://bscscan.com/address/0x000000Cd6521Ed1a65FAe0678eA15aF4EEAD74fe)               |


## Supported Deployments

Last updated: August 17, 2025

| Chain     | Symbol | Unit    | Tornado Contract Address                                                                                                           |
|-----------|--------|---------|------------------------------------------------------------------------------------------------------------------------------------|
| Ethereum  | ETH    | 0.1     | [0x12D66f87A04A9E220743712cE6d9bB1B5616B8Fc](https://etherscan.io/address/0x12D66f87A04A9E220743712cE6d9bB1B5616B8Fc)              |
| Ethereum  | ETH    | 1       | [0x47CE0C6eD5B0Ce3d3A51fdb1C52DC66a7c3c2936](https://etherscan.io/address/0x47CE0C6eD5B0Ce3d3A51fdb1C52DC66a7c3c2936)              |
| Ethereum  | ETH    | 10      | [0x910Cbd523D972eb0a6f4cAe4618aD62622b39DbF](https://etherscan.io/address/0x910Cbd523D972eb0a6f4cAe4618aD62622b39DbF)              |
| Ethereum  | ETH    | 100     | [0xA160cdAB225685dA1d56aa342Ad8841c3b53f291](https://etherscan.io/address/0xA160cdAB225685dA1d56aa342Ad8841c3b53f291)              |
| Ethereum  | DAI    | 100     | [0xD4B88Df4D29F5CedD6857912842cff3b20C8Cfa3](https://etherscan.io/address/0xD4B88Df4D29F5CedD6857912842cff3b20C8Cfa3)              |
| Ethereum  | DAI    | 1000    | [0xFD8610d20aA15b7B2E3Be39B396a1bC3516c7144](https://etherscan.io/address/0xFD8610d20aA15b7B2E3Be39B396a1bC3516c7144)              |
| Ethereum  | DAI    | 10000   | [0x07687e702b410Fa43f4cB4Af7FA097918ffD2730](https://etherscan.io/address/0x07687e702b410Fa43f4cB4Af7FA097918ffD2730)              |
| Ethereum  | DAI    | 100000  | [0x23773E65ed146A459791799d01336DB287f25334](https://etherscan.io/address/0x23773E65ed146A459791799d01336DB287f25334)              |
| Ethereum  | cDAI   | 5000    | [0x22aaA7720ddd5388A3c0A3333430953C68f1849b](https://etherscan.io/address/0x22aaA7720ddd5388A3c0A3333430953C68f1849b)              |
| Ethereum  | cDAI   | 50000   | [0x03893a7c7463AE47D46bc7f091665f1893656003](https://etherscan.io/address/0x03893a7c7463AE47D46bc7f091665f1893656003)              |
| Ethereum  | cDAI   | 500000  | [0x2717c5e28cf931547B621a5dddb772Ab6A35B701](https://etherscan.io/address/0x2717c5e28cf931547B621a5dddb772Ab6A35B701)              |
| Ethereum  | cDAI   | 5000000 | [0xD21be7248e0197Ee08E0c20D4a96DEBdaC3D20Af](https://etherscan.io/address/0xD21be7248e0197Ee08E0c20D4a96DEBdaC3D20Af)              |
| Ethereum  | USDC   | 100     | [0xd96f2B1c14Db8458374d9Aca76E26c3D18364307](https://etherscan.io/address/0xd96f2B1c14Db8458374d9Aca76E26c3D18364307)              |
| Ethereum  | USDC   | 1000    | [0x4736dCf1b7A3d580672CcE6E7c65cd5cc9cFBa9D](https://etherscan.io/address/0x4736dCf1b7A3d580672CcE6E7c65cd5cc9cFBa9D)              |
| Ethereum  | USDT   | 100     | [0x169AD27A470D064DEDE56a2D3ff727986b15D52B](https://etherscan.io/address/0x169AD27A470D064DEDE56a2D3ff727986b15D52B)              |
| Ethereum  | USDT   | 1000    | [0x0836222F2B2B24A3F36f98668Ed8F0B38D1a872f](https://etherscan.io/address/0x0836222F2B2B24A3F36f98668Ed8F0B38D1a872f)              |
| Ethereum  | WBTC   | 0.1     | [0x178169B423a011fff22B9e3F3abeA13414dDD0F1](https://etherscan.io/address/0x178169B423a011fff22B9e3F3abeA13414dDD0F1)              |
| Ethereum  | WBTC   | 1       | [0x610B717796ad172B316836AC95a2ffad065CeaB4](https://etherscan.io/address/0x610B717796ad172B316836AC95a2ffad065CeaB4)              |
| Ethereum  | WBTC   | 10      | [0xbB93e510BbCD0B7beb5A853875f9eC60275CF498](https://etherscan.io/address/0xbB93e510BbCD0B7beb5A853875f9eC60275CF498)              |
| Optimism  | ETH    | 0.1     | [0x84443CFd09A48AF6eF360C6976C5392aC5023a1F](https://optimistic.etherscan.io/address/0x84443CFd09A48AF6eF360C6976C5392aC5023a1F)   |
| Optimism  | ETH    | 1       | [0xd47438C816c9E7f2E2888E060936a499Af9582b3](https://optimistic.etherscan.io/address/0xd47438C816c9E7f2E2888E060936a499Af9582b3)   |
| Optimism  | ETH    | 10      | [0x330bdFADE01eE9bF63C209Ee33102DD334618e0a](https://optimistic.etherscan.io/address/0x330bdFADE01eE9bF63C209Ee33102DD334618e0a)   |
| Optimism  | ETH    | 100     | [0x1E34A77868E19A6647b1f2F47B51ed72dEDE95DD](https://optimistic.etherscan.io/address/0x1E34A77868E19A6647b1f2F47B51ed72dEDE95DD)   |
| BSC       | BNB    | 0.1     | [0x84443CFd09A48AF6eF360C6976C5392aC5023a1F](https://bscscan.com/address/0x84443CFd09A48AF6eF360C6976C5392aC5023a1F)               |
| BSC       | BNB    | 1       | [0xd47438C816c9E7f2E2888E060936a499Af9582b3](https://bscscan.com/address/0xd47438C816c9E7f2E2888E060936a499Af9582b3)               |
| BSC       | BNB    | 10      | [0x330bdFADE01eE9bF63C209Ee33102DD334618e0a](https://bscscan.com/address/0x330bdFADE01eE9bF63C209Ee33102DD334618e0a)               |
| BSC       | BNB    | 100     | [0x1E34A77868E19A6647b1f2F47B51ed72dEDE95DD](https://bscscan.com/address/0x1E34A77868E19A6647b1f2F47B51ed72dEDE95DD)               |
| Polygon   | POL    | 100     | [0x1E34A77868E19A6647b1f2F47B51ed72dEDE95DD](https://polygonscan.com/address/0x1E34A77868E19A6647b1f2F47B51ed72dEDE95DD)           |
| Polygon   | POL    | 1000    | [0xdf231d99Ff8b6c6CBF4E9B9a945CBAcEF9339178](https://polygonscan.com/address/0xdf231d99Ff8b6c6CBF4E9B9a945CBAcEF9339178)           |
| Polygon   | POL    | 10000   | [0xaf4c0B70B2Ea9FB7487C7CbB37aDa259579fe040](https://polygonscan.com/address/0xaf4c0B70B2Ea9FB7487C7CbB37aDa259579fe040)           |
| Polygon   | POL    | 100000  | [0xa5C2254e4253490C54cef0a4347fddb8f75A4998](https://polygonscan.com/address/0xa5C2254e4253490C54cef0a4347fddb8f75A4998)           |
| Arbitrum  | ETH    | 0.1     | [0x84443CFd09A48AF6eF360C6976C5392aC5023a1F](https://arbiscan.io/address/0x84443CFd09A48AF6eF360C6976C5392aC5023a1F)               |
| Arbitrum  | ETH    | 1       | [0xd47438C816c9E7f2E2888E060936a499Af9582b3](https://arbiscan.io/address/0xd47438C816c9E7f2E2888E060936a499Af9582b3)               |
| Arbitrum  | ETH    | 10      | [0x330bdFADE01eE9bF63C209Ee33102DD334618e0a](https://arbiscan.io/address/0x330bdFADE01eE9bF63C209Ee33102DD334618e0a)               |
| Arbitrum  | ETH    | 100     | [0x1E34A77868E19A6647b1f2F47B51ed72dEDE95DD](https://arbiscan.io/address/0x1E34A77868E19A6647b1f2F47B51ed72dEDE95DD)               |
| Avalanche | AVAX   | 10      | [0x330bdFADE01eE9bF63C209Ee33102DD334618e0a](https://avascan.info/blockchain/c/address/0x330bdFADE01eE9bF63C209Ee33102DD334618e0a) |
| Avalanche | AVAX   | 100     | [0x1E34A77868E19A6647b1f2F47B51ed72dEDE95DD](https://avascan.info/blockchain/c/address/0x1E34A77868E19A6647b1f2F47B51ed72dEDE95DD) |
| Avalanche | AVAX   | 500     | [0xaf8d1839c3c67cf571aa74B5c12398d4901147B3](https://avascan.info/blockchain/c/address/0xaf8d1839c3c67cf571aa74B5c12398d4901147B3) |
| Sepolia   | ETH    | 0.1     | [0x8C4A04d872a6C1BE37964A21ba3a138525dFF50b](https://sepolia.etherscan.io/address/0x8C4A04d872a6C1BE37964A21ba3a138525dFF50b)      |
| Sepolia   | ETH    | 1       | [0x8cc930096B4Df705A007c4A039BDFA1320Ed2508](https://sepolia.etherscan.io/address/0x8cc930096B4Df705A007c4A039BDFA1320Ed2508)      |
| Sepolia   | ETH    | 10      | [0x8D10d506D29Fc62ABb8A290B99F66dB27Fc43585](https://sepolia.etherscan.io/address/0x8D10d506D29Fc62ABb8A290B99F66dB27Fc43585)      |


## Buy me a coffee

If you like this project 😉☕  

EVM Address: 0x5Fe21cB7B590E284F39b715E12a9Ac328b3D3914  

![](/assets/0x5Fe21cB7B590E284F39b715E12a9Ac328b3D3914.png)
