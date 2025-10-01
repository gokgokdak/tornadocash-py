# Prover

A minimized version of one of the WebSnark modules

Modified from 👉 https://github.com/tornadocash/websnark#4c0af6a8b65aabea3c09f377f63c44e7a58afa6d

Return a JSON object with the following structure:
```json
{
    "pi_a": [
        "21440631675674537428348291584912552922287517075005523353334773490016201614421",
        "15127299628458688392214851412542297066930128770600784370542323372344427443426",
        "1"
    ],
    "pi_b": [
        [
            "12814946870690198605352052269347454744992359297791737200639976648401522327725",
            "2710320687308734447263781453783158523744334914051054563047794847162787191416"
        ],
        [
            "13066069913961661538730312252204715666487827715868579066216062111075683165387",
            "4889891732720659170094910333427534817802972638085306547157777773204526677068"
        ],
        [ "1", "0" ]
    ],
    "pi_c": [
        "3956517219337442990943464913477305112927219283128510609779269980796698077595",
        "3116909696587227763654937123278075851928638626025781354873016906870684705420",
        "1"
    ],
    "publicSignals": [
        "5449870870154494757698847261691583314925861354620760480266496418887110305164",
        "4270524347838964758799445581014653561892820038739984487868757645202897693415",
        "12696284824510262420843062593305747029752110428",
        "312267640386303481280932568793045309390384198046",
        "3000000000000000",
        "0"
    ],
    "solidity": {
        "proof": "0x2f66f7acdc4041c93703ee6e1addbffdd18f0e482b99c7bf5a3f2eb9e71a24552171bf88406fbf0ba3b36b99ee7acc0ace09a8f8bee10114f66280f890c074e205fdfcb5a313087768d852cc8301bd8d7ac0c7c4df46d4c8af76a41387e45a781c5500bd88f38977d1d70f1e293d43317b16e658c70caa481bbe6ba84bcd00ad0acf94a4e97ad34016c6e44ef36e80e907884c9b2c72d906ccd4853b25d53c4c1ce3222ce6db5b4f56e1e3e7b0345b60e6726d8c38c5709d92396d3edf5664cb08bf4f340d7bdef44f620cd39e3c64958774817e8aa6015b74925ccd2149a99b06e41bbe2d5c116847abf37f1f8075636a9ace21548da8e039d1791c97b0e28c",
        "publicSignals": [
            "0x0c0c84818531e5888135c5219919215265f23ff4aba41375f201615cb3e9258c",
            "0x097107f7c6d252a02f007694c5948b379860f8773e22a2bef15eab1c61eeeae7",
            "0x00000000000000000000000002395233b8175b0a04d5a0ad0f62eaf7afe55d5c",
            "0x00000000000000000000000036b290b60bf8aecd244ef53e387e7602229af19e",
            "0x000000000000000000000000000000000000000000000000000aa87bee538000",
            "0x0000000000000000000000000000000000000000000000000000000000000000"
        ]
    }
}
```

# Verifier

A minimized version of one of the SnarkJS modules

Modified from 👉 https://github.com/tornadocash/snarkjs#869181cfaf7526fe8972073d31655493a04326d5

# Demo

A simple hand made prove and verify demo to show how to use them and test the correctness of the implementation.

## Why

I was going to re-implement the witness and proof generation in pure Python or C++ with PyBind11, but it turns out to be a lot of work.

The original Tornado Cash uses a very old version of SnarkJS, where the output format of keys is in JSON format instead of `.zkey` files. Also, the compiled circuit is in JSON format instead of `.wasm` or `.r1cs` files.

There is even JavaScript code embedded in the compiled output `circuit.json`, making it impossible to upgrade to the latest SnarkJS or use other tools like `circom 2` or `rapidsnark` that expect the modern formats.

If you have any ideas to make this part fully Python or C++ with PyBind11 implemented, please feel free to open an issue or PR. ☕
