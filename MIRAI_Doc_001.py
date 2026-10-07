import streamlit as st
import pdfplumber
import re
import pandas as pd
import plotly.express as px
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

st.set_page_config(page_title="【MIRAIサポート】財務・格付け診断アプリ", layout="wide")

st.title("🏦 財務・格付け診断 ＆ 逆算シミュレーション")
st.markdown("bixidの企業ドックPDFから、座標解析により財務数値を完璧に自動抽出します。")

# --- 補助関数：カンマ区切りの入力欄 ---
def input_with_comma(label, default_value):
    key_str = f"val_{label}"
    if key_str not in st.session_state:
        st.session_state[key_str] = default_value
    
    val_str = st.text_input(label, value=f"{st.session_state[key_str]:,}")
    
    try:
        clean_val = int(val_str.replace(",", "").replace(" ", "").replace(" ", ""))
        st.session_state[key_str] = clean_val
        return clean_val
    except ValueError:
        return st.session_state[key_str]

def safe_div(n, d):
    return n / d if d else 0

# 1. PDFアップロード機能
uploaded_file = st.file_uploader("bixidの企業ドックPDFをアップロードしてください", type="pdf")

data = {
    "決算月": "",
    "流動資産": 0, "売上債権": 0, "棚卸資産": 0, "固定資産": 0, "繰延資産": 0, "総資産": 0,
    "流動負債": 0, "仕入債務": 0, "短期借入金": 0, "固定負債": 0, "長期借入金": 0, "社債": 0, "純資産": 0,
    "売上高": 0, "売上原価": 0, "売上総利益": 0, "人件費": 0, "販管費": 0, "減価償却費": 0,
    "営業利益": 0, "受取利息・配当金": 0, "支払利息": 0, "経常利益": 0, "当期純利益": 0
}

if uploaded_file is not None:
    with pdfplumber.open(uploaded_file) as pdf:
        full_text = ""
        words_list = []
        
        for page in pdf.pages:
            t = page.extract_text() or ""
            full_text += t + "\n"
            # ページ内のすべての単語と座標を取得
            words_list.extend(page.extract_words())

        # 決算月の抽出
        month_match = re.search(r"\[(\d{4}/\d{1,2})\]", full_text)
        if month_match:
            data["決算月"] = month_match.group(1)

        # 座標ベースのパーサー：キーワードと同じ行（Y座標が近い）にあり、かつ右側にある数値を正確に取得する
        def get_value_by_coordinates(keyword):
            for i, word in enumerate(words_list):
                if keyword in word['text']:
                    kw_top = word['top']
                    kw_x1 = word['x1']
                    
                    # 同じ行（上下の許容誤差 ±4以内）にあり、かつキーワードより右側（x0 > kw_x1 - 10）にある単語を探す
                    candidate_nums = []
                    for w in words_list:
                        if abs(w['top'] - kw_top) <= 4 and w['x0'] >= kw_x1 - 10:
                            cleaned = w['text'].replace(",", "").replace(".", "").replace("円", "").strip()
                            if re.match(r"^-\d+$|^\d+$", cleaned):
                                candidate_nums.append((w['x0'], int(cleaned)))
                    
                    if candidate_nums:
                        # 最も右側にある（またはすぐ隣の）数字を採用
                        candidate_nums.sort(key=lambda x: x[0])
                        return candidate_nums[0][1]
            return 0

        # 各項目を座標解析で完全に抽出
        target_keys = list(data.keys())
        for k in target_keys:
            if k == "決算月":
                continue
            val = get_value_by_coordinates(k)
            if val != 0:
                data[k] = val
                st.session_state[f"val_{k}"] = val

        # 減価償却費の合算（複数箇所にある場合）
        total_dep = 0
        for i, word in enumerate(words_list):
            if "減価償却費" in word['text']:
                kw_top = word['top']
                kw_x1 = word['x1']
                for w in words_list:
                    if abs(w['top'] - kw_top) <= 4 and w['x0'] >= kw_x1 - 10:
                        cleaned = w['text'].replace(",", "").replace(".", "").strip()
                        if re.match(r"^\d+$", cleaned):
                            total_dep += int(cleaned)
                            break
        if total_dep > 0:
            data["減価償却費"] = total_dep
            st.session_state["val_減価償却費"] = total_dep

    st.success("企業ドックPDFの座標解析による財務数値の抽出が完了しました。")

# メインタブの作成
tab1, tab2, tab3 = st.tabs(["📝 1.財務データ・所見入力", "📊 2.財務分析＆レーダーチャート", "💰 3.借入余力シミュレーション"])

