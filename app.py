# app.py - MeArm 機械手臂控制 (含自動放鬆功能)
from flask import Flask, render_template, request, jsonify
import pigpio
import time
import socket
import config  # 讀取你的 config.py

# 嘗試匯入 QR Code
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

# 記錄目前位置
current_pos = {
    'base': config.HOME_POS['base'],
    'shoulder': config.HOME_POS['shoulder'],
    'elbow': config.HOME_POS['elbow'],
    'gripper': config.GRIPPER_OPEN
}

# 腳位對應
PINS = {
    'base': config.PIN_BASE,
    'shoulder': config.PIN_SHOULDER,
    'elbow': config.PIN_ELBOW,
    'gripper': config.PIN_GRIPPER
}

# ==========================================
# 2. 馬達控制核心
# ==========================================
def move_servo(axis, val):
    """移動馬達 (含安全限位)"""
    global current_pos
    
    # --- 安全限位 ---
    if axis == 'elbow':
        if val < 1700: val = 1700
        if val > 2400: val = 2400 
    elif axis == 'shoulder':
        if val < 800: val = 800
        if val > 2400: val = 2400
    elif axis == 'base':
        if val < 500: val = 500
        if val > 2500: val = 2500
    elif axis == 'gripper':
        if val < 500: val = 500
        if val > 2500: val = 2500

    # --- 執行移動 ---
    if pi.connected:
        pi.set_servo_pulsewidth(PINS[axis], val)
    
    current_pos[axis] = val

def relax_all_motors():
    """
    [新功能] 放鬆所有馬達
    當任務完成後呼叫此函式，馬達會停止出力 (PWM=0)
    """
    print("😴 任務結束，放鬆所有馬達訊號...")
    if pi.connected:
        pi.set_servo_pulsewidth(PINS['base'], 0)
        pi.set_servo_pulsewidth(PINS['shoulder'], 0)
        pi.set_servo_pulsewidth(PINS['elbow'], 0)
        pi.set_servo_pulsewidth(PINS['gripper'], 0)

# ==========================================
# 3. Web 路由
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/move', methods=['POST'])
def manual_move():
    data = request.json
    axis = data.get('axis')
    step = int(data.get('step'))
    if axis in current_pos:
        new_val = current_pos[axis] + step
        move_servo(axis, new_val)
        return jsonify({"status": "success", "val": new_val})
    return jsonify({"status": "error"}), 400

@app.route('/set_gripper', methods=['POST'])
def set_gripper():
    data = request.json
    action = data.get('action')
    target_val = config.GRIPPER_CLOSE if action == 'close' else config.GRIPPER_OPEN
    print(f"👐 夾爪執行: {action}")
    move_servo('gripper', target_val)
    return jsonify({"status": "success"})

@app.route('/home', methods=['POST'])
def go_home():
    print("🏠 執行歸位...")
    move_servo('gripper', config.GRIPPER_OPEN)
    time.sleep(0.5)
    move_servo('shoulder', config.HOME_POS['shoulder'])
    time.sleep(0.5)
    move_servo('elbow', config.HOME_POS['elbow'])
    time.sleep(0.5)
    move_servo('base', config.HOME_POS['base'])
    return jsonify({"status": "success"})

# --- 功能 D: 自動堆疊 (含最後放鬆) ---
@app.route('/auto_stack', methods=['POST'])
def auto_stack():
    print("🤖 [Auto] 開始自動堆疊...")
    
    try:
        # 1. 歸位
        print(" -> 1. 歸位")
        move_servo('gripper', config.GRIPPER_OPEN)
        move_servo('shoulder', config.HOME_POS['shoulder'])
        time.sleep(1)
        move_servo('elbow', config.HOME_POS['elbow'])
        time.sleep(0.8)
        move_servo('base', config.HOME_POS['base'])
        time.sleep(1)
        
        # 2. 去供料區
        print(" -> 2. 去供料區")
        move_servo('base', config.PICKUP_HOVER['base']) 
        time.sleep(1.5)
        move_servo('shoulder', config.PICKUP_HOVER['shoulder'])
        move_servo('elbow', config.PICKUP_HOVER['elbow'])
        time.sleep(1.5)
        
        # 下降抓取
        move_servo('elbow', config.PICKUP_DOWN['elbow'])
        time.sleep(0.5)
        move_servo('shoulder', config.PICKUP_DOWN['shoulder'])
        time.sleep(1.2)
        move_servo('gripper', config.GRIPPER_CLOSE)
        time.sleep(1)
        
        # 3. 搬運 (先抬再轉)
        print(" -> 3. 搬運中")
        move_servo('shoulder', 1500) # 原地抬高
        time.sleep(1)
        move_servo('base', config.PLACE_HOVER['base']) # 空中旋轉
        time.sleep(1.5)
        move_servo('elbow', config.PLACE_HOVER['elbow'])
        time.sleep(1)

        # 4. 放置
        print(" -> 4. 放置")
        move_servo('shoulder', config.PLACE_DOWN['shoulder'])
        time.sleep(1)
        move_servo('gripper', config.GRIPPER_OPEN)
        time.sleep(1)
        
        # 5. 撤退回家
        print(" -> 5. 回家")
        move_servo('shoulder', 1500)
        time.sleep(1)
        move_servo('elbow', 1700)
        time.sleep(0.8)
        move_servo('base', config.HOME_POS['base'])
        time.sleep(1) # 等它完全停穩
        
        # === [新增功能] 任務完成，放鬆馬達 ===
        relax_all_motors()
        
        return jsonify({"status": "completed"})
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return jsonify({"status": "error"}), 500

# ==========================================
# 4. 主程式啟動
# ==========================================
if __name__ == '__main__':
    def get_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    host_ip = get_ip()
    url = f"http://{host_ip}:5000"

    print("\n" + "="*45)
    print("🚀 系統啟動... (Ctrl+C 可結束)")
    print("="*45)

    try:
        # 開機歸位
        print("正在歸位...")
        move_servo('base', config.HOME_POS['base'])
        time.sleep(1.5) 
        move_servo('shoulder', config.HOME_POS['shoulder'])
        time.sleep(1.5) 
        move_servo('elbow', config.HOME_POS['elbow'])
        time.sleep(1.5) 
        move_servo('gripper', config.GRIPPER_OPEN)
        time.sleep(1)
        
        print(f"\n✅ 連線網址: {url}")
        print("👇 請掃描 QR Code 👇")
        
        if HAS_QR:
            qr = qrcode.QRCode()
            qr.add_data(url)
            qr.make(fit=True)
            try: qr.print_ascii(invert=True)
            except: qr.print_ascii()

        app.run(host='0.0.0.0', port=5000, debug=True)

    except KeyboardInterrupt:
        # 當你按下 Ctrl+C 強制結束時，會執行這裡
        print("\n⛔ 程式停止，正在放鬆馬達...")
        relax_all_motors()
        pi.stop()
        print("✅ 已安全退出")
    finally:
        # 確保任何情況下退出都關閉 pigpio
        if pi.connected:
            pi.stop()
