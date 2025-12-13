# app.py - MeArm 最終完整版 (含緊急停止功能)
from flask import Flask, render_template, request, jsonify
import pigpio
import time
import socket
import config

try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False

app = Flask(__name__)

# --- 初始化 ---
pi = pigpio.pi()
if not pi.connected:
    print("❌ pigpio 未連線")

current_pos = {
    'base': config.HOME_POS['base'],
    'shoulder': config.HOME_POS['shoulder'],
    'elbow': config.HOME_POS['elbow'],
    'gripper': config.GRIPPER_OPEN
}

PINS = {
    'base': config.PIN_BASE, 'shoulder': config.PIN_SHOULDER,
    'elbow': config.PIN_ELBOW, 'gripper': config.PIN_GRIPPER
}

# [新增] 全局停止旗標
STOP_FLAG = False

# --- 馬達放鬆 ---
def relax_all_motors():
    if pi.connected:
        for p in PINS.values(): pi.set_servo_pulsewidth(p, 0)
    print("😴 馬達已放鬆")

# --- 馬達控制 (含緊急停止檢查) ---
def move_servo(axis, target_val, speed_mode='auto'):
    global current_pos, STOP_FLAG
    
    # [檢查點 1] 如果已經按下停止鍵，直接不執行
    if STOP_FLAG: return

    # 安全限位
    if axis == 'elbow':
        if target_val < 1700: target_val = 1700
        if target_val > 2400: target_val = 2400 
    elif axis == 'shoulder':
        if target_val < 800: target_val = 800
        if target_val > 2400: target_val = 2400
    elif axis == 'base':
        if target_val < 500: target_val = 500
        if target_val > 2500: target_val = 2500
    elif axis == 'gripper':
        if target_val < 500: target_val = 500
        if target_val > 2500: target_val = 2500

    if pi.connected:
        # 瞬間到位模式
        if axis == 'gripper' or speed_mode == 'fast':
            pi.set_servo_pulsewidth(PINS[axis], target_val)
            current_pos[axis] = target_val
            return

        # 平滑移動模式
        start_val = current_pos[axis]
        step = 10 if axis == 'base' else 30
        delay = 0.005 if axis == 'base' else 0.004
        if speed_mode == 'smooth': step = 20; delay = 0.005

        if start_val > target_val: step = -step
        current = start_val
        
        # 迴圈移動
        while abs(current - target_val) > abs(step):
            # [檢查點 2] 移動中隨時檢查是否要緊急停止
            if STOP_FLAG:
                print(f"⛔ {axis} 移動被強制中斷！")
                relax_all_motors() # 立刻放鬆
                return # 跳出函式

            current += step
            pi.set_servo_pulsewidth(PINS[axis], current)
            time.sleep(delay)
            
        # 最後到位
        if not STOP_FLAG:
            pi.set_servo_pulsewidth(PINS[axis], target_val)
            current_pos[axis] = target_val

# --- 核心搬運 ---
def perform_stacking(target_hover, target_down):
    global STOP_FLAG
    if STOP_FLAG: return # 開頭檢查

    # 1. 抓取
    move_servo('gripper', config.GRIPPER_OPEN)
    move_servo('shoulder', config.HOME_POS['shoulder'])
    time.sleep(0.3)
    move_servo('base', config.PICKUP_HOVER['base'])
    time.sleep(0.5)
    
    if STOP_FLAG: return # 步驟間檢查

    move_servo('shoulder', config.PICKUP_HOVER['shoulder'])
    move_servo('elbow', config.PICKUP_DOWN['elbow'] + 30) # 過衝
    time.sleep(0.2)
    move_servo('elbow', config.PICKUP_DOWN['elbow'])
    time.sleep(0.3)
    
    move_servo('shoulder', config.PICKUP_DOWN['shoulder'])
    time.sleep(0.5)
    print("    ✊ 夾取")
    move_servo('gripper', config.GRIPPER_CLOSE)
    time.sleep(0.5)
    
    if STOP_FLAG: return # 步驟間檢查

    # 2. 搬運
    print(f"    🔼 抬高")
    move_servo('shoulder', 1500)
    time.sleep(0.5)
    print("    🔄 旋轉")
    move_servo('base', target_hover['base'])
    time.sleep(0.8)
    print("    💪 伸出")
    move_servo('elbow', target_hover['elbow'])
    time.sleep(0.5)
    
    if STOP_FLAG: return

    # 3. 放置
    print("    🎯 強制校正")
    move_servo('base', target_down['base'])
    move_servo('elbow', target_down['elbow'])
    time.sleep(0.3)

    print("    ⬇️ 放置")
    move_servo('shoulder', target_down['shoulder'])
    time.sleep(0.5)
    move_servo('gripper', config.GRIPPER_OPEN)
    time.sleep(0.5)
    
    if STOP_FLAG: return

    # 4. 撤退
    move_servo('shoulder', 1500)
    time.sleep(0.3)
    move_servo('elbow', 1700)
    time.sleep(0.3)
    move_servo('base', config.HOME_POS['base'])
    time.sleep(0.5)

