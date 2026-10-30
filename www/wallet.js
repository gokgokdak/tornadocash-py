const $ = (id) => document.getElementById(id);
let sdk, pairing;

export async function connectWalletConnect(projectId, chains) {
    if (!projectId) throw new Error('Set WEBUI_WALLETCONNECT_PROJECT_ID in config.py to use WalletConnect.');
    const dialog = $('wallet-dialog');
    let cancelled = false, attempt, client, display;
    let reject;
    const closed = new Promise((_, fail) => { reject = fail; });
    const cancel = () => {
        cancelled = true;
        if (attempt) attempt.cancelled = true;
        reject(new Error('Wallet connection cancelled.'));
    };
    dialog.addEventListener('close', cancel);
    $('wallet-options').hidden = true;
    $('wallet-title').textContent = 'WalletConnect';
    $('wallet-qr').hidden = false;
    $('wallet-uri').value = '';
    $('wallet-qr-image').removeAttribute('src');
    $('wallet-message').textContent = 'Preparing WalletConnect…';
    $('wallet-message').dataset.error = false;
    if (!dialog.open) dialog.showModal();
    try {
        return await Promise.race([closed, (async () => {
            sdk ||= import('./vendor/walletconnect.js').then(async ({ EthereumProvider, toDataURL }) => ({
                client: await EthereumProvider.init({
                    projectId, optionalChains: chains, showQrModal: false,
                    optionalMethods: ['eth_sendTransaction', 'wallet_switchEthereumChain'],
                    optionalEvents: ['accountsChanged', 'chainChanged'],
                    metadata: { name: 'Tornado', description: 'Local Tornado client', url: location.origin, icons: [] },
                    disableProviderPing: true,
                }),
                toDataURL,
            })).catch((error) => { sdk = null; throw error; });
            const loaded = await sdk;
            client = loaded.client;
            if (cancelled) throw new Error('Wallet connection cancelled.');
            if (client.session && !pairing) return client;
            display = (uri) => {
                $('wallet-uri').value = uri;
                $('wallet-message').textContent = 'Approve the connection in your wallet…';
                $('wallet-message').dataset.error = false;
                loaded.toDataURL(uri, { width: 256, margin: 2 }).then((src) => {
                    if (!cancelled) $('wallet-qr-image').src = src;
                }).catch(reject);
            };
            client.on('display_uri', display);
            if (!pairing) {
                const pending = { uri: '', cancelled: false };
                const remember = (uri) => { pending.uri = uri; };
                client.on('display_uri', remember);
                pending.promise = client.connect({ optionalChains: chains }).then(async () => {
                    // A cancelled proposal can still be approved by the wallet later.
                    if (pending.cancelled) { await client.disconnect(); throw new Error('Wallet connection cancelled.'); }
                    return client;
                }).finally(() => { client.removeListener('display_uri', remember); pairing = null; });
                pairing = pending;
            }
            attempt = pairing;
            attempt.cancelled = false;
            if (attempt.uri) display(attempt.uri);
            return await attempt.promise;
        })()]);
    } catch (error) {
        cancelled = true;
        if (attempt) attempt.cancelled = true;
        throw error;
    } finally {
        dialog.removeEventListener('close', cancel);
        if (display) client.removeListener('display_uri', display);
        $('wallet-qr').hidden = true;
        $('wallet-options').hidden = false;
        $('wallet-title').textContent = 'Connect a wallet';
        dialog.close();
    }
}
