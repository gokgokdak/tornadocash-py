const $ = (id) => document.getElementById(id);
const number = (value) => value == null ? '—' : Number(value).toLocaleString('en-US');
const pending = new Map();
let socket, sequence = 0, snapshot = { instances: [] };
let selected = '', poolList = '', account = '', walletChain = '', busy = false, draft = null;
let lastLogId = 0, firstLogs = true;
let provider;
const providers = new WeakSet();
const states = {
    starting: 'Starting', connecting: 'Connecting RPC', retrying: 'Retrying RPC',
    initializing: 'Initializing', syncing: 'Syncing', ready: 'Ready', error: 'Error',
    stopped: 'Stopped', building_tree: 'Building tree',
    proving: 'Generating proof', relaying: 'Submitting to relayer', working: 'Working',
};
const stateLabel = (state) => states[state] || state?.replaceAll('_', ' ') || 'Starting';
const noteId = (note) => (note || '').trim().split('-').slice(0, 3).join('-').toLowerCase();

function checkBackend(id) {
    if (socket?.readyState !== WebSocket.OPEN) throw new Error('Backend disconnected. Please wait for reconnection.');
    if (snapshot.stopping) throw new Error('Backend is shutting down.');
    if (id !== undefined && !snapshot.instances.some((item) => item.id === id)) throw new Error(id
        ? 'This instance is not configured in the backend. Check the selected pool or note.'
        : 'No pool is available yet. Wait for backend status.');
}

function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text != null) node.textContent = text;
    if (className) node.className = className;
    return node;
}

function message(text, error = false) {
    $('message').textContent = text;
    $('message').dataset.error = error;
    let target = $('message');
    for (const name of ['backup']) {
        if (!$(`${name}-dialog`).open) continue;
        target = $(`${name}-message`);
        target.textContent = text;
        target.dataset.error = error;
    }
    if (error) target.scrollIntoView({ block: 'nearest' });
}

async function rpc(method, params) {
    if ('note' in params && !params.note.trim()) throw new Error('Enter your note.');
    checkBackend(['status', 'receipt'].includes(method) ? undefined : params.instance || noteId(params.note));
    return new Promise((resolve, reject) => {
        const id = ++sequence;
        pending.set(id, { resolve, reject });
        socket.send(JSON.stringify({ id, method, params }));
    });
}

function connect() {
    const url = new URLSearchParams(location.search).get('ws') || `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.hostname || '127.0.0.1'}:8765`;
    try { socket = new WebSocket(url); }
    catch (error) { message(error.message, true); return; }
    firstLogs = true;
    socket.onopen = () => { renderStatus(); updateLogStatus(); };
    socket.onmessage = ({ data }) => {
        let result;
        try { result = JSON.parse(data); } catch { return; }
        if (result.type === 'logs') { appendLogs(result); return; }
        if (result.type === 'status') {
            snapshot = result;
            if (!snapshot.instances.some((item) => item.id === selected)) selected = snapshot.instances[0]?.id || '';
            const signature = JSON.stringify(snapshot.instances.map(({ id, chain_id, symbol, unit }) => [id, chain_id, symbol, unit]));
            if (signature !== poolList) { poolList = signature; renderPools(); }
            renderStatus();
            return;
        }
        const request = pending.get(result.id);
        if (!request) return;
        if (result.type === 'progress') {
            if (busy && typeof result.message === 'string') message(result.message);
            return;
        }
        pending.delete(result.id);
        if (result.error) request.reject(new Error(result.error));
        else request.resolve(result.result);
    };
    socket.onclose = () => {
        for (const request of pending.values()) {
            request.reject(new Error('Backend disconnected.'));
        }
        pending.clear();
        renderStatus();
        updateLogStatus();
        setTimeout(connect, 2000);
    };
    socket.onerror = () => socket.close();
}

function updateLogStatus() {
    $('logs-status').textContent = socket?.readyState === WebSocket.OPEN
        ? `${$('logs').childElementCount} / 500 lines · connected`
        : 'Disconnected · logs kept · reconnecting…';
}