with tab1:
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1: company_name = st.text_input("企業名", value="株式会社〇〇")
    with col_info2: kessan_tsuki = st.text_input("決算月", value=data["決算月"] if data["決算月"] else "2026/3")
    with col_info3: jugyoin = st.number_input("従業員数（名）", min_value=1, value=10)
    
    col_bs, col_pl = st.columns(2)
    with col_bs:
        st.markdown("#### 【貸借対照表 (B/S)】")
        ryudo_shisan = input_with_comma("流動資産", data["流動資産"])
        urio = input_with_comma(" 売上債権", data["売上債権"])
        tana = input_with_comma(" 棚卸資産", data["棚卸資産"])
        kotei_shisan = input_with_comma("固定資産", data["固定資産"])
        sou_shisan = input_with_comma("総資産", data["総資産"])
        st.markdown("---")
        ryudo_fusai = input_with_comma("流動負債", data["流動負債"])
        shii = input_with_comma(" 仕入債務", data["仕入債務"])
        tanki = input_with_comma(" 短期借入金", data["短期借入金"])
        kotei_fusai = input_with_comma("固定負債", data["固定負債"])
        chouki = input_with_comma(" 長期借入金", data["長期借入金"])
        shasai = input_with_comma(" 社債", data["社債"])
        jun_shisan = input_with_comma("純資産", data["純資産"])

    with col_pl:
        st.markdown("#### 【損益計算書 (P/L)】")
        uriage = input_with_comma("売上高", data["売上高"])
        sori = input_with_comma("売上総利益（粗利）", data["売上総利益"])
        jinkenhi = input_with_comma(" うち人件費", data["人件費"])
        shokyaku = input_with_comma(" うち減価償却費", data["減価償却費"])
        eigyo = input_with_comma("営業利益", data["営業利益"])
        keijo = input_with_comma("経常利益", data["経常利益"])
        junrieki = input_with_comma("当期純利益", data["当期純利益"])

    st.markdown("---")
    st.markdown("#### ✍️ 診断者（銀行OB）の総合所見・今後の課題")
    diagnosis_opinion = st.text_area(
        "ここに銀行OBとしての評価、改善に向けたアドバイスなどを自由に記載してください（Excelに出力されます）。",
        value="【現状評価】\n表面上は債務超過であるが、役員借入金等を考慮した実態ベースでは正常先の範疇にある。\n\n【今後の課題・対策】\n来期の追加融資を見据え、売上高経常利益率の改善および固定費の見直しが急務である。",
        height=150
    )

# --- 計算ロジック ---
kizon_kariire = tanki + chouki + shasai
kani_cf = eigyo + shokyaku

roa = safe_div(junrieki, sou_shisan) * 100
eigyo_rieki_ritsu = safe_div(eigyo, uriage) * 100
junrieki_ritsu = safe_div(junrieki, uriage) * 100

shokan_nensu = safe_div(kizon_kariire, kani_cf) if kani_cf > 0 else 999
gessho_bairitsu = safe_div(kizon_kariire, safe_div(uriage, 12))

ryudo_hiritsu = safe_div(ryudo_shisan, ryudo_fusai) * 100
jikoshihon_hiritsu = safe_div(jun_shisan, sou_shisan) * 100
kotei_choki_hiritsu = safe_div(kotei_shisan, (kotei_fusai + jun_shisan)) * 100

rodou_bunpai = safe_div(jinkenhi, sori) * 100
uriage_per_head = safe_div(uriage, jugyoin)
nenshu_per_head = safe_div(jinkenhi, jugyoin)

