# app.py
from flask import Flask, render_template, request, jsonify
import time
import shapes  # 匯入剛剛寫的圖形資料庫
from arm_driver import MeArm  # 匯入您原本的驅動程式 (請確保它在同一個資料夾)

app = Flask(__name__)

# --- 初始化手臂 ---
try:
    bot = MeArm()
    print("✅ 機械手臂連線成功！")
except:
    print("⚠️ 手臂未連線")
    bot = None

# --- 設定區 ---
FEEDER_POS = [0, 165, 25]  # 取料點座標 [x, y, z] 
SAFE_HEIGHT = 100          # 移動時的安全高度 (避免撞倒積木)

def move_block(target_x, target_y, target_z):
    """ 執行一次搬運任務：取料 -> 放置 """
    if not bot: return

    print(f"🚜 搬運積木到: ({target_x}, {target_y}, {target_z})")

    # 1. --- 去取料點 ---
     bot.move_to_safe(SAFE_HEIGHT)       # 抬高
     bot.move_to(*FEEDER_POS)            # 到取料點上方
     bot.move_gripper(0)                 # 張開
     bot.move_to(FEEDER_POS[0], FEEDER_POS[1], 5) # 下降取料
     bot.move_gripper(100)               # 夾緊
     time.sleep(0.5)
     bot.move_to(*FEEDER_POS)            # 抬起 (回到原本高度)

    # 2. --- 去放置點 ---
     bot.move_to_safe(SAFE_HEIGHT)       # 抬高過山車
     bot.move_to(target_x, target_y, target_z + 20) # 到目標正上方
     bot.move_to(target_x, target_y, target_z)      # 輕輕放下
     bot.move_gripper(0)                 # 張開
     bot.move_to(target_x, target_y, target_z + 30) # 抬高離開

    # (註：這裡我把實際動作註解掉了，您需要把您原本寫好的 move 函式整合進來)
    # 簡單模擬動作：
    print("   -> 假裝手臂在動... (請把註解打開並換成您的程式碼)")
    time.sleep(1) # 模擬動作時間

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_build', methods=['POST'])
def start_build():
    data = request.json
    shape_name = data.get('shape_name')
    print(f"📲 收到手機指令：建造 {shape_name}")

    # 1. 取得座標清單
    coords_list = shapes.get_coords(shape_name)
    
    if not coords_list:
        return jsonify({"status": "error", "message": "找不到這個形狀的資料"})

    # 2. 開始建造 (迴圈)
    # 這裡可以做成非同步(Thread)，但為了簡單，先做同步(網頁會轉圈圈直到做完)
    for i, block in enumerate(coords_list):
        print(f"--- 第 {i+1} 塊積木 ---")
        move_block(block['x'], block['y'], block['z'])
        # 提示：在這裡可以加上 '請補充積木' 的暫停，如果只有一個取料口的話

    return jsonify({"status": "success", "message": "建造完成"})

if __name__ == '__main__':
    # 啟動 Web Server，允許區網連線

    app.run(host='0.0.0.0', port=5000, debug=True)