function appendLogs({ entries, reset }) {
    const output = $('logs');
    if (reset || firstLogs) { output.replaceChildren(); lastLogId = 0; firstLogs = false; }
    for (const entry of entries) {
        if (entry.id <= lastLogId) continue;
        lastLogId = entry.id;
        const line = element('div', entry.text, 'log-line');
        line.dataset.level = entry.level;
        output.append(line);
    }
    while (output.childElementCount > 500) output.firstElementChild.remove();
    if ($('auto-scroll').checked) output.scrollTop = output.scrollHeight;
    updateLogStatus();
}

function hasProgress(item) {
    return socket?.readyState === WebSocket.OPEN
        && !['starting', 'connecting', 'retrying', 'initializing', 'error', 'stopped'].includes(item?.state)
        && ['syncing', 'ready'].includes(item?.sync_state || item?.state)
        && Number.isFinite(item?.progress) && item.latest_block != null;
}

const pool = () => snapshot.instances.find((item) => item.id === selected);

function options(select, values, value) {
    select.replaceChildren(...values.map(([key, label]) => new Option(label, key)));
    select.value = value;
}

function renderPools() {
    const current = pool();
    const chains = [...new Map(snapshot.instances.map((item) => [item.chain_id, item.chain])).entries()];
    options($('network'), chains.map(([id, name]) => [id, name.charAt(0).toUpperCase() + name.slice(1)]), String(current?.chain_id || ''));
    const tokens = [...new Set(snapshot.instances.filter((item) => item.chain_id === current?.chain_id).map((item) => item.symbol))];
    options($('token'), tokens.map((symbol) => [symbol, symbol.toUpperCase()]), current?.symbol || '');
    const amounts = snapshot.instances.filter((item) => item.chain_id === current?.chain_id && item.symbol === current?.symbol).sort((a, b) => Number(a.unit) - Number(b.unit));
    $('amounts').replaceChildren(...amounts.map((item) => {
        const label = element('label', null, 'amount-choice');
        const radio = document.createElement('input');
        Object.assign(radio, { type: 'radio', name: 'amount', value: item.id, checked: item.id === selected });
        radio.onchange = () => { selected = item.id; renderStatus(); };
        label.append(radio, element('span', `${item.unit} ${item.symbol.toUpperCase()}`));
        return label;
    }));
    renderStatistics();
}

function renderStatistics() {
    const current = pool();
    $('selected-pool').textContent = current ? `${current.unit} ${current.symbol.toUpperCase()}` : '—';
    $('anonymity').textContent = current?.anonymity_set == null ? '—' : `${number(current.anonymity_set)} equal user deposits`;
    for (const [id, key] of [['deposits', 'deposits_total'], ['withdrawals', 'withdrawals_total'], ['synced-block', 'synced_block'], ['latest-block', 'latest_block']]) $(id).textContent = number(current?.[key]);
    const updated = current?.last_update_sec == null ? null : new Date(current.last_update_sec * 1000);
    $('last-update').textContent = updated ? updated.toLocaleString(undefined, { hourCycle: 'h23' }) : '—';
    if (!hasProgress(current)) {
        $('latest-block').textContent = '—';
        $('synced-block').textContent = current?.synced_block == null ? '—' : `${number(current.synced_block)} (cached)`;
    }
    $('pool-state').textContent = socket?.readyState === WebSocket.OPEN
        ? current?.message || current?.activity || stateLabel(current?.state)
        : 'Backend disconnected. Waiting to reconnect.';
    $('pool-address').textContent = current?.address || 'Waiting for backend';
}

