from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
import asyncio
import time
import threading

import winsdk.windows.devices.bluetooth.advertisement as wwda
from winsdk.windows.devices.bluetooth.advertisement import BluetoothLEAdvertisementPublisherStatus
import winsdk.windows.storage.streams as wwss

# 명령어 매핑
def get_command(mode, submode):
    if not (0 <= submode <= 9):
        submode = 0

    commands = {
        "shock1": ["d5964c", "d41f5d", "d7846f", "d60d7e", "d1b20a", "d03b1b", "d3a029", "d22938", "dddec0", "dc57d1"],
        "shock2": ["a5113f", "a4982e", "a7031c", "a68a0d", "a13579", "a0bc68", "a3275a", "a2ae4b", "ad59b3", "acd0a2"],
        "shake":  ["C5175C", "F41D7C", "F7864E", "F60F5F", "F1B02B", "F0393A", "F3A208", "F22B19", "FDDCE1", "FC55F0"],
        "telescope": ["E5157D", "E49C6C", "E7075E", "E68E4F", "E1313B", "E0B82A", "E32318", "E2AA09", "ED5DF1", "ECD4E0"],
    }

    return commands.get(mode, ["E5157D"])[submode]

# BLE 광고 전송
async def send_command(command, duration):
    adv = wwda.BluetoothLEAdvertisementPublisher()
    mdata = wwda.BluetoothLEManufacturerData()
    mdata.company_id = 0xFF

    writer = wwss.DataWriter()
    writer.write_bytes(bytearray.fromhex("0000006db643ce97fe427c" + command))
    mdata.data = writer.detach_buffer()

    adv.advertisement.manufacturer_data.append(mdata)
    adv.start()

    while adv.status != BluetoothLEAdvertisementPublisherStatus.STARTED:
        time.sleep(0.01)

    time.sleep(duration)
    adv.stop()

# bpm 모드 반복 진동 쓰레드
class SendBeat(threading.Thread):
    def __init__(self, duration, bpm):
        super().__init__()
        self.duration = duration
        self.ppulse = 0.5
        self.ppause = max((60 - (bpm * self.ppulse)) / bpm, 0)
        self.do_run = True

    def run(self):
        while getattr(self, "do_run", True):
            command = get_command("shake", 3)
            asyncio.run(send_command(command, self.duration))
            time.sleep(self.ppause)

# 요청 처리 함수
sb = None
def toy_control(params):
    global sb
    duration = float(params.get("duration", 0.05))
    mode = params.get("mode", "shake")
    submode = int(params.get("submode", 0))

    if mode == "bpm":
        bpm = submode
        if bpm == 0:
            if sb:
                sb.do_run = False
        else:
            sb = SendBeat(duration, bpm)
            sb.start()
    else:
        command = get_command(mode, submode)
        asyncio.run(send_command(command, duration))

# HTTP 핸들러
class RequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")  # CORS 허용
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        self._set_headers()
        self.wfile.write(json.dumps({"status": "ready"}).encode("utf-8"))

    def do_POST(self):
        if self.path != "/lovespouse":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        params = json.loads(body.decode("utf-8"))

        toy_control(params)
        self._set_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))

# 서버 실행
def run_server(port=8080):
    logging.basicConfig(level=logging.INFO)
    server_address = ("", port)
    httpd = HTTPServer(server_address, RequestHandler)
    logging.info(f"LoveSpouse BLE control server running on port {port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info("Stopping server")

if __name__ == "__main__":
    run_server()
