import asyncio
import json
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from typing import Any

import websockets


class WebSocketGui(object):

    def __init__(self, root: tk.Tk) -> None:
        self.root: tk.Tk = root
        self.root.title('TornadoCash WebSocket Verifier')
        self.root.geometry('900x640')

        self.base_url: tk.StringVar = tk.StringVar(value='ws://127.0.0.1:8000')
        self.chain: tk.StringVar = tk.StringVar(value='sepolia')
        self.symbol: tk.StringVar = tk.StringVar(value='eth')
        self.unit: tk.StringVar = tk.StringVar(value='1')
        self.operation: tk.StringVar = tk.StringVar(value='subscribe')
        self.request_id: tk.StringVar = tk.StringVar(value='1')
        self.status: tk.StringVar = tk.StringVar(value='Disconnected')

        self.loop: asyncio.AbstractEventLoop | None = None
        self.websocket: Any | None = None
        self.thread: threading.Thread | None = None
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.ui_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.connected: bool = False
        self.current_url: str | None = None
        self.pending_send_after_connect: bool = False

        self._build()
        self._drain_logs()
        self.root.protocol('WM_DELETE_WINDOW', self.close)

    def _build(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        top = ttk.Frame(self.root, padding=10)
        top.grid(row=0, column=0, sticky='ew')
        top.columnconfigure(1, weight=1)
        top.columnconfigure(3, weight=1)

        ttk.Label(top, text='Base URL').grid(row=0, column=0, sticky='w', padx=(0, 6))
        ttk.Entry(top, textvariable=self.base_url).grid(row=0, column=1, sticky='ew', padx=(0, 12))
        ttk.Label(top, text='Operation').grid(row=0, column=2, sticky='w', padx=(0, 6))
        ttk.Combobox(
            top,
            textvariable=self.operation,
            values=('subscribe', 'events', 'metadata'),
            state='readonly',
            width=16,
        ).grid(row=0, column=3, sticky='w')

        ttk.Label(top, text='Chain').grid(row=1, column=0, sticky='w', padx=(0, 6), pady=(8, 0))
        ttk.Combobox(
            top,
            textvariable=self.chain,
            values=('ethereum', 'optimism', 'bsc', 'polygon', 'arbitrum', 'avalanche', 'sepolia'),
            width=18,
        ).grid(row=1, column=1, sticky='w', pady=(8, 0))
        ttk.Label(top, text='Symbol').grid(row=1, column=2, sticky='w', padx=(0, 6), pady=(8, 0))
        ttk.Combobox(
            top,
            textvariable=self.symbol,
            values=('eth', 'bnb', 'pol', 'avax', 'dai', 'cdai', 'usdc', 'usdt', 'wbtc'),
            width=16,
        ).grid(row=1, column=3, sticky='w', pady=(8, 0))

        ttk.Label(top, text='Unit').grid(row=2, column=0, sticky='w', padx=(0, 6), pady=(8, 0))
        ttk.Combobox(
            top,
            textvariable=self.unit,
            values=('0.1', '1', '10', '100', '500', '1000', '5000', '10000', '50000', '100000', '500000', '5000000'),
            width=18,
        ).grid(row=2, column=1, sticky='w', pady=(8, 0))
        ttk.Label(top, text='Request ID').grid(row=2, column=2, sticky='w', padx=(0, 6), pady=(8, 0))
        ttk.Entry(top, textvariable=self.request_id, width=18).grid(row=2, column=3, sticky='w', pady=(8, 0))

        buttons = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        buttons.grid(row=1, column=0, sticky='ew')
        buttons.columnconfigure(7, weight=1)

        ttk.Button(buttons, text='Connect', command=self.connect).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text='Disconnect', command=self.disconnect).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(buttons, text='Send Request', command=self.send_request).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(buttons, text='Metadata Test', command=self.metadata_test).grid(row=0, column=3, padx=(0, 8))
        ttk.Button(buttons, text='Clear Log', command=lambda: self.log_text.delete('1.0', tk.END)).grid(row=0, column=4, padx=(0, 8))
        ttk.Label(buttons, textvariable=self.status).grid(row=0, column=8, sticky='e')

        body = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        body.grid(row=2, column=0, sticky='nsew')
        body.rowconfigure(1, weight=1)
        body.columnconfigure(0, weight=1)

        ttk.Label(body, text='Request JSON').grid(row=0, column=0, sticky='w')
        self.request_text = scrolledtext.ScrolledText(body, height=7)
        self.request_text.grid(row=1, column=0, sticky='ew', pady=(4, 10))
        self.request_text.insert('1.0', json.dumps({'params': {}}, indent=2))

        ttk.Label(body, text='Messages').grid(row=2, column=0, sticky='w')
        self.log_text = scrolledtext.ScrolledText(body, height=18)
        self.log_text.grid(row=3, column=0, sticky='nsew', pady=(4, 0))

    def build_url(self, operation: str | None = None) -> str:
        op = (operation if operation is not None else self.operation.get()).strip('/')
        return '/'.join([
            self.base_url.get().rstrip('/'),
            self.chain.get().strip(),
            self.symbol.get().strip(),
            self.unit.get().strip(),
            op,
        ])

    def connect(self) -> None:
        if self.connected:
            self._log('Already connected')
            return
        url = self.build_url()
        self.current_url = url
        self.thread = threading.Thread(target=self._run_client_thread, args=(url,), daemon=True)
        self.thread.start()

    def disconnect(self) -> None:
        if self.loop is None or self.websocket is None:
            return
        asyncio.run_coroutine_threadsafe(self.websocket.close(), self.loop)

    def close(self) -> None:
        if self.connected:
            self.disconnect()
            self.root.after(200, self.root.destroy)
        else:
            self.root.destroy()

    def send_request(self) -> None:
        if self.loop is None or self.websocket is None or not self.connected:
            messagebox.showwarning('Not connected', 'Connect to a WebSocket endpoint first.')
            return

        try:
            payload = json.loads(self.request_text.get('1.0', tk.END))
            if not isinstance(payload, dict):
                raise ValueError('Request JSON must be an object')
            payload.setdefault('id', self.request_id.get())
        except BaseException as e:
            messagebox.showerror('Invalid JSON', str(e))
            return

        text = json.dumps(payload)
        asyncio.run_coroutine_threadsafe(self._send(text), self.loop)

    def metadata_test(self) -> None:
        self.operation.set('metadata')
        self.request_text.delete('1.0', tk.END)
        self.request_text.insert('1.0', json.dumps({'params': {}}, indent=2))
        target_url = self.build_url('metadata')
        if self.connected and self.current_url == target_url:
            self.send_request()
        elif self.connected:
            self.pending_send_after_connect = True
            self.disconnect()
            self.root.after(800, self.connect)
        else:
            self.pending_send_after_connect = True
            self.connect()

    def _run_client_thread(self, url: str) -> None:
        asyncio.run(self._run_client(url))

    async def _run_client(self, url: str) -> None:
        self.loop = asyncio.get_running_loop()
        self._log(f'Connecting: {url}')
        try:
            async with websockets.connect(url) as websocket:
                self.websocket = websocket
                self.connected = True
                self._post_status(f'Connected: {url}')
                self._log('Connected')
                if self.pending_send_after_connect:
                    self.pending_send_after_connect = False
                    self._post_send_request()
                async for message in websocket:
                    self._log(self._format_message('recv', message))
        except BaseException as e:
            self._log(f'Connection closed: {e}')
        finally:
            self.connected = False
            self.websocket = None
            self.loop = None
            self.current_url = None
            self._post_status('Disconnected')

    async def _send(self, text: str) -> None:
        if self.websocket is None:
            return
        await self.websocket.send(text)
        self._log(self._format_message('send', text))

    def _format_message(self, direction: str, message: str) -> str:
        try:
            parsed = json.loads(message)
            body = json.dumps(parsed, ensure_ascii=False, indent=2)
        except BaseException:
            body = message
        return f'{direction.upper()} {body}'

    def _log(self, text: str) -> None:
        timestamp = time.strftime('%H:%M:%S')
        self.log_queue.put(f'[{timestamp}] {text}\n')

    def _post_status(self, text: str) -> None:
        self.ui_queue.put(('status', text))

    def _post_send_request(self) -> None:
        self.ui_queue.put(('send_request', None))

    def _drain_logs(self) -> None:
        while True:
            try:
                action, value = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            if action == 'status':
                self.status.set(value)
            elif action == 'send_request':
                self.root.after(200, self.send_request)

        while True:
            try:
                item = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.log_text.insert(tk.END, item)
            self.log_text.see(tk.END)
        self.root.after(100, self._drain_logs)


def main() -> None:
    root = tk.Tk()
    WebSocketGui(root)
    root.mainloop()


if __name__ == '__main__':
    main()
