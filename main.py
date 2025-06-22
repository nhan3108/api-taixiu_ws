from fastapi import FastAPI, HTTPException
import httpx
from collections import Counter
import os
import traceback

app = FastAPI()

# ==== THUẬT TOÁN CHUNG ====
def get_tai_xiu(total):
    return "Tài" if 11 <= total <= 18 else "Xỉu"

# ==== THUẬT TOÁN 1 ====
def du_doan_sunwin_200k(totals_list):
    if len(totals_list) < 4:
        return "Chờ", "Đợi thêm dữ liệu để phân tích cầu."
    last_4 = totals_list[-4:]
    last_3 = totals_list[-3:]
    last_6 = totals_list[-6:]
    last_total = totals_list[-1]
    last_result = get_tai_xiu(last_total)
    if last_4[0] == last_4[2] and last_4[0] == last_4[3] and last_4[0] != last_4[1]:
        return "Tài", f"Cầu đặc biệt {last_4[0]}-{last_4[1]}-{last_4[0]}-{last_4[0]}. Bắt Tài theo công thức."
    if last_3[0] == last_3[2] and last_3[0] != last_3[1]:
        return "Xỉu" if last_result == "Tài" else "Tài", f"Cầu sandwich {last_3}. Bẻ cầu!"
    special_nums = {7, 9, 10}
    count = sum(1 for total in last_3 if total in special_nums)
    if count >= 2:
        return "Xỉu" if last_result == "Tài" else "Tài", f"Xuất hiện cặp {list(special_nums)} trong 3 phiên gần nhất. Bẻ cầu!"
    freq_count = last_6.count(last_total)
    if freq_count >= 3:
        return get_tai_xiu(last_total), f"Số {last_total} lặp lại {freq_count} lần. Bắt theo cầu nghiêng."
    if last_3[0] == last_3[2] or last_3[1] == last_3[2]:
        return "Xỉu" if last_result == "Tài" else "Tài", f"Cầu lặp lại {last_3[1]}-{last_3[2]} hoặc {last_3[0]}-{last_3[2]}. Bẻ cầu 1-1."
    return "Xỉu" if last_result == "Tài" else "Tài", "Không có cầu đặc biệt, dự đoán theo cầu 1-1."

# ==== THUẬT TOÁN 2 VIP ====
def tai_xiu_stats(totals_list):
    types = [get_tai_xiu(t) for t in totals_list]
    count = Counter(types)
    return {
        "tai_count": count["Tài"],
        "xiu_count": count["Xỉu"],
        "most_common_total": Counter(totals_list).most_common(1)[0][0],
        "most_common_type": "Tài" if count["Tài"] >= count["Xỉu"] else "Xỉu"
    }

def du_doan_sunwin_200k_vip(totals_list):
    if len(totals_list) < 4:
        return "Chờ", 0, "Chưa đủ dữ liệu, cần ít nhất 4 phiên."
    last_4 = totals_list[-4:]
    last_3 = totals_list[-3:]
    last_6 = totals_list[-6:]
    last_total = totals_list[-1]
    last_result = get_tai_xiu(last_total)

    def rule_special_pattern():
        if last_4[0] == last_4[2] == last_4[3] and last_4[0] != last_4[1]:
            return "Tài", 85, f"Cầu đặc biệt {last_4}. Bắt Tài theo công thức đặc biệt."
    def rule_sandwich():
        if last_3[0] == last_3[2] and last_3[0] != last_3[1]:
            return "Xỉu" if last_result == "Tài" else "Tài", 83, f"Cầu sandwich {last_3}. Bẻ cầu!"
    def rule_special_numbers():
        special_nums = {7, 9, 10}
        count = sum(1 for t in last_3 if t in special_nums)
        if count >= 2:
            return "Xỉu" if last_result == "Tài" else "Tài", 81, f"Xuất hiện ≥2 số đặc biệt {special_nums} gần nhất. Bẻ cầu!"
    def rule_frequent_repeat():
        freq = last_6.count(last_total)
        if freq >= 3:
            return get_tai_xiu(last_total), 80, f"Số {last_total} lặp lại {freq} lần. Bắt theo nghiêng cầu!"
    def rule_repeat_pattern():
        if last_3[0] == last_3[2] or last_3[1] == last_3[2]:
            return "Xỉu" if last_result == "Tài" else "Tài", 77, f"Cầu lặp dạng {last_3}. Bẻ cầu theo dạng A-B-B hoặc A-B-A."

    rules = [rule_special_pattern, rule_sandwich, rule_special_numbers, rule_frequent_repeat, rule_repeat_pattern]
    for rule in rules:
        result = rule()
        if result:
            return result
    return "Xỉu" if last_result == "Tài" else "Tài", 71, "Không có cầu đặc biệt nào, bẻ cầu mặc định theo 1-1."

