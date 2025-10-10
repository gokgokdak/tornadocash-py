*__Security Warnings__:*    
*1. Only run the open source code and scripts locally or binaries compiled on your machine*  
*2. Do not trust or use __ANY__ Tornado Cash service from the webpage or IPFS*  
*3. There’s no longer any such thing as an "official website" after the sanctions*  
*4. Any websites that claim themselves as "official" are 100% __FAKE__*  
*5. See 👉 [[Block Domain] Fake ethereum Tornado cash websites Phishing](https://github.com/MetaMask/eth-phishing-detect/issues/13826)*


# TornadoCash-py

A Python implementation to interact with Tornado Cash smart contracts.  

Similar to the original [tornado-cli](https://github.com/tornadocash/tornado-cli), but more features and better experience


## Preparations

### Startup

- Required minimum Python version `3.10+`, recommend `3.13`
- Clone the repository and install required Python packages by running the following command in the terminal:  
    ```bash
    git clone https://github.com/gokgokdak/tornadocash-py.git
    cd tornadocash-py
    pip install -r requirements.txt
    ```
- Then download the database cache for the first startup
    ```bash
    cd ./db
    git clone https://github.com/gokgokdak/tornadocash-db.git
    ```

### RPC Service (Optional)

For blockchain interaction, `publicnode.com` was used as the default RPC provider, technically it should be enough for most users.  

For better experience or if you want to set up your own RPC provider, replace the `RPC_URLS` variable in `config.py` with your own endpoint.  

![](/assets/readme_rpc.png)


### Node.js Runtime (Optional)

Node.js runtime is required, version 14 or above is recommended.  

By default, it uses Node.js binary runtime bundled in the `./zk/bin` directory, to use your local  Node.js, please set the `BUNDLED_NODE_JS` variable to `False` in `config.py`, and make sure the `node` command is available in your system PATH.

![](/assets/readme_nodejs.png)

See 👉 [Node.js official website](https://nodejs.org/en/download) for installation if you don't want to use the bundled binary.  


## Usage & Tutorial

### Sync Blockchain

According to the Tornado Cash protocol, to initiate a withdrawal, the user is required to rebuild the merkle tree with the contract's **ALL** historical commitments to calculate the latest tree root, which means we have to save a copy of all contract events locally.  

Download the prefetched database cache to accelerate the process, put all `.sqlite` files under the `./db` directory.  
Blockchain database cache 👉 [https://github.com/gokgokdak/tornadocash-db](https://github.com/gokgokdak/tornadocash-db)

Or, you could sync the blockchain data from scratch, which may take a long time depending on your network quality, to do this, please run:  
`python cli.py --sync <chain> <symbol> <unit>`  

To sync all deployments:  
`python cli.py --sync_all`    

It is recommended to keep the program running to stay synchronized with the blockchain, simply add a `--keep` option to `--sync` or `--sync_all` command.  


### Deposit

The private key is used to provide ETH and pay for gas fees, make sure it has enough balance.
```bash
# python cli.py --deposit <key> <chain> <symbol> <unit>
python cli.py --deposit 0x0f36dead4beafdead4beafdead4beafdead4beafdead4beafdead4beafde9a66 sepolia eth 0.1
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
python cli.py --deposit_batch 0x0f36dead4beafdead4beafdead4beafdead4beafdead4beafdead4beafde9a66 "{'ethereum':{'eth':{'10':100,'100':20}},'polygon':{'pol':{'100000':1000}}}"
```


### Offline Deposit

Create a note on the offline machine, scan the QR code or copy the invoice text to the online machine  
```bash
# python cli.py --create_note <chain> <symbol> <unit>
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
> python cli.py --deposit_invoice 0x0f36dead4beafdead4beafdead4beafdead4beafdead4beafdead4beafde9a66 sepolia-eth-0.1-122ec0ef7098492ae61f26695edd4c070ca40ca6b1455ff64843f53ad03780cb
[I 2025-10-10 09:48:57:807 tid=35492 cli] Depositing Sepolia 0.1 eth (cli.py:357)
[I 2025-10-10 09:49:03:674 tid=35492 Tornado] deposit(from=0xA09CBdDb54c7bD239F80b252d25002001580BafF) succeed, tx hash: b16ed68f119b80e8e8a3a3df65bf590917fa4262518b5ed2ff680c8511490bca (core.py:271)
```


### Withdraw

The private key is used to pay for gas fees, make sure it has enough ETH.
```bash
# python cli.py --withdraw <note> <recipient> <key/relayer_url>
python cli.py --withdraw \
    sepolia-eth-0.1-e7d384e9ee682ea4c209893b0d618094bedfb7b580400686fc6ef350514667-bb5654636d95ffb21235a79cb504a847f4c0eba695346491fa105761e7a0f8 \
    0xA09CBdDb54c7bD239F80b252d25002001580BafF \
    0x0f36dead4beafdead4beafdead4beafdead4beafdead4beafdead4beafde9a66
```

With a relayer service, the private key is not required, but the relayer will charge a fee from the withdrawn amount.
```bash
# python cli.py --withdraw <note> <recipient> <key/relayer_url>
python cli.py --withdraw \
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


## Running Tests

It is **HIGHLY** recommended to run all unit tests before using this program, to make sure the mathematics and cryptographic calculations are correct on your machine.
- Navigate to the project root directory and run the unit tests using Python's unittest framework:
    ```bash
    python -m unittest discover -s test -p "test_*.py"
    ```


## Known Relayers  

Last updated: August 17, 2025  

Sourced from 👉 https://relayer.tornadoeth.cash

| URL                                       | ENS                 | Chain    | Address                                                                                                               |
|-------------------------------------------|---------------------|----------|-----------------------------------------------------------------------------------------------------------------------|
| https://safe-relayer.online               | safe-relayer.eth    | Ethereum | [0xC7c3C87603c55955100DceCA02443fBff1B15361](https://etherscan.io/address/0xC7c3C87603c55955100DceCA02443fBff1B15361) |
| https://mainnet-tornado.cheap-relayer.xyz | cheap-relayer.eth   | Ethereum | [0x076D4E32C6A5D888fC4658281539c94E778C796d](https://etherscan.io/address/0x076D4E32C6A5D888fC4658281539c94E778C796d) |
| https://eth.t-relayer.com                 | t-relayer.eth       | Ethereum | [0x000000Cd6521Ed1a65FAe0678eA15aF4EEAD74fe](https://etherscan.io/address/0x000000Cd6521Ed1a65FAe0678eA15aF4EEAD74fe) |
| https://main-relayer.com                  | main-relayer.eth    | Ethereum | [0x15980A3Bd6ed317f42d2eD0DCf3d3D730b6Bc0C5](https://etherscan.io/address/0x15980A3Bd6ed317f42d2eD0DCf3d3D730b6Bc0C5) |
| https://relayer.wind-egg.com              | default-relayer.eth | Ethereum | [0x5555555731006f71f121144534Ca7C8799F66AA3](https://etherscan.io/address/0x5555555731006f71f121144534Ca7C8799F66AA3) |
| https://main.gm777.xyz                    | 0xgm777.eth         | Ethereum | [0x94596B6A626392F5D972D6CC4D929a42c2f0008c](https://etherscan.io/address/0x94596B6A626392F5D972D6CC4D929a42c2f0008c) |
| https://black-hardy.com                   | k-relayer.eth       | Ethereum | [0xC49415493eB3Ec64a0F13D8AA5056f1CfC4ce35c](https://etherscan.io/address/0xC49415493eB3Ec64a0F13D8AA5056f1CfC4ce35c) |
| https://tornima.xyz                       | torrelayer.eth      | Ethereum | [0x2Ee39Ff05643bC7cc9ed31B71e142429044A425C](https://etherscan.io/address/0x2Ee39Ff05643bC7cc9ed31B71e142429044A425C) |
| https://torn-city.com                     | torn-city.eth       | Ethereum | [0xd04e9f0945DEA8373D882C730e2c93a74B591796](https://etherscan.io/address/0xd04e9f0945DEA8373D882C730e2c93a74B591796) |
| https://mainnet.das-relayer.com           | das-relayer.eth     | Ethereum | [0xFfDf1Dd461e3Ce4A78685D2DC0641d95B71b9F53](https://etherscan.io/address/0xFfDf1Dd461e3Ce4A78685D2DC0641d95B71b9F53) |
| https://main.firstrelayer.xyz             | first-relayer.eth   | Ethereum | [0xD8f1Eb586Ecb93745392EE254a028f1F67E1437E](https://etherscan.io/address/0xD8f1Eb586Ecb93745392EE254a028f1F67E1437E) |
| https://main.x-relayer.top                | 0xrelayer.eth       | Ethereum | [0x0Bed01A860a56266383D648320852715FEcAc7ae](https://etherscan.io/address/0x0Bed01A860a56266383D648320852715FEcAc7ae) |
| https://eth.maxstorn.xyz                  | nice-relayer.eth    | Ethereum | [0xb0Cdc0AB2D454F2360d4629d519819E13DBE816A](https://etherscan.io/address/0xb0Cdc0AB2D454F2360d4629d519819E13DBE816A) |


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

EVM Address: 0xd54eA9e8106227080f72bfD4b9d99BbD96Eacd11  

![](/assets/0xd54eA9e8106227080f72bfD4b9d99BbD96Eacd11.png)
