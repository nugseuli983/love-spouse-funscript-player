from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
import asyncio
import time
import threading
import os
from urllib.parse import parse_qs, urlparse

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

# 스크립트 플레이어 클래스
class ScriptPlayer(threading.Thread):
    def __init__(self, script_data, mode="shake"):
        super().__init__()
        self.script_data = script_data
        self.actions = script_data.get("actions", [])
        self.mode = mode
        self.do_run = True
        self.paused = False
        self.start_time = None
        self.pause_offset = 0
        self.last_action_index = 0
        self.video_sync = False
        self.video_time = 0
        
    def run(self):
        if not self.actions:
            return
            
        self.start_time = time.time() * 1000  # 현재 시간 (밀리초)
        
        # 액션을 시간순으로 정렬
        sorted_actions = sorted(self.actions, key=lambda x: x.get("at", 0))
        
        i = 0
        while i < len(sorted_actions) and self.do_run:
            if self.paused:
                time.sleep(0.1)
                continue
                
            if self.video_sync:
                # 비디오 시간 기준으로 액션 실행
                elapsed = self.video_time
            else:
                # 내부 타이머 기준으로 액션 실행
                current_time = time.time() * 1000
                elapsed = current_time - self.start_time - self.pause_offset
            
            # 현재 시간에 맞는 액션 찾기
            while i < len(sorted_actions):
                action = sorted_actions[i]
                action_time = action.get("at", 0)
                
                if elapsed >= action_time:
                    # 액션 실행
                    pos = action.get("pos", 0)
                    # pos 값(0-100)을 submode 값(0-9)으로 변환
                    submode = min(9, max(0, int(pos / 11)))
                    command = get_command(self.mode, submode)
                    asyncio.run(send_command(command, 0.05))  # 짧은 지속시간으로 명령 전송
                    self.last_action_index = i
                    i += 1
                else:
                    break
            
            # 다음 액션까지 대기
            if i < len(sorted_actions):
                next_action = sorted_actions[i]
                next_time = next_action.get("at", 0)
                if self.video_sync:
                    # 비디오 동기화 모드에서는 짧게 대기
                    sleep_time = 0.01
                else:
                    # 내부 타이머 모드에서는 다음 액션까지 대기
                    sleep_time = min(0.01, (next_time - elapsed) / 1000)
                time.sleep(max(0.001, sleep_time))
            else:
                # 모든 액션 완료
                time.sleep(0.1)
    
    def pause(self):
        if not self.paused:
            self.paused = True
            self.pause_start_time = time.time() * 1000
    
    def resume(self):
        if self.paused:
            self.paused = False
            pause_duration = time.time() * 1000 - self.pause_start_time
            self.pause_offset += pause_duration
    
    def stop(self):
        self.do_run = False
        
    def set_video_time(self, video_time_ms):
        """비디오 시간을 설정하여 스크립트와 동기화"""
        self.video_time = video_time_ms
        self.video_sync = True
        
    def disable_video_sync(self):
        """비디오 동기화 모드 비활성화"""
        self.video_sync = False
        # 현재 시간 기준으로 시작 시간 재설정
        current_time = time.time() * 1000
        if self.last_action_index < len(self.actions):
            last_action = sorted(self.actions, key=lambda x: x.get("at", 0))[self.last_action_index]
            last_time = last_action.get("at", 0)
            self.start_time = current_time - last_time
            self.pause_offset = 0

# 스크립트 관리
script_player = None

def load_script(script_data, mode="shake"):
    global script_player
    
    # 기존 플레이어 중지
    if script_player and script_player.is_alive():
        script_player.stop()
        script_player.join(1)
    
    # 새 플레이어 생성
    script_player = ScriptPlayer(script_data, mode)
    return {"status": "loaded", "actions": len(script_player.actions)}

def start_script():
    global script_player
    if not script_player:
        return {"status": "error", "message": "No script loaded"}
    if script_player.is_alive():
        if script_player.paused:
            script_player.resume()
            return {"status": "resumed"}
        return {"status": "already_running"}
    # If script_player exists but is not alive, recreate thread for replay
    script_data = script_player.script_data
    mode = script_player.mode
    script_player = ScriptPlayer(script_data, mode)
    script_player.start()
    return {"status": "started"}

def pause_script():
    global script_player
    if not script_player or not script_player.is_alive():
        return {"status": "error", "message": "No script running"}
    
    script_player.pause()
    return {"status": "paused"}

