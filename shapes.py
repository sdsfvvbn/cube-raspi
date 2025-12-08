# shapes.py

# 積木尺寸 (mm)
BLOCK_SIZE = 20
# 堆疊的高度層 (Z軸) -> 第一層是 10mm (或是底板高度), 第二層是 10+25...
LAYER_H = [10, 10 + BLOCK_SIZE, 10 + BLOCK_SIZE*2, 10 + BLOCK_SIZE*3]

# 建造原點 (Base Origin) - 請根據您的底板位置修改
ORIGIN_X = 0    # 前後
ORIGIN_Y = 150  # 左右 (假設在正前方 15cm 處)

def get_coords(name):
    """ 根據名字回傳座標清單 [{'x':0, 'y':150, 'z':10}, ...] """
    
    shapes = {}

    # 1. 🗼 高塔 (最簡單，一直往上疊)
    shapes['tower'] = [
        {'x': ORIGIN_X, 'y': ORIGIN_Y, 'z': LAYER_H[0]}, # 第1層
        {'x': ORIGIN_X, 'y': ORIGIN_Y, 'z': LAYER_H[1]}, # 第2層
        {'x': ORIGIN_X, 'y': ORIGIN_Y, 'z': LAYER_H[2]}, # 第3層
    ]

    # 2. 🧱 城牆 (2層高, 每層3個)
    # 這裡我們稍微錯開一點，或是並排
    shapes['wall'] = [
        # 第一層 (左中右)
        {'x': ORIGIN_X,      'y': ORIGIN_Y,      'z': LAYER_H[0]},
        {'x': ORIGIN_X,      'y': ORIGIN_Y + 30, 'z': LAYER_H[0]},
        {'x': ORIGIN_X,      'y': ORIGIN_Y - 30, 'z': LAYER_H[0]},
        # 第二層 (壓在縫隙上?) 這裡先做簡單堆疊
        {'x': ORIGIN_X,      'y': ORIGIN_Y + 15, 'z': LAYER_H[1]},
        {'x': ORIGIN_X,      'y': ORIGIN_Y - 15, 'z': LAYER_H[1]},
    ]

    # 3. 🔺 金字塔 (底層3個 -> 上層2個 -> 頂層1個)
    shapes['pyramid'] = [
        # Level 1 (底部 2x2 或 3x3，這裡簡化為一排3個)
        {'x': ORIGIN_X, 'y': ORIGIN_Y - 30, 'z': LAYER_H[0]},
        {'x': ORIGIN_X, 'y': ORIGIN_Y,      'z': LAYER_H[0]},
        {'x': ORIGIN_X, 'y': ORIGIN_Y + 30, 'z': LAYER_H[0]},
        # Level 2 (2個，放在縫隙)
        {'x': ORIGIN_X, 'y': ORIGIN_Y - 15, 'z': LAYER_H[1]},
        {'x': ORIGIN_X, 'y': ORIGIN_Y + 15, 'z': LAYER_H[1]},
        # Level 3 (頂端)
        {'x': ORIGIN_X, 'y': ORIGIN_Y,      'z': LAYER_H[2]},
    ]

    # 4. 🪜 階梯
    shapes['stairs'] = [
        {'x': ORIGIN_X,      'y': ORIGIN_Y - 30, 'z': LAYER_H[0]},
        {'x': ORIGIN_X,      'y': ORIGIN_Y,      'z': LAYER_H[0]},
        {'x': ORIGIN_X,      'y': ORIGIN_Y,      'z': LAYER_H[1]}, # 第2階疊在第2個位置
        {'x': ORIGIN_X + 30, 'y': ORIGIN_Y + 30, 'z': LAYER_H[0]}, # 這裡只是示範，您可以自己設計
    ]


    return shapes.get(name, [])