# ==== THUẬT TOÁN 4 ====
def phan_tich_cau(lst_ket_qua, lst_tong):
    if lst_ket_qua[-3:] == ["Tài", "Tài", "Tài"]:
        return "Xỉu", 70, "3 Tài liên tiếp"
    elif lst_ket_qua[-3:] == ["Xỉu", "Xỉu", "Xỉu"]:
        return "Tài", 70, "3 Xỉu liên tiếp"
    elif lst_ket_qua[-2:] == ["Tài", "Xỉu"]:
        return "Tài", 60, "Tài-Xỉu gần nhất"
    elif lst_tong[-1] >= 15:
        return "Xỉu", 60, "Tổng ≥15 nên đoán Xỉu"
    elif lst_tong[-1] <= 9:
        return "Tài", 60, "Tổng ≤9 nên đoán Tài"
    else:
        return lst_ket_qua[-1], 55, "Không rõ cầu, giữ nguyên kết quả gần nhất"

# ==== ĐỌC PATTERN ====
def load_pattern_data():
    patterns = []
    file_path = "mau_cau_10000.txt"
    if not os.path.exists(file_path):
        return patterns
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) == 2:
                pattern, result = parts
                pattern = pattern.strip().upper()
                result = result.strip().upper()
                if set(pattern).issubset({"T", "X"}) and result in {"T", "X"}:
                    patterns.append((pattern, result))
    return patterns

def thong_ke_tu_pattern(patterns):
    dung, sai = 0, 0
    for pattern, result in patterns:
        count_t = pattern.count("T")
        count_x = pattern.count("X")
        if count_t > count_x:
            predict = "T"
        elif count_x > count_t:
            predict = "X"
        else:
            predict = "T" if pattern[-1] == "X" else "X"
        if predict == result:
            dung += 1
        else:
            sai += 1
    return dung, sai, dung + sai

def current_pattern(patterns):
    raw = [r for _, r in patterns]
    return "".join(["t" if x == "T" else "x" for x in raw[-15:]])

# ==== API CHÍNH ====
@app.get("/api/taixiu_ws")
async def get_prediction():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("https://wanglinapiws.up.railway.app/api/taixiu?limit=10")
            data = await r.json()

        if not data:
            raise HTTPException(status_code=500, detail="Dữ liệu trả về rỗng từ API nguồn.")

        last = data[-1]
        dice = last.get("dice", [None, None, None])
        phien = last["session"]
        totals = [item["total"] for item in data]
        results = [item["result"] for item in data]

        du_doan, tin_cay, chi_tiet = du_doan_sunwin_200k_vip(totals)
        patterns = load_pattern_data()
        dung, sai, tong = thong_ke_tu_pattern(patterns)
        pattern = current_pattern(patterns)

        return {
            "id": "VanwNhat_V2_DuDoanFull",
            "Phien": phien,
            "Ket_qua": last["result"],
            "Tong": last["total"],
            "Xuc_xac_1": dice[0],
            "Xuc_xac_2": dice[1],
            "Xuc_xac_3": dice[2],
            "Next_phien": phien + 1,
            "Du_doan": du_doan,
            "Tin_cay": tin_cay,
            "Chi_tiet": chi_tiet,
            "Pattern": pattern,
            "So_lan_dung": dung,
            "So_lan_sai": sai,
            "Tong_so_lan_dudoan": tong
        }

    except Exception as e:
        print("Lỗi khi xử lý API:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