function renderStatus() {
    const connected = socket?.readyState === WebSocket.OPEN;
    const instances = snapshot.instances;
    const readyCount = connected ? instances.filter((item) => item.ready).length : '—';
    $('ready-count').textContent = `${readyCount} / ${instances.length} ready`;
    $('instances').replaceChildren(...instances.map((item) => {
        const row = document.createElement('tr');
        const name = element('td', `${item.unit} ${item.symbol.toUpperCase()}`);
        name.append(element('small', item.chain, 'muted chain'));
        name.title = item.address;
        if (item.error) name.append(element('small', item.error, 'instance-error'));
        const state = element('td', connected ? stateLabel(item.state) : 'Disconnected', 'state');
        state.dataset.state = connected ? item.state : 'error';
        if (connected && item.message) state.append(element('small', item.message, 'instance-message'));
        if (connected && item.activity && item.activity !== item.message) state.append(element('small', item.activity, 'instance-message'));
        if (connected && item.sync_activity && item.sync_activity !== item.activity) state.append(element('small', item.sync_activity, 'instance-message'));
        const sync = element('td', null, 'sync');
        if (hasProgress(item)) {
            sync.textContent = `${number(item.synced_block)} / ${number(item.latest_block)}`;
            const progress = document.createElement('progress');
            progress.max = 1;
            progress.value = Math.max(0, Math.min(1, item.progress));
            progress.setAttribute('aria-label', `${item.id} block synchronization`);
            const percent = Math.min(item.remaining_blocks > 0 ? 99.9 : 100, 100 * item.progress);
            sync.append(progress, element('small', `${percent.toFixed(1)}%${item.remaining_blocks == null ? '' : ` · ${number(item.remaining_blocks)} blocks left`}`));
        } else {
            sync.textContent = item.synced_block == null ? 'Cached block —' : `Cached block ${number(item.synced_block)}`;
            sync.append(element('small', !connected ? 'Disconnected; waiting for backend'
                : item.latest_block == null ? 'Chain head not confirmed.' : `Last known head ${number(item.latest_block)}`));
        }
        const deposits = element('td', number(item.deposits_total));
        const withdrawals = element('td', number(item.withdrawals_total));
        deposits.title = `${number(item.deposits)} synced this session`;
        withdrawals.title = `${number(item.withdrawals)} synced this session`;
        row.append(name, state, sync, deposits, withdrawals);
        return row;
    }));
    if (!instances.length) {
        const row = document.createElement('tr');
        const cell = element('td', 'Waiting for backend…', 'muted');
        cell.colSpan = 5;
        row.append(cell);
        $('instances').append(row);
    }
    const rate = snapshot.relayer_fee_rate;
    $('relayer-fee').textContent = `Service fee: ${rate == null ? 'backend configured rate' : `${rate}%`} + network gas, deducted from the deposit.`;
    renderStatistics();
    updateControls();
}

function updateControls() {
    $('deposit-fields').disabled = busy || !!draft;
    $('withdraw-fields').disabled = busy;
    $('start-deposit').disabled = busy || !!draft;
    $('check-note').disabled = busy;
    $('confirm-withdraw').disabled = busy;
    $('network').disabled = busy || !!draft || !pool();
    $('wallet').disabled = busy;
    $('wallet').textContent = account ? `${account.slice(0, 6)}…${account.slice(-4)}` : 'Connect wallet';
    $('wallet').title = account ? `${account} · wallet chain ${Number(walletChain) || 'unknown'}` : 'Connect an Ethereum wallet';
    $('confirm-deposit').disabled = busy;
    $('approve-token').disabled = busy;
    $('cancel-deposit').disabled = busy;
}

async function run(action) {
    if (busy) return;
    busy = true;
    message('');
    updateControls();
    try { await action(); }
    catch (error) { message(error.message || String(error), true); }
    finally { busy = false; updateControls(); }
}

async function wallet(instance) {
    if (!provider) {
        if (!window.ethereum) throw new Error('No browser wallet found. Open this page in a browser with an Ethereum wallet.');
        bindWallet(window.ethereum);
    }
    const currentProvider = provider;
    message('Requesting wallet account access. Confirm in your wallet if prompted…');
    const accounts = await currentProvider.request({ method: 'eth_requestAccounts' });
    if (!accounts[0]) throw new Error('No wallet account selected.');
    if (instance) {
        const chainId = `0x${instance.chain_id.toString(16)}`;
        message('Checking wallet network…');
        const current = await currentProvider.request({ method: 'eth_chainId' });
        if (current.toLowerCase() !== chainId) {
            message(`Confirm the switch to ${instance.chain} in your wallet…`);
            await currentProvider.request({ method: 'wallet_switchEthereumChain', params: [{ chainId }] });
        }
    }
    const address = (await currentProvider.request({ method: 'eth_accounts' }))[0] || '';
    if (provider !== currentProvider) throw new Error('Wallet connection changed. Please retry.');
    if (!address) throw new Error('No wallet account selected.');
    account = address;
    message('');
    updateControls();
    return account;
}

