# app.py - MeArm 機械手臂控制核心 (最終完整版)
from flask import Flask, render_template, request, jsonify
import pigpio
import time
import socket
import config  # 讀取你的 config.py

# 嘗試匯入 QR Code 套件 (沒裝也不會報錯)
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
    print("❌ 錯誤：無法連接 pigpio daemon，請務必先執行 'sudo pigpiod'")
else:
    print("✅ pigpio 連線成功")

# 記錄目前位置 (初始化為 config 的預設值)
current_pos = {
    'base': config.HOME_POS['base'],
    'shoulder': config.HOME_POS['shoulder'],
    'elbow': config.HOME_POS['elbow'],
    'gripper': config.GRIPPER_OPEN
}

# 腳位對應表
PINS = {
    'base': config.PIN_BASE,
    'shoulder': config.PIN_SHOULDER,
    'elbow': config.PIN_ELBOW,
    'gripper': config.PIN_GRIPPER
}

# ==========================================
# 2. 馬達控制核心 (含安全限位)
# ==========================================
def move_servo(axis, val):
    """
    移動馬達並寫入 PWM，包含針對你機器的安全限位保護
    """
    global current_pos
    
    # --- 安全限位保護 (Safety Guards) ---
    
    if axis == 'elbow':
        # 你的放置點是 2300，所以我們上限開到 2400 以確保能到達
        if val < 1700: 
            print(f"⚠️ Elbow 修正: {val} -> 1700 (後縮極限)")
            val = 1700
        if val > 2400: val = 2400 # 開放一點空間給 2300

    elif axis == 'shoulder':
        # 你的抓取點需要降到 1000，所以下限要開低一點
        if val < 800: val = 800
        if val > 2400: val = 2400

    elif axis == 'base':
        # 底座範圍通常較大
        if val < 500: val = 500
        if val > 2500: val = 2500

    elif axis == 'gripper':
        # 夾爪保護
        if val < 500: val = 500
        if val > 2500: val = 2500

    # --- 執行移動 ---
    if pi.connected:
        pi.set_servo_pulsewidth(PINS[axis], val)
    
    # --- 更新記憶 ---
    current_pos[axis] = val

# ==========================================
# 3. Web 路由設定
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

# --- 功能 A: 手機手動微調 (前後左右) ---
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

# --- 功能 B: 夾爪一鍵到位 (開/合) ---
@app.route('/set_gripper', methods=['POST'])
def set_gripper():
    data = request.json
    action = data.get('action') # 'open' or 'close'
    
    target_val = config.GRIPPER_OPEN
    if action == 'close':
        target_val = config.GRIPPER_CLOSE # 讀取你的 Sweet Spot
        
    print(f"👐 夾爪執行: {action} ({target_val})")
    move_servo('gripper', target_val)
    return jsonify({"status": "success"})

# --- 功能 C: 一鍵致中 (歸位) ---
@app.route('/home', methods=['POST'])
def go_home():
    print("🏠 執行手動歸位...")
    # 安全順序：先鬆開 -> 抬手 -> 收手 -> 轉底座
    move_servo('gripper', config.GRIPPER_OPEN)
    time.sleep(0.5)
    move_servo('shoulder', config.HOME_POS['shoulder'])
    time.sleep(0.5)
    move_servo('elbow', config.HOME_POS['elbow'])
    time.sleep(0.5)
    move_servo('base', config.HOME_POS['base'])
    return jsonify({"status": "success"})

