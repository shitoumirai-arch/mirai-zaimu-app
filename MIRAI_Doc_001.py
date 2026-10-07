import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="【MIRAIサポート】財務・格付け診断アプリ", layout="wide")

st.title("🏦 財務・格付け診断 ＆ 逆算シミュレーション")
st.markdown("bixidの「企業ドック診断結果(PDF)」をアップロードすると、B/S・P/Lの全項目を自動抽出し、銀行目線での借入余力をシミュレーションします。")

# --- 補助関数：カンマ区切りの入力欄を作る ---
def input_with_comma(label, default_value):
    val_str = st.text_input(label, value=f"{default_value:,}")
    try:
        return int(val_str.replace(",", "").replace(" ", "").replace(" ", ""))
    except ValueError:
        return 0

# 1. PDFアップロード機能
uploaded_file = st.file_uploader("bixidのPDFをアップロードしてください", type="pdf")

# 初期値データ辞書の作成（PDFから拾えなかった時は0になる）
data = {
    "決算月": "",
    "流動資産": 0, "売上債権": 0, "棚卸資産": 0, "固定資産": 0, "繰延資産": 0, "総資産": 0,
    "流動負債": 0, "仕入債務": 0, "短期借入金": 0, "固定負債": 0, "長期借入金": 0, "社債": 0, "純資産": 0,
    "売上高": 0, "売上原価": 0, "売上総利益": 0, "人件費": 0, "販管費": 0, "減価償却費": 0,
    "営業利益": 0, "受取利息・配当金": 0, "支払利息": 0, "経常利益": 0, "当期純利益": 0
}