async function sendTransaction(transaction, instance) {
    checkBackend(instance.id);
    const currentProvider = provider;
    if (!currentProvider) throw new Error('Wallet disconnected. Please reconnect.');
    message('Checking wallet network and account before submission…');
    const chainId = await currentProvider.request({ method: 'eth_chainId' });
    const accounts = await currentProvider.request({ method: 'eth_accounts' });
    if (provider !== currentProvider) throw new Error('Wallet connection changed. Please retry.');
    if (Number(chainId) !== instance.chain_id || Number(transaction.chainId) !== instance.chain_id) throw new Error('Wallet network changed. Select the pool network and retry.');
    if (accounts[0]?.toLowerCase() !== transaction.from?.toLowerCase()) throw new Error('Wallet account changed. Please retry the transaction.');
    checkBackend(instance.id);
    message('Confirm transaction signing and submission in your wallet…');
    const hash = await currentProvider.request({ method: 'eth_sendTransaction', params: [transaction] });
    await waitReceipt(instance, hash);
    return hash;
}

async function waitReceipt(instance, hash) {
    message(`Transaction submitted. Waiting for confirmation: ${hash}`);
    let disconnected = false;
    const waitForBackend = () => {
        if (!disconnected) message(`Backend disconnected. Waiting to reconnect and check transaction: ${hash}`);
        disconnected = true;
    };
    for (;;) {
        await new Promise((resolve) => setTimeout(resolve, 5000));
        if (socket?.readyState !== WebSocket.OPEN) { waitForBackend(); continue; }
        if (disconnected) {
            message(`Backend reconnected. Checking transaction confirmation: ${hash}`);
            disconnected = false;
        }
        let receipt;
        try { receipt = await rpc('receipt', { instance: instance.id, hash }); }
        catch (error) { if (socket?.readyState !== WebSocket.OPEN) { waitForBackend(); continue; } throw error; }
        if (receipt.status === 'failed') throw new Error(`Transaction reverted: ${hash}`);
        if (receipt.status === 'confirmed') { message(`Transaction confirmed: ${hash}`); return; }
    }
}

function closeDraft() {
    draft = null;
    $('deposit-note').value = '';
    $('backup-message').textContent = '';
    updateControls();
}

