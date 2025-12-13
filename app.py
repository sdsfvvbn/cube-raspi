# app.py - MeArm 最終整合版 (依據您的時間參數 + 緊急停止功能)
from flask import Flask, render_template, request, jsonify
import pigpio
import time
import socket
import config  # 讀取 config.py

try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False

app = Flask(__name__)

# ==========================================
# 1. 硬體初始化
# ==========================================
pi = pigpio.pi()
if not pi.connected:
    print("❌ 錯誤：無法連接 pigpio daemon")
else:
    print("✅ pigpio 連線成功")

current_pos = {
    'base': config.HOME_POS['base'],
    'shoulder': config.HOME_POS['shoulder'],
    'elbow': config.HOME_POS['elbow'],
    'gripper': config.GRIPPER_OPEN
}

PINS = {
    'base': config.PIN_BASE,
    'shoulder': config.PIN_SHOULDER,
    'elbow': config.PIN_ELBOW,
    'gripper': config.PIN_GRIPPER
}

# [重要] 全局停止旗標
STOP_FLAG = False

# ==========================================
# 2. 輔助函式
# ==========================================
def relax_all_motors():
    """放鬆所有馬達"""
    if pi.connected:
        for p in PINS.values():
            pi.set_servo_pulsewidth(p, 0)
    print("😴 馬達已放鬆")

def move_servo(axis, target_val, speed_mode='auto'):
    """
    移動馬達 (整合您的速度設定 + 緊急停止檢查)
    """
    global current_pos, STOP_FLAG
    
    # [檢查 1] 若已按下停止，直接跳出
    if STOP_FLAG: return

    # --- 安全限位 ---
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
        # 瞬間到位模式 (夾爪或指定快速)
        if axis == 'gripper' or speed_mode == 'fast':
            pi.set_servo_pulsewidth(PINS[axis], target_val)
            current_pos[axis] = target_val
            return

        # 平滑移動模式
        start_val = current_pos[axis]
        
        # [依據您的設定：統一快速]
        step = 30      # 您設定的步距
        delay = 0.004  # 您設定的延遲
        
        if speed_mode == 'smooth': 
            step = 20
            delay = 0.005

        if start_val > target_val: 
            step = -step
            
        current = start_val
        
        # 迴圈移動
        while abs(current - target_val) > abs(step):
            # [檢查 2] 移動中隨時檢查緊急停止
            if STOP_FLAG:
                print(f"⛔ {axis} 移動被強制中斷！")
                relax_all_motors()
                return

            current += step
            pi.set_servo_pulsewidth(PINS[axis], current)
            time.sleep(delay)
            
        # 最後到位
        if not STOP_FLAG:
            pi.set_servo_pulsewidth(PINS[axis], target_val)
            current_pos[axis] = target_val

# ==========================================
# 3. 核心搬運邏輯 (使用您的時間參數)
# ==========================================
def perform_stacking(target_hover, target_down):
    global STOP_FLAG
    if STOP_FLAG: return

    # --- 1. 歸位 & 去供料區 ---
    move_servo('gripper', config.GRIPPER_OPEN)
    move_servo('shoulder', config.HOME_POS['shoulder'])
    time.sleep(1) # 您設定的時間
    
    move_servo('base', config.PICKUP_HOVER['base']) 
    time.sleep(1) # 您設定的時間
    
    if STOP_FLAG: return

    move_servo('shoulder', config.PICKUP_HOVER['shoulder'])
    move_servo('elbow', config.PICKUP_HOVER['elbow'])
    time.sleep(1) # 您設定的時間
    
    # 下降抓取 (無過衝)
    move_servo('elbow', config.PICKUP_DOWN['elbow'])
    move_servo('shoulder', config.PICKUP_DOWN['shoulder']) 
    time.sleep(1) # 您設定的時間
    
    if STOP_FLAG: return

    # 夾取
    print("    ✊ 夾取")
    move_servo('gripper', config.GRIPPER_CLOSE)
    time.sleep(1) # 您設定的時間
    
    # --- 2. 搬運 ---
    print("    🔼 原地抬高")
    move_servo('shoulder', target_hover['shoulder']) 
    time.sleep(1) # 您設定的時間
    
    if STOP_FLAG: return

    print("    🔄 旋轉")
    move_servo('base', target_hover['base'])
    time.sleep(1.5) # 您設定的時間 (較長)
    
    print("    💪 伸出")
    move_servo('elbow', target_down['elbow']) 
    time.sleep(2)   # 您設定的時間 (最長)

    if STOP_FLAG: return

    # --- 3. 放置 ---
    print("    ⬇️ 放置")
    move_servo('shoulder', target_down['shoulder']) 
    time.sleep(1.5) # 您設定的時間
    
    print("    👐 鬆開")
    move_servo('gripper', config.GRIPPER_OPEN)
    time.sleep(1) # 您設定的時間
    
    if STOP_FLAG: return

    # --- 4. 撤退 ---
    print("    🏠 撤退")
    move_servo('shoulder', 1500)
    time.sleep(1) # 您設定的時間
    move_servo('elbow', 1750)
    time.sleep(1) # 您設定的時間
    move_servo('base', config.HOME_POS['base'])
    time.sleep(1) # 您設定的時間

