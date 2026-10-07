import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="【MIRAIサポート】財務・格付け診断アプリ", layout="wide")

st.title("🏦 財務・格付け診断 ＆ 逆算シミュレーション")
st.markdown("bixidの「企業ドック診断結果(PDF)」をアップロードすると、主要数値を自動抽出し、銀行目線での借入余力をシミュレーションします。")

# --- 補助関数：カンマ区切りの入力欄を作る ---
def input_with_comma(label, default_value):
    # カンマ付きの文字列としてテキストボックスを表示
    val_str = st.text_input(label, value=f"{default_value:,}")
    # カンマや全角半角のスペースを除去して数値（整数）に戻す
    try:
        return int(val_str.replace(",", "").replace(" ", "").replace(" ", ""))
    except ValueError:
        return 0

# 1. PDFアップロード機能
uploaded_file = st.file_uploader("bixidのPDFをアップロードしてください", type="pdf")

# 初期値
data = {
    "売上債権": 0, "棚卸資産": 0, "仕入債務": 0,
    "短期借入金": 0, "長期借入金": 0,
    "営業利益": 0, "減価償却費": 0
}

# PDFからのテキスト抽出と数値解析
if uploaded_file is not None:
    with pdfplumber.open(uploaded_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
        
        patterns = {
            "売上債権": r"売上債権\s*([\d,]+)",
            "棚卸資産": r"棚卸資産\s*([\d,]+)",
            "仕入債務": r"仕入債務\s*([\d,]+)",
            "短期借入金": r"短期借入金\s*([\d,]+)",
            "長期借入金": r"長期借入金\s*([\d,]+)",
            "営業利益": r"営業利益\s*([-\d,]+)",
            "減価償却費": r"減価償却費\s*([\d,]+)"
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                data[key] = int(match.group(1).replace(",", ""))
    st.success("PDFの読み込みが完了しました。数値を自動入力しています（必要に応じて手修正してください）。")

# 2. 抽出データの確認・修正エリア
st.header("1. 財務データの確認・修正")
st.markdown("銀行OBの視点で、役員貸付や含み損益などの「実態修正」がある場合は、ここで直接数値を書き換えてください。")

col1, col2 = st.columns(2)
with col1:
    urio = input_with_comma("売上債権（円）", data["売上債権"])
    tana = input_with_comma("棚卸資産（円）", data["棚卸資産"])
    shii = input_with_comma("仕入債務（円）", data["仕入債務"])
with col2:
    tanki = input_with_comma("短期借入金（円）", data["短期借入金"])
    chouki = input_with_comma("長期借入金（円）", data["長期借入金"])
    eigyo = input_with_comma("営業利益（円）", data["営業利益"])
    shokyaku = input_with_comma("減価償却費（円）", data["減価償却費"])

kizon_kariire = tanki + chouki
kani_cf = eigyo + shokyaku

# 3. シミュレーション実行エリア
st.header("2. 融希可能額・逆算シミュレーション")

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
    kibou_gaku = st.number_input("追加希望融資額（円）", min_value=0, value=10000000, step=1000000)
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