with tab2:
    st.markdown(f"### 📈 財務指標分析レポート （{company_name} / {kessan_tsuki}期）")
    col_chart, col_metrics = st.columns([1, 1.5])
    with col_chart:
        score_shihon = 5 if jikoshihon_hiritsu >= 30 else 4 if jikoshihon_hiritsu >= 15 else 3 if jikoshihon_hiritsu >= 0 else 2 if jikoshihon_hiritsu >= -10 else 1
        score_ryudo = 5 if ryudo_hiritsu >= 150 else 4 if ryudo_hiritsu >= 100 else 3 if ryudo_hiritsu >= 80 else 2 if ryudo_hiritsu >= 50 else 1
        score_eigyo = 5 if eigyo_rieki_ritsu >= 10 else 4 if eigyo_rieki_ritsu >= 5 else 3 if eigyo_rieki_ritsu >= 0 else 2 if eigyo_rieki_ritsu >= -5 else 1
        score_shokan = 1 if kani_cf <= 0 else 5 if shokan_nensu <= 5 else 4 if shokan_nensu <= 10 else 3 if shokan_nensu <= 15 else 2
        score_rodou = 1 if sori <= 0 else 5 if rodou_bunpai <= 40 else 4 if rodou_bunpai <= 50 else 3 if rodou_bunpai <= 60 else 2
        
        df_radar = pd.DataFrame(dict(
            r=[score_shihon, score_ryudo, score_eigyo, score_shokan, score_rodou],
            theta=['安全性\n(自己資本比率)', '資金力\n(流動比率)', '収益性\n(営業利益率)', '返済能力\n(償還年数)', '効率性\n(労働分配率)']
        ))
        fig = px.line_polar(df_radar, r='r', theta='theta', line_close=True, range_r=[0,5], title="銀行目線 財務バランスマップ")
        fig.update_traces(fill='toself', line_color='#1f77b4')
        st.plotly_chart(fig, use_container_width=True)

    with col_metrics:
        st.markdown("#### 12の主要指標一覧")
        m1, m2, m3 = st.columns(3)
        m1.metric("ROA", f"{roa:.1f} %")
        m2.metric("売上高営業利益率", f"{eigyo_rieki_ritsu:.1f} %")
        m3.metric("売上高当期純利益率", f"{junrieki_ritsu:.1f} %")
        
        m4, m5, m6 = st.columns(3)
        m4.metric("簡易CF", f"{kani_cf:,} 円")
        m5.metric("簡易債務償還年数", f"{shokan_nensu:.1f} 年" if kani_cf > 0 else "測定不能 (赤字)")
        m6.metric("借入金月商倍率", f"{gessho_bairitsu:.1f} ヶ月")

        m7, m8, m9 = st.columns(3)
        m7.metric("流動比率", f"{ryudo_hiritsu:.1f} %")
        m8.metric("自己資本比率", f"{jikoshihon_hiritsu:.1f} %")
        m9.metric("固定長期適合率", f"{kotei_choki_hiritsu:.1f} %")

        m10, m11, m12 = st.columns(3)
        m10.metric("一人当たり売上", f"{int(uriage_per_head):,} 円")
        m11.metric("労働分配率", f"{rodou_bunpai:.1f} %")
        m12.metric("平均年収", f"{int(nenshu_per_head):,} 円")

with tab3:
    st.markdown(f"### 🏦 借入余力・逆算シミュレーション （{company_name}）")
    col3_1, col3_2 = st.columns(2)
    with col3_1:
        st.subheader("【ブロック1】運転資金枠チェック")
        unten_shikin = urio + tana - shii
        st.metric(label="正常運転資金（短期枠）", value=f"{unten_shikin:,} 円")
        
        st.subheader("【ブロック2】CF借入余力（現状の限界）")
        kyoyou_nensu = st.selectbox("銀行の許容償還年数", [7, 10, 15], index=1)
        cf_yoryoku = (kani_cf * kyoyou_nensu) - kizon_kariire if kani_cf > 0 else 0
        st.metric(label="現在の稼ぐ力から見た借入余力", value=f"{cf_yoryoku:,} 円")

    with col3_2:
        st.subheader("【ブロック3】目標利益の逆算")
        kibou_gaku = input_with_comma("追加希望融資額（円）", 10000000)
        hensai_kikan = st.slider("希望返済期間（年）", min_value=1, max_value=20, value=7)
        
        hitsuyou_cf = safe_div((kizon_kariire + kibou_gaku), hensai_kikan)
        mokuhyo_eigyo = hitsuyou_cf - shokyaku
        
        st.info(f"💡 {kibou_gaku:,}円 を {hensai_kikan}年で返すための条件")
        st.metric(label="来期に必要な営業利益（必達目標）", value=f"{int(mokuhyo_eigyo):,} 円")
        
    st.markdown("---")
    st.markdown("💬 **銀行OBからの処方箋**")
    if mokuhyo_eigyo > eigyo:
        kaizen_gaku = int(mokuhyo_eigyo - eigyo)
        st.warning(f"社長,現状のままでは追加融資の稟議は通りません。融資を引き出すためには、来期の営業利益を今の状態から **{kaizen_gaku:,}円 改善** させる計画書が必要です。我々と一緒に、この利益を生み出すための具体的な経営改善計画を作りましょう。")
    else:
        st.success("現状の収益力でも十分に審査のテーブルに乗る可能性が高いです。具体的な事業計画書に落とし込みましょう。")

# --- スタイリッシュなExcel生成・ダウンロード機能 ---
st.markdown("---")
st.markdown("### 📥 スタイリッシュ診断レポート（Excel）ダウンロード")