# --- 路由 ---
@app.route('/')
def index():
    return render_template('index.html')

# [新增] 緊急停止路由
@app.route('/stop', methods=['POST'])
def emergency_stop():
    global STOP_FLAG
    STOP_FLAG = True # 舉起紅旗
    print("\n🚨🚨🚨 收到緊急停止指令！ 🚨🚨🚨")
    relax_all_motors() # 放鬆馬達
    return jsonify({"status": "stopped"})

@app.route('/move', methods=['POST'])
def manual_move():
    global STOP_FLAG
    STOP_FLAG = False # 手動移動時，重置停止旗標
    d = request.json
    axis, step = d.get('axis'), int(d.get('step'))
    if axis in current_pos:
        move_servo(axis, current_pos[axis] + step, 'smooth')
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

@app.route('/set_gripper', methods=['POST'])
def set_gripper():
    global STOP_FLAG
    STOP_FLAG = False
    act = request.json.get('action')
    val = config.GRIPPER_CLOSE if act == 'close' else config.GRIPPER_OPEN
    move_servo('gripper', val)
    return jsonify({"status": "success"})

@app.route('/home', methods=['POST'])
def go_home():
    global STOP_FLAG
    STOP_FLAG = False # 歸位時重置
    print("🏠 執行歸位")
    move_servo('gripper', config.GRIPPER_OPEN)
    time.sleep(0.2); move_servo('shoulder', config.HOME_POS['shoulder'])
    time.sleep(0.2); move_servo('elbow', config.HOME_POS['elbow'])
    time.sleep(0.2); move_servo('base', config.HOME_POS['base'])
    return jsonify({"status": "success"})

@app.route('/auto_stack', methods=['POST'])
def auto_stack():
    global STOP_FLAG
    STOP_FLAG = False # 任務開始，降下紅旗
    print("🤖 [單一模式] 啟動")
    try:
        perform_stacking(config.PLACE_HOVER, config.PLACE_DOWN)
        relax_all_motors()
        if STOP_FLAG: return jsonify({"status": "stopped"})
        return jsonify({"status": "completed"})
    except Exception as e:
        return jsonify({"status": "error"}), 500

@app.route('/build_pyramid', methods=['POST'])
def build_pyramid():
    global STOP_FLAG
    STOP_FLAG = False # 任務開始，降下紅旗
    
    shape_type = request.json.get('shape_type', 'pyramid')
    if shape_type == 'tower': target_list = config.SHAPE_TOWER_2
    elif shape_type == 'tower3': target_list = config.SHAPE_TOWER_3
    elif shape_type == 'side': target_list = config.SHAPE_PYRAMID_SIDE
    else: target_list = config.PYRAMID_POSITIONS

    try:
        for i, target in enumerate(target_list):
            if STOP_FLAG:
                print("⛔ 任務已強制終止")
                break # 跳出迴圈

            block_num = i + 1
            print(f"\n=== 第 {block_num} 顆：{target['name']} ===")
            
            if block_num > 1:
                print("⏳ 等待補貨 (4秒)...")
                # 分段等待，以便隨時響應停止
                for _ in range(40): # 40 * 0.1s = 4s
                    if STOP_FLAG: break
                    time.sleep(0.1)
            
            if STOP_FLAG: break

            perform_stacking(target['hover'], target['down'])
            print(f"✅ 第 {block_num} 顆完成")

        relax_all_motors()
        if STOP_FLAG: return jsonify({"status": "stopped"})
        return jsonify({"status": "completed"})
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        relax_all_motors()
        return jsonify({"status": "error"}), 500

if __name__ == '__main__':
    def get_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try: s.connect(('8.8.8.8', 80)); ip = s.getsockname()[0]
        except: ip = '127.0.0.1'
        finally: s.close()
        return ip
    
    host_ip = get_ip()
    url = f"http://{host_ip}:5000"
    print(f"\n🚀 MeArm 啟動 | 網址: {url}")
    
    if HAS_QR:
        qr = qrcode.QRCode(); qr.add_data(url); qr.make(fit=True)
        try: qr.print_ascii(invert=True)
        except: pass

    # 開機歸位
    move_servo('base', config.HOME_POS['base']); time.sleep(0.5)
    move_servo('shoulder', config.HOME_POS['shoulder']); time.sleep(0.5)
    move_servo('elbow', config.HOME_POS['elbow']); time.sleep(0.5)
    move_servo('gripper', config.GRIPPER_OPEN)

    app.run(host='0.0.0.0', port=5000, debug=True)