$('network').onchange = () => { selected = snapshot.instances.find((item) => String(item.chain_id) === $('network').value)?.id || ''; renderPools(); renderStatus(); };
$('clear-logs').onclick = () => { $('logs').replaceChildren(); updateLogStatus(); };
$('auto-scroll').onchange = () => { if ($('auto-scroll').checked) $('logs').scrollTop = $('logs').scrollHeight; };
$('live-logs').ontoggle = () => { if ($('live-logs').open && $('auto-scroll').checked) $('logs').scrollTop = $('logs').scrollHeight; };
$('token').onchange = () => { selected = snapshot.instances.find((item) => item.chain_id === pool()?.chain_id && item.symbol === $('token').value)?.id || ''; renderPools(); renderStatus(); };
$('wallet').onclick = () => run(async () => {
    await wallet(pool());
    message('Wallet connected.');
});
for (const name of ['deposit', 'withdraw']) {
    $(`${name}-panel`).addEventListener('invalid', (event) => message(event.target.validationMessage, true), true);
    $(`${name}-tab`).onclick = () => {
        if (!busy) message('');
        for (const tab of ['deposit', 'withdraw']) {
            $(`${tab}-tab`).setAttribute('aria-selected', tab === name);
            $(`${tab}-panel`).hidden = tab !== name;
        }
        renderStatus();
    };
}
$('deposit-panel').onsubmit = (event) => {
    event.preventDefault();
    run(async () => {
        const instance = pool();
        checkBackend(selected);
        await wallet(instance);
        message('Creating deposit note…');
        draft = { ...await rpc('create_note', { instance: instance.id }), instance };
        $('deposit-note').value = draft.note;
        $('backup-message').textContent = '';
        $('approve-token').hidden = instance.native;
        $('backup-dialog').showModal();
        message('Save your note, then confirm the deposit.');
    });
};
$('cancel-deposit').onclick = () => $('backup-dialog').close();
$('backup-dialog').onclose = closeDraft;
$('backup-dialog').oncancel = (event) => { if (busy) event.preventDefault(); };
$('copy-note').onclick = async () => {
    try { await navigator.clipboard.writeText(draft.note); message('Note copied.'); }
    catch { $('deposit-note').focus(); $('deposit-note').select(); message('Select and copy the note manually.', true); }
};
$('download-note').onclick = () => {
    try {
        const url = URL.createObjectURL(new Blob([draft.note + '\n'], { type: 'text/plain' }));
        const link = Object.assign(document.createElement('a'), { href: url, download: `tornado-${draft.instance.id}-${Date.now()}.txt` });
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        message('Download requested. Check that the note file was saved.');
    } catch (error) { message(error.message || String(error), true); }
};
$('approve-token').onclick = () => run(async () => {
    checkBackend(draft.instance.id);
    const address = await wallet(draft.instance);
    message('Building token approval transaction…');
    const tx = await rpc('approve', { instance: draft.instance.id, account: address });
    await sendTransaction(tx, draft.instance);
    message('Token approved. You can now deposit.');
});
$('confirm-deposit').onclick = () => run(async () => {
    if (!draft) throw new Error('Create a deposit note first.');
    if (!window.confirm('Have you saved your note? Without it, you cannot withdraw your deposit.')) return;
    checkBackend(draft.instance.id);
    const address = await wallet(draft.instance);
    message('Building deposit transaction…');
    const tx = await rpc('deposit', { instance: draft.instance.id, account: address, note: draft.note });
    await sendTransaction(tx, draft.instance);
    $('backup-dialog').close();
});
for (const radio of document.querySelectorAll('input[name=mode]')) radio.onchange = () => {
    const relayer = radio.value === 'relayer' && radio.checked;
    $('relayer-field').hidden = !relayer;
    $('relayer').required = relayer;
    $('accept-fee').required = relayer;
    $('accept-fee').checked = false;
};
$('withdraw-note').oninput = () => { $('note-status').textContent = ''; renderStatus(); };
$('check-note').onclick = () => run(async () => {
    message('Checking note status…');
    const result = await rpc('note_status', { note: $('withdraw-note').value.trim() });
    $('note-status').textContent = `${result.deposited ? 'Deposited' : 'Not deposited'} · ${result.spent ? 'Already spent' : 'Unspent'} · ${number(result.deposits_after)} deposits and ${number(result.withdrawals_after)} withdrawals after yours.`;
    message('Note status checked.');
});
$('withdraw-panel').onsubmit = (event) => {
    event.preventDefault();
    run(async () => {
        const note = $('withdraw-note').value.trim();
        const recipient = $('recipient').value.trim();
        message('Checking deposit and withdrawal status…');
        const status = await rpc('note_status', { note });
        const instance = snapshot.instances.find((item) => item.id === status.instance);
        if (!instance) throw new Error('This note does not match a configured instance.');
        if (!status.deposited) throw new Error('The deposit has not been found.');
        if (status.spent) throw new Error('This note has already been spent.');
        if (document.querySelector('input[name=mode]:checked').value === 'relayer') {
            const relayer = $('relayer').value.trim();
            if (!/^https?:\/\//i.test(relayer)) throw new Error('Enter an HTTP or HTTPS relayer URL.');
            message('Preparing withdrawal for the relayer…');
            const result = await rpc('relay_withdraw', { note, recipient, relayer });
            await waitReceipt(instance, result.hash);
        } else {
            const address = await wallet(instance);
            message('Building withdrawal transaction…');
            const tx = await rpc('withdraw', { note, recipient, account: address });
            await sendTransaction(tx, instance);
        }
    });
};
function bindWallet(next) {
    provider = next;
    account = walletChain = '';
    if (!next) { updateControls(); return; }
    if (!providers.has(next)) {
        providers.add(next);
        next.on?.('accountsChanged', (accounts) => { if (provider === next) { account = accounts[0] || ''; updateControls(); } });
        next.on?.('chainChanged', (chainId) => { if (provider === next) { walletChain = chainId; updateControls(); } });
        next.on?.('disconnect', () => { if (provider === next) { bindWallet(null); message('Wallet disconnected. Please reconnect.', true); } });
    }
    next.request({ method: 'eth_accounts' }).then((accounts) => { if (provider === next) { account = accounts[0] || ''; updateControls(); } }).catch(() => {});
    next.request({ method: 'eth_chainId' }).then((chainId) => { if (provider === next) { walletChain = chainId; updateControls(); } }).catch(() => {});
}
window.addEventListener('ethereum#initialized', () => { if (!provider) bindWallet(window.ethereum); });
bindWallet(window.ethereum);
updateControls();
connect();