# ==========================================
# 4. Web 路由
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

# [緊急停止]
@app.route('/stop', methods=['POST'])
def emergency_stop():
    global STOP_FLAG
    STOP_FLAG = True # 舉起紅旗
    print("\n🚨🚨🚨 收到緊急停止指令！ 🚨🚨🚨")
    relax_all_motors()
    return jsonify({"status": "stopped"})

@app.route('/move', methods=['POST'])
def manual_move():
    global STOP_FLAG
    STOP_FLAG = False # 手動移動重置旗標
    data = request.json
    axis = data.get('axis')
    step = int(data.get('step'))
    if axis in current_pos:
        new_val = current_pos[axis] + step
        move_servo(axis, new_val, speed_mode='smooth')
        return jsonify({"status": "success", "val": new_val})
    return jsonify({"status": "error"}), 400

@app.route('/set_gripper', methods=['POST'])
def set_gripper():
    global STOP_FLAG
    STOP_FLAG = False
    data = request.json
    action = data.get('action')
    target_val = config.GRIPPER_CLOSE if action == 'close' else config.GRIPPER_OPEN
    move_servo('gripper', target_val)
    return jsonify({"status": "success"})

@app.route('/home', methods=['POST'])
def go_home():
    global STOP_FLAG
    STOP_FLAG = False # 歸位重置旗標
    print("🏠 執行歸位")
    move_servo('gripper', config.GRIPPER_OPEN)
    time.sleep(0.2)
    move_servo('shoulder', config.HOME_POS['shoulder'])
    time.sleep(0.2)
    move_servo('elbow', config.HOME_POS['elbow'])
    time.sleep(0.2)
    move_servo('base', config.HOME_POS['base'])
    return jsonify({"status": "success"})

@app.route('/auto_stack', methods=['POST'])
def auto_stack():
    global STOP_FLAG
    STOP_FLAG = False # 任務開始
    print("🤖 [單一模式] 啟動")
    try:
        perform_stacking(config.PLACE_HOVER, config.PLACE_DOWN)
        relax_all_motors()
        if STOP_FLAG: return jsonify({"status": "stopped"})
        return jsonify({"status": "completed"})
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/build_pyramid', methods=['POST'])
def build_pyramid():
    global STOP_FLAG
    STOP_FLAG = False # 任務開始
    
    # 支援多種形狀
    shape_type = request.json.get('shape_type', 'pyramid')
    
    if shape_type == 'tower':
        print("🗼 [雙層塔] 啟動")
        target_list = config.SHAPE_TOWER_2
    elif shape_type == 'tower3':
        print("🏙️ [摩天大樓] 啟動")
        target_list = config.SHAPE_TOWER_3
    elif shape_type == 'side':
        print("🔺 [橫向金字塔] 啟動")
        target_list = config.SHAPE_PYRAMID_SIDE
    else:
        print("🏗️ [金字塔] 啟動")
        target_list = config.PYRAMID_POSITIONS

    try:
        for i, target in enumerate(target_list):
            if STOP_FLAG: 
                print("⛔ 任務中斷")
                break

            block_num = i + 1
            print(f"\n=== 第 {block_num} 顆：{target['name']} ===")
            
            # 補貨等待 (您設定為 2 秒)
            if block_num > 1:
                print("⏳ 等待補貨 (2秒)...")
                for _ in range(20): # 20 * 0.1s = 2s
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

# ==========================================
# 5. 主程式啟動
# ==========================================
if __name__ == '__main__':
    def get_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try: s.connect(('8.8.8.8', 80)); ip = s.getsockname()[0]
        except: ip = '127.0.0.1'
        finally: s.close()
        return ip

    host_ip = get_ip()
    url = f"http://{host_ip}:5000"

    print("\n" + "="*45)
    print("🚀 MeArm 系統啟動 (自訂時間版)")
    print("="*45)

    try:
        # 開機歸位
        print("正在歸位...")
        move_servo('base', config.HOME_POS['base'])
        time.sleep(1) 
        move_servo('shoulder', config.HOME_POS['shoulder'])
        time.sleep(1) 
        move_servo('elbow', config.HOME_POS['elbow'])
        time.sleep(1) 
        move_servo('gripper', config.GRIPPER_OPEN)
        
        print(f"\n✅ 連線網址: {url}")
        
        if HAS_QR:
            qr = qrcode.QRCode(); qr.add_data(url); qr.make(fit=True)
            try: qr.print_ascii(invert=True)
            except: qr.print_ascii()
        
        app.run(host='0.0.0.0', port=5000, debug=True)

    except KeyboardInterrupt:
        print("\n⛔ 停止，放鬆馬達...")
        relax_all_motors()
        pi.stop()
    finally:
        if pi.connected: pi.stop()