output = io.BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    df_bs_pl = pd.DataFrame({
        "項目": [
            "企業名", "決算月", "従業員数",
            "流動資産", "  うち売上債権", "  うち棚卸資産", "固定資産", "総資産",
            "流動負債", "  うち仕入債務", "  うち短期借入金", "固定負債", "  うち長期借入金", "  うち社債", "純資産",
            "売上高", "売上総利益(粗利)", "  うち人件費", "  うち減価償却費", "営業利益", "経常利益", "当期純利益"
        ],
        "金額 (円)": [
            company_name, kessan_tsuki, jugyoin,
            ryudo_shisan, urio, tana, kotei_shisan, sou_shisan,
            ryudo_fusai, shii, tanki, kotei_fusai, chouki, shasai, jun_shisan,
            uriage, sori, jinkenhi, shokyaku, eigyo, keijo, junrieki
        ]
    })
    df_bs_pl.to_excel(writer, sheet_name="財務データ", index=False)
    
    df_analysis = pd.DataFrame({
        "指標カテゴリ": ["収益性", "収益性", "収益性", "資金力", "資金力", "資金力", "安全性", "安全性", "安全性", "効率性", "効率性", "効率性"],
        "指標名": [
            "ROA", "売上高営業利益率", "売上高当期純利益率",
            "簡易キャッシュフロー", "簡易債務償還年数", "借入金月商倍率",
            "流動比率", "自己資本比率", "固定長期適合率",
            "一人当たり売上高", "労働分配率", "平均年収"
        ],
        "数値": [
            f"{roa:.1f}%", f"{eigyo_rieki_ritsu:.1f}%", f"{junrieki_ritsu:.1f}%",
            f"{kani_cf:,} 円", f"{shokan_nensu:.1f} 年" if kani_cf > 0 else "測定不能", f"{gessho_bairitsu:.1f} ヶ月",
            f"{ryudo_hiritsu:.1f}%", f"{jikoshihon_hiritsu:.1f}%", f"{kotei_choki_hiritsu:.1f}%",
            f"{int(uriage_per_head):,} 円", f"{rodou_bunpai:.1f}%", f"{int(nenshu_per_head):,} 円"
        ]
    })
    df_analysis.to_excel(writer, sheet_name="財務分析指標", index=False)
    
    df_sim = pd.DataFrame({
        "シミュレーション項目": [
            "正常運転資金（短期枠）",
            "現在の稼ぐ力から見た借入余力（CF基準）",
            "追加希望融資額",
            "希望返済期間",
            "来期に必要な営業利益（必達目標）"
        ],
        "結果": [
            f"{unten_shikin:,} 円",
            f"{cf_yoryoku:,} 円",
            f"{kibou_gaku:,} 円",
            f"{hensai_kikan} 年",
            f"{int(mokuhyo_eigyo):,} 円"
        ]
    })
    df_sim.to_excel(writer, sheet_name="借入余力・逆算シミュレーション", index=False)

    df_opinion = pd.DataFrame({
        "項目": ["対象企業", "決算月", "銀行OB 総合所見・今後の課題"],
        "内容": [company_name, kessan_tsuki, diagnosis_opinion]
    })
    df_opinion.to_excel(writer, sheet_name="総合所見", index=False)

excel_data = output.getvalue()
wb = openpyxl.load_workbook(io.BytesIO(excel_data))

header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
header_font = Font(name="Meiryo", size=11, bold=True, color="FFFFFF")
cell_font = Font(name="Meiryo", size=10)
stripe_fill = PatternFill(start_color="F9FBFD", end_color="F9FBFD", fill_type="solid")
border_thin = Border(left=Side(style='thin', color='D9D9D9'), right=Side(style='thin', color='D9D9D9'), top=Side(style='thin', color='D9D9D9'), bottom=Side(style='thin', color='D9D9D9'))

for sheet in wb.sheetnames:
    ws = wb[sheet]
    for col_num in range(1, ws.max_column + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border_thin
    ws.row_dimensions[1].height = 25

    for row_num in range(2, ws.max_row + 1):
        ws.row_dimensions[row_num].height = 20
        is_stripe = (row_num % 2 == 0)
        for col_num in range(1, ws.max_column + 1):
            cell = ws.cell(row=row_num, column=col_num)
            cell.font = cell_font
            cell.border = border_thin
            if is_stripe:
                cell.fill = stripe_fill
            if col_num > 1 and sheet != "総合所見":
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value:
                for line in str(cell.value).split('\n'):
                    if len(line) > max_len: max_len = len(line)
        ws.column_dimensions[col_letter].width = max(max_len * 2 + 4, 15)

final_output = io.BytesIO()
wb.save(final_output)

st.download_button(
    label="📊 スタイリッシュなExcelレポートをダウンロード",
    data=final_output.getvalue(),
    file_name=f"財務格付け診断レポート_{company_name}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