# --- 功能 D: 自動堆疊 (Lift-then-Turn 安全邏輯) ---
@app.route('/auto_stack', methods=['POST'])
def auto_stack():
    print("🤖 [Auto] 開始自動堆疊流程...")
    
    try:
        # === 步驟 1: 安全歸位 ===
        print(" -> 1. 歸位準備")
        move_servo('gripper', config.GRIPPER_OPEN)
        move_servo('shoulder', config.HOME_POS['shoulder']) # 先抬高！
        time.sleep(1)
        move_servo('elbow', config.HOME_POS['elbow'])
        time.sleep(0.8)
        move_servo('base', config.HOME_POS['base'])         # 最後轉正
        time.sleep(1)
        
        # === 步驟 2: 去供料區 (Pickup) ===
        print(" -> 2. 前往供料區")
        
        # A. 轉向 (手是舉高的，安全)
        move_servo('base', config.PICKUP_HOVER['base']) 
        time.sleep(1.5)
        
        # B. 伸出手臂 (Hover)
        move_servo('shoulder', config.PICKUP_HOVER['shoulder'])
        move_servo('elbow', config.PICKUP_HOVER['elbow'])
        time.sleep(1.5)
        
        # C. 下降 (Down)
        print("    下降抓取...")
        move_servo('elbow', config.PICKUP_DOWN['elbow'])
        time.sleep(0.5)
        move_servo('shoulder', config.PICKUP_DOWN['shoulder']) # 降到 1000
        time.sleep(1.2) # 等穩一點
        
        # D. 夾取
        print("    夾取！")
        move_servo('gripper', config.GRIPPER_CLOSE)
        time.sleep(1)
        
        # === 步驟 3: 搬運 (關鍵：先抬高，再轉向) ===
        print(" -> 3. 搬運中...")
        
        # A. 【原地抬高】 (Lift) - 這是最重要的安全動作
        print("    原地抬高 Shoulder...")
        move_servo('shoulder', 1500) 
        time.sleep(1)
        
        # B. 【空中旋轉】 (Turn)
        print("    底座旋轉...")
        move_servo('base', config.PLACE_HOVER['base'])
        time.sleep(1.5)
        
        # C. 【調整手肘】
        move_servo('elbow', config.PLACE_HOVER['elbow']) # 伸到 2300
        time.sleep(1)

        # === 步驟 4: 放置 (Place) ===
        print(" -> 4. 下降放置...")
        move_servo('shoulder', config.PLACE_DOWN['shoulder']) # 降到 1200
        time.sleep(1)
        
        print("    鬆開夾爪")
        move_servo('gripper', config.GRIPPER_OPEN)
        time.sleep(1)
        
        # === 步驟 5: 撤退回家 ===
        print(" -> 5. 任務完成，撤退")
        move_servo('shoulder', 1500) # 先抬高
        time.sleep(1)
        move_servo('elbow', 1700)    # 收手
        time.sleep(0.8)
        move_servo('base', config.HOME_POS['base']) # 回正
        
        return jsonify({"status": "completed"})
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# 4. 主程式啟動點
# ==========================================
if __name__ == '__main__':
    # 取得本機 IP 函式
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
    print("🚀 MeArm 機器人系統啟動")
    print("⚠️  注意：馬達開始歸位，請保持淨空！")
    print("="*45)

    # === 開機緩衝邏輯 (Soft Start) ===
    print("1. 底座歸位 (Base)...")
    move_servo('base', config.HOME_POS['base'])
    time.sleep(2) 
    
    print("2. 肩膀歸位 (Shoulder)...")
    move_servo('shoulder', config.HOME_POS['shoulder'])
    time.sleep(2) 
    
    print("3. 手肘歸位 (Elbow)...")
    move_servo('elbow', config.HOME_POS['elbow'])
    time.sleep(2) 
    
    print("4. 夾爪初始化...")
    move_servo('gripper', config.GRIPPER_OPEN)
    time.sleep(1)
    
    print("\n" + "="*45)
    print(f"✅ Web Server 已啟動！")
    print(f"🔗 連線網址: {url}")
    print("👇 請掃描 QR Code 連線 👇")
    print("="*45)
    
    # 顯示 QR Code
    if HAS_QR:
        qr = qrcode.QRCode()
        qr.add_data(url)
        qr.make(fit=True)
        try: qr.print_ascii(invert=True)
        except: qr.print_ascii()
    
    # 啟動 Flask
    app.run(host='0.0.0.0', port=5000, debug=True)
