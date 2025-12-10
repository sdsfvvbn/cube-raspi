# app.py - MeArm 機械手臂控制 (俐落快節奏版)
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

# ==========================================
# 2. 馬達控制核心 (快節奏平滑版)
# ==========================================
def move_servo(axis, target_val, speed_mode='smooth'):
    """
    speed_mode: 'smooth' (快速平滑), 'fast' (瞬間到位)
    """
    global current_pos
    
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

    # --- 執行移動 ---
    if pi.connected:
        
        # 情況 1: 夾爪或是指定要快 -> 瞬間到位
        if axis == 'gripper' or speed_mode == 'fast':
            pi.set_servo_pulsewidth(PINS[axis], target_val)
            current_pos[axis] = target_val
            return

        # 情況 2: 平滑移動 (已調快速度)
        start_val = current_pos[axis]
        
        # [速度設定區] -------------------------
        step = 30      # 改成 30 (原本 10) -> 跨步變大
        delay = 0.004  # 改成 0.004 (原本 0.008) -> 頻率變快
        # ------------------------------------
        
        if start_val > target_val:
            step = -step # 往回跑
            
        current = start_val
        # 迴圈移動
        while abs(current - target_val) > abs(step):
            current += step
            pi.set_servo_pulsewidth(PINS[axis], current)
            time.sleep(delay) 
            
        # 確保最後到位
        pi.set_servo_pulsewidth(PINS[axis], target_val)
        current_pos[axis] = target_val

def relax_all_motors():
    if pi.connected:
        for p in PINS.values(): pi.set_servo_pulsewidth(p, 0)

# ==========================================
# 3. 核心搬運邏輯
# ==========================================
def perform_stacking(target_hover, target_down):
    # 因為 move_servo 變快了，這裡的 sleep 可以稍微縮短，讓整體流程更順
    
    # 1. 歸位 & 去供料區
    move_servo('gripper', config.GRIPPER_OPEN)
    move_servo('shoulder', config.HOME_POS['shoulder'])
    time.sleep(0.3)
    
    move_servo('base', config.PICKUP_HOVER['base']) 
    time.sleep(0.3)
    
    move_servo('shoulder', config.PICKUP_HOVER['shoulder'])
    move_servo('elbow', config.PICKUP_HOVER['elbow'])
    time.sleep(0.5)
    
    # 下降抓取
    move_servo('elbow', config.PICKUP_DOWN['elbow'])
    move_servo('shoulder', config.PICKUP_DOWN['shoulder']) 
    time.sleep(0.5) # 等穩
    
    # 夾取
    print(" 夾取")
    move_servo('gripper', config.GRIPPER_CLOSE)
    time.sleep(0.5)
    
    # 2. 搬運
    print("    🔼 原地抬高")
    move_servo('shoulder', 1500) 
    time.sleep(0.3)
    
    print("旋轉")
    move_servo('base', target_hover['base'])
    time.sleep(0.5)
    
    print("伸出")
    move_servo('elbow', target_hover['elbow']) 
    time.sleep(0.3)

    # 3. 放置
    print("放置")
    move_servo('shoulder', target_down['shoulder']) 
    time.sleep(0.5)
    
    print("鬆開")
    move_servo('gripper', config.GRIPPER_OPEN)
    time.sleep(0.5)
    
    # 4. 撤退
    print("撤退")
    move_servo('elbow', 1700)
    time.sleep(0.3)
    move_servo('shoulder', 1500)
    time.sleep(0.3)
    move_servo('base', config.HOME_POS['base'])
    time.sleep(0.5)

# ==========================================
# 4. Web 路由
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
        move_servo(axis, new_val, speed_mode='smooth')
        return jsonify({"status": "success", "val": new_val})
    return jsonify({"status": "error"}), 400

@app.route('/set_gripper', methods=['POST'])
def set_gripper():
    data = request.json
    action = data.get('action')
    target_val = config.GRIPPER_CLOSE if action == 'close' else config.GRIPPER_OPEN
    move_servo('gripper', target_val)
    return jsonify({"status": "success"})

@app.route('/home', methods=['POST'])
def go_home():
    move_servo('gripper', config.GRIPPER_OPEN)
    time.sleep(1)
    move_servo('shoulder', config.HOME_POS['shoulder'])
    time.sleep(1)
    move_servo('elbow', config.HOME_POS['elbow'])
    time.sleep(1)
    move_servo('base', config.HOME_POS['base'])
    return jsonify({"status": "success"})

@app.route('/auto_stack', methods=['POST'])
def auto_stack():
    print("🤖 [Auto] 單一堆疊")
    try:
        perform_stacking(config.PLACE_HOVER, config.PLACE_DOWN)
        relax_all_motors()
        return jsonify({"status": "completed"})
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/build_pyramid', methods=['POST'])
def build_pyramid():
    print("🏗️ [Auto] 金字塔連續模式")
    try:
        for i, target in enumerate(config.PYRAMID_POSITIONS):
            block_num = i + 1
            print(f"\n=== 第 {block_num} 顆：{target['name']} ===")
            
            if block_num > 1:
                print("⏳ 等待補貨 (4秒)...")
                time.sleep(4)
            
            perform_stacking(target['hover'], target['down'])
            print(f"✅ 第 {block_num} 顆完成")

        print("🎉 金字塔完成")
        relax_all_motors()
        return jsonify({"status": "completed"})
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        relax_all_motors()
        return jsonify({"status": "error", "message": str(e)}), 500

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
    print("🚀 MeArm 系統啟動 (快節奏版)")
    print("="*45)

    try:
        # 開機歸位
        print("正在緩慢歸位...")
        move_servo('base', config.HOME_POS['base'])
        time.sleep(0.5) 
        move_servo('shoulder', config.HOME_POS['shoulder'])
        time.sleep(0.5) 
        move_servo('elbow', config.HOME_POS['elbow'])
        time.sleep(0.5) 
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