def stop_script():
    global script_player
    if not script_player or not script_player.is_alive():
        return {"status": "error", "message": "No script running"}
    script_player.stop()
    script_player.join(1)
    # Do NOT set script_player = None, keep script data for replay
    return {"status": "stopped"}

def sync_with_video(video_time_ms):
    global script_player
    if not script_player or not script_player.is_alive():
        return {"status": "error", "message": "No script running"}
    
    script_player.set_video_time(video_time_ms)
    return {"status": "synced", "time": video_time_ms}

def disable_video_sync():
    global script_player
    if not script_player or not script_player.is_alive():
        return {"status": "error", "message": "No script running"}
    
    script_player.disable_video_sync()
    return {"status": "sync_disabled"}

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
    def _set_headers(self, content_type="application/json"):
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")  # CORS 허용
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Toy-Mode, X-Video-Time")
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Toy-Mode, X-Video-Time")
        self.end_headers()

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)
        
        # 루트 경로 - HTML 인터페이스 제공
        if path == "/" or path == "":
            try:
                with open("script_player.html", "rb") as file:
                    self._set_headers("text/html")
                    self.wfile.write(file.read())
                    return
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"File not found")
                return
        
        # 비디오 파일 제공
        if path.startswith("/videos/"):
            video_path = path[8:]  # "/videos/" 제거
            try:
                with open(os.path.join("videos", video_path), "rb") as file:
                    self.send_response(200)
                    if video_path.endswith(".mp4"):
                        self.send_header("Content-type", "video/mp4")
                    elif video_path.endswith(".webm"):
                        self.send_header("Content-type", "video/webm")
                    else:
                        self.send_header("Content-type", "application/octet-stream")
                    self.end_headers()
                    self.wfile.write(file.read())
                    return
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Video file not found")
                return
        
        if path == "/lovespouse/script":
            # 스크립트 관련 명령 처리
            action = query.get("action", ["status"])[0]
            
            if action == "start":
                response = start_script()
            elif action == "pause":
                response = pause_script()
            elif action == "stop":
                response = stop_script()
            elif action == "sync":
                if "time" in query:
                    video_time = int(query["time"][0])
                    response = sync_with_video(video_time)
                else:
                    response = {"status": "error", "message": "Missing time parameter"}
            elif action == "disable_sync":
                response = disable_video_sync()
            elif action == "status":
                if not script_player:
                    response = {"status": "no_script"}
                elif not script_player.is_alive():
                    response = {"status": "loaded_not_running"}
                elif script_player.paused:
                    response = {"status": "paused"}
                else:
                    response = {"status": "playing"}
            else:
                response = {"status": "error", "message": "Unknown action"}
                
            self._set_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))
            return
        
        # 기본 GET 요청 처리
        self._set_headers()
        self.wfile.write(json.dumps({"status": "ready"}).encode("utf-8"))

    def do_POST(self):
        if self.path == "/lovespouse":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            params = json.loads(body.decode("utf-8"))

            toy_control(params)
            self._set_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
            return
            
        elif self.path == "/lovespouse/script/load":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            
            try:
                script_data = json.loads(body.decode("utf-8"))
                mode = self.headers.get("X-Toy-Mode", "shake")
                
                # 스크립트 유효성 검사
                if "actions" not in script_data or not isinstance(script_data["actions"], list):
                    self._set_headers()
                    self.wfile.write(json.dumps({
                        "status": "error", 
                        "message": "Invalid script format: missing actions array"
                    }).encode("utf-8"))
                    return
                
                response = load_script(script_data, mode)
                self._set_headers()
                self.wfile.write(json.dumps(response).encode("utf-8"))
                return
                
            except json.JSONDecodeError:
                self._set_headers()
                self.wfile.write(json.dumps({
                    "status": "error", 
                    "message": "Invalid JSON format"
                }).encode("utf-8"))
                return
        
        # 알 수 없는 경로
        self.send_response(404)
        self.end_headers()

# 서버 실행
def run_server(port=8080):
    logging.basicConfig(level=logging.INFO)
    server_address = ("", port)
    httpd = HTTPServer(server_address, RequestHandler)
    logging.info(f"LoveSpouse BLE control server running on port {port}")
    
    # videos 디렉토리 생성 (없는 경우)
    os.makedirs("videos", exist_ok=True)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info("Stopping server")

if __name__ == "__main__":
    run_server()