# PDFからのテキスト抽出と数値解析
if uploaded_file is not None:
    with pdfplumber.open(uploaded_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
        
        # 決算月の抽出 (例: [2026/3])
        month_match = re.search(r"\[(\d{4}/\d{1,2})\]", text)
        if month_match:
            data["決算月"] = month_match.group(1)
        
        # 各科目の正規表現パターン
        patterns = {
            "流動資産": r"流動資産[\s\|]*([\d,\.]+)",
            "売上債権": r"売上債権[\s\|]*([\d,\.]+)",
            "棚卸資産": r"棚卸資産[\s\|]*([\d,\.]+)",
            "固定資産": r"固定資産[\s\|]*([\d,\.]+)",
            "繰延資産": r"繰延資産[\s\|]*([\d,\.]+)",
            "総資産": r"総資産[\s\|]*([\d,\.]+)",
            
            "流動負債": r"流動負債[\s\|]*([\d,\.]+)",
            "仕入債務": r"仕入債務[\s\|]*([\d,\.]+)",
            "短期借入金": r"短期借入金[\s\|]*([\d,\.]+)",
            "固定負債": r"固定負債[\s\|]*([\d,\.]+)",
            "長期借入金": r"長期借入金[\s\|]*([\d,\.]+)",
            "社債": r"社債[\s\|]*([\d,\.]+)",
            "純資産": r"純資産[\s\|]*([-\d,\.]+)",
            
            "売上高": r"売上高[\s\|]*([\d,\.]+)",
            "売上原価": r"売上原価[\s\|]*([\d,\.]+)",
            "売上総利益": r"売上総利益[\s\|]*([-\d,\.]+)",
            "人件費": r"人件費[\s\|]*([\d,\.]+)",
            "販管費": r"販管費[\s\|]*([\d,\.]+)",
            "営業利益": r"営業利益[\s\|]*([-\d,\.]+)",
            "受取利息・配当金": r"受取利息・配当金[\s\|]*([\d,\.]+)",
            "支払利息": r"支払利息[\s\|]*([\d,\.]+)",
            "経常利益": r"経常利益[\s\|]*([-\d,\.]+)",
            "当期純利益": r"当期純利益[\s\|]*([-\d,\.]+)"
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                val_str = match.group(1).replace(",", "").replace(".", "")
                try:
                    data[key] = int(val_str)
                except ValueError:
                    pass
        
        # 減価償却費は複数箇所（製造原価と販管費など）にある場合を想定し、すべて合算する
        depreciations = re.findall(r"減価償却費[\s\|]*([\d,\.]+)", text)
        total_dep = 0
        for dep in depreciations:
            try:
                total_dep += int(dep.replace(",", "").replace(".", ""))
            except:
                pass
        if total_dep > 0:
            data["減価償却費"] = total_dep
            
    st.success("PDFの読み込みが完了しました。")

# 2. 基本情報と抽出データの確認・修正エリア
st.header("1. 基本情報・財務データの確認・修正")
st.markdown("PDFから抽出された決算数値を一覧表示しています。実態修正が必要な項目は直接数値を書き換えてください。")

# --- 追加：企業名と決算月 ---
st.subheader("📌 基本情報")
col_info1, col_info2 = st.columns(2)
with col_info1:
    company_name = st.text_input("企業名", placeholder="株式会社〇〇")
with col_info2:
    kessan_tsuki = st.text_input("決算月", value=data["決算月"], placeholder="例：2026/3")

# --- 追加：B/SとP/Lをタブで整理 ---
tab1, tab2 = st.tabs(["貸借対照表 (B/S)", "損益計算書 (P/L)"])

with tab1:
    col_bs_left, col_bs_right = st.columns(2)
    with col_bs_left:
        st.markdown("###### 【資産の部】")
        ryudo_shisan = input_with_comma("流動資産", data["流動資産"])
        urio = input_with_comma(" うち売上債権", data["売上債権"])
        tana = input_with_comma(" うち棚卸資産", data["棚卸資産"])
        kotei_shisan = input_with_comma("固定資産", data["固定資産"])
        kurinobe_shisan = input_with_comma("繰延資産", data["繰延資産"])
        sou_shisan = input_with_comma("総資産", data["総資産"])

    with col_bs_right:
        st.markdown("###### 【負債・純資産の部】")
        ryudo_fusai = input_with_comma("流動負債", data["流動負債"])
        shii = input_with_comma(" うち仕入債務", data["仕入債務"])
        tanki = input_with_comma(" うち短期借入金", data["短期借入金"])
        kotei_fusai = input_with_comma("固定負債", data["固定負債"])
        chouki = input_with_comma(" うち長期借入金", data["長期借入金"])
        shasai = input_with_comma(" うち社債", data["社債"])
        jun_shisan = input_with_comma("純資産", data["純資産"])

with tab2:
    col_pl_left, col_pl_right = st.columns(2)
    with col_pl_left:
        uriage = input_with_comma("売上高", data["売上高"])
        genka = input_with_comma("売上原価", data["売上原価"])
        sori = input_with_comma("売上総利益", data["売上総利益"])
        hankanhi = input_with_comma("販管費", data["販管費"])
        jinkenhi = input_with_comma(" うち人件費", data["人件費"])
        shokyaku = input_with_comma("減価償却費（全体）", data["減価償却費"])
    with col_pl_right:
        eigyo = input_with_comma("営業利益", data["営業利益"])
        uketsori_risoku = input_with_comma("受取利息・配当金", data["受取利息・配当金"])
        shiharai_risoku = input_with_comma("支払利息", data["支払利息"])
        keijo = input_with_comma("経常利益", data["経常利益"])
        junrieki = input_with_comma("当期純利益", data["当期純利益"])

# シミュレーション計算用の変数を再定義（入力された値を元に計算）
kizon_kariire = tanki + chouki + shasai
kani_cf = eigyo + shokyaku

# 3. シミュレーション実行エリア
st.header("2. 融資可能額・逆算シミュレーション")

# 企業名が入力されていれば表示する
if company_name:
    st.markdown(f"#### 🏢 対象企業：{company_name} （{kessan_tsuki} 期）")

col3, col4 = st.columns(2)
with col3:
    st.subheader("【ブロック1】運転資金枠チェック")
    unten_shikin = urio + tana - shii
    st.metric(label="正常運転資金（短期枠）", value=f"{unten_shikin:,} 円")
    
    st.subheader("【ブロック2】CF借入余力（現状の限界）")
    kyoyou_nensu = st.selectbox("銀行の許容償還年数", [7, 10, 15], index=1)
    
    if kani_cf <= 0:
        cf_yoryoku = 0
    else:
        cf_yoryoku = (kani_cf * kyoyou_nensu) - kizon_kariire
    
    st.metric(label="現在の稼ぐ力から見た借入余力", value=f"{cf_yoryoku if cf_yoryoku > 0 else 0:,} 円")

with col4:
    st.subheader("【ブロック3】目標利益の逆算")
    kibou_gaku = input_with_comma("追加希望融資額（円）", 10000000)
    hensai_kikan = st.slider("希望返済期間（年）", min_value=1, max_value=20, value=7)
    
    hitsuyou_cf = (kizon_kariire + kibou_gaku) / hensai_kikan
    mokuhyo_eigyo = hitsuyou_cf - shokyaku
    
    st.info(f"💡 {kibou_gaku:,}円 を {hensai_kikan}年で返すための条件")
    st.metric(label="来期に必要な営業利益（必達目標）", value=f"{int(mokuhyo_eigyo):,} 円")
    
st.markdown("---")
st.markdown("💬 **銀行OBからの処方箋**")
if mokuhyo_eigyo > eigyo:
    kaizen_gaku = int(mokuhyo_eigyo - eigyo)
    st.warning(f"社長、現状のままでは追加融資の稟議は通りません。融資を引き出すためには、来期の営業利益を今の状態から **{kaizen_gaku:,}円 改善** させる計画書が必要です。我々と一緒に、この利益を生み出すための具体的な経営改善計画を作りましょう。")
else:
    st.success("現状の収益力でも十分に審査のテーブルに乗る可能性が高いです。具体的な事業計画書に落とし込みましょう。")
