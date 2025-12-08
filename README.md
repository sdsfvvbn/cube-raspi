# 基於樹莓派的 IoT MeArm 積木自動堆疊機器人

# (IoT Web-Controlled MeArm Robot for Block Stacking)

## 📖 專題概述 (Project Overview)

本專題實作了一個基於樹莓派 (Raspberry Pi) 的 4自由度 (4-DOF) MeArm 機械手臂控制系統。專題的核心目標是讓機械手臂能夠透過 Web 介面接收指令，並依照預先寫好的程式邏輯，**自動將木頭積木堆疊成指定的形狀**（如金字塔、城牆）。

此外，為了確保抓取的精準度，系統內建了\*\*「手動測試模式」\*\*，允許開發者透過指令精準控制手臂的前後、左右與上下移動，以進行座標校正。

### 🌟 核心功能

  * **自動堆疊 (Auto Stacking):** 使用者只需在手機網頁上選擇圖形，手臂即會自動執行一連串複雜動作完成堆疊。
  * **手動測試校正 (Manual Testing):** 提供指令列工具，可控制手臂「前後左右」微調，用於尋找最佳抓取點。
  * **Web 控制介面:** 使用 Python Flask 架設伺服器，讓手機或電腦在同一個 Wi-Fi 下即可控制。
  * **平滑運動控制:** 針對 SG90 馬達特性優化了 PWM 訊號，包含「夾爪加速」與「手臂穩速」功能，防止抖動。

-----

## 🛠️ 硬體需求 (Hardware Requirements)

本專題使用以下硬體組件：

  * **控制器:** Raspberry Pi (4)
  * **機械手臂:** MeArm 
  * **致動器:** SG90 伺服馬達 x 4 (底座、左臂、右臂、夾爪)
  * **電源供應 :**
      * 樹莓派：使用 5V/3A 電源。
      * 馬達：**獨立供電** (使用 4顆 AA 電池盒)。
  * **其他:** 麵包板、杜邦線、2x2cm 木頭正方體積木。
![S__99663880](https://github.com/user-attachments/assets/799c9f4b-1fbe-4214-945e-1a0777a90165)

-----

## ⚡ 電路連接圖 (Circuit Diagram)

**警告:** 絕對不可將馬達電源直接接在樹莓派的 5V 腳位，電流過大會燒毀主機板。

### 接線對照表

| 馬達部位 | GPIO 腳位 (BCM編號) | 實體腳位 (Physical) | 功能描述 |
| :--- | :--- | :--- | :--- |
| **底座 (Base)** | GPIO 19 | Pin 35 | 控制左右旋轉 |
| **肩膀 (Shoulder)** | GPIO 13 | Pin 33 | 控制前後/上下 |
| **手肘 (Elbow)** | GPIO 12 | Pin 32 | 控制前後/上下 |
| **夾爪 (Gripper)** | GPIO 18 | Pin 12 | 控制夾取/放開 |

![12DE9A6C-1833-4292-89D1-277F71979283](https://github.com/user-attachments/assets/e76ca700-0b64-41b7-80c8-070696d08184)



-----

## 💻 軟體架構與安裝 (Software & Installation)

### 1\. 系統環境準備

我們使用 `pigpio` 函式庫來產生高精度的 PWM 訊號，以避免馬達抖動。

```bash
# 更新系統
sudo apt-get update

# 安裝必要套件
sudo apt-get install pigpio python3-pigpio python3-flask

# 啟動 pigpio 守護行程 (Daemon)
sudo systemctl start pigpiod
sudo systemctl enable pigpiod
```

### 2\. 取得專案程式碼

```bash
git clone https://github.com/您的帳號/您的專案名稱.git
cd 您的專案名稱
```

### 3\. 專案檔案結構

  * `app.py`: Web 伺服器主程式 (負責自動堆疊邏輯)。
  * `final_control.py`: **手動測試程式** (負責前後左右校正)。
  * `config.py`: 存放校正後的 PWM 數值。
  * `shapes.py`: 定義堆疊形狀的座標資料庫。

-----

## 🚀 使用教學 (How to Run)

本系統分為兩個階段：先進行「手動測試校正」，確認位置無誤後，再執行「自動堆疊」。

### 階段一：手動測試與校正 (Testing Mode)

在讓手臂自動跑之前，我們必須確認它能準確到達指定位置。請執行測試程式：

```bash
python3 final_control.py
```

**操作說明：**
程式會顯示選單，選擇馬達後，可輸入指令控制方向：

  * **前後控制 (Shoulder/Elbow):** 輸入數值讓手臂前伸或後縮。
  * **左右控制 (Base):** 輸入數值讓底座左轉或右轉。
  * **夾爪測試:** 測試開合速度（極速模式）。

*記錄下「供料區」與「堆疊原點」的 PWM 數值，並填入 `config.py` 中。*

### 階段二：自動堆疊模式 (Auto Stacking Mode)

校正完成後，啟動 Web 伺服器：

```bash
python3 app.py
```

1.  確認樹莓派 IP 位址 (輸入 `hostname -I` 查詢)。
2.  手機連接同一個 Wi-Fi，瀏覽器輸入 `http://[樹莓派IP]:5000`。
3.  在網頁上選擇圖形（例如：Tower），按下 **"Start Build"**。
4.  手臂將依照預寫好的程式碼，自動將積木搬運並堆疊成形。

-----

## 🎥 成果演示 (Demo Video)

[在此插入您的 YouTube 影片連結或 GIF 動圖]

**影片內容說明：**

1.  展示手機介面操作。
2.  展示機械手臂從供料區夾取積木。
3.  展示手臂自動完成「金字塔」或「高塔」堆疊。

-----

## 🔧 問題排解 (Troubleshooting)

在開發過程中，我們解決了以下挑戰：

1.  **啟動暴衝問題 (Startup Jitter):**
      * *問題:* 程式啟動瞬間，四顆馬達同時通電導致電流過載，手臂會瘋狂抽動。
      * *解法:* 實作了「軟啟動 (Soft Start)」邏輯，讓馬達依序一顆一顆通電，並加入 `time.sleep` 等待電壓回穩。
2.  **夾爪與手臂速度不同步:**
      * *問題:* 夾爪需要快速開合，但手臂需要慢速移動才穩。
      * *解法:* 在程式中實作「自動變速邏輯」，當偵測到控制夾爪時自動切換為高速模式，控制手臂時則維持高扭力的慢速模式。
3.  **地心引力導致手臂下垂:**
      * *問題:* 手臂伸長時因力矩過大而舉不起來（回不去）。
      * *解法:* 優化了 `slow_move` 的步進頻率 (Step/Delay)，並在回程時使用全速指令以提供最大扭力。

-----

## 📚 參考資料 (References)

本專案參考了以下開源資源與文獻：

1.  **Raspberry Pi GPIO Scripting**: [https://www.instructables.com/Raspberry-Pi-Python-scripting-the-GPIO/](https://www.instructables.com/Raspberry-Pi-Python-scripting-the-GPIO/)
2.  **IoT Core Kit Examples**: [https://github.com/ARM-software/Cloud-IoT-Core-Kit-Examples](https://github.com/ARM-software/Cloud-IoT-Core-Kit-Examples)
3.  **MeArm Robot Arm Open Source Project**: [https://shop.mearm.com/](https://shop.mearm.com/) (Mechanical structure reference)
4.  **pigpio Python Library**: [http://abyz.me.uk/rpi/pigpio/python.html](http://abyz.me.uk/rpi/pigpio/python.html) (PWM control implementation)


