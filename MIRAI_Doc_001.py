import streamlit as st
import pdfplumber
import re
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="【MIRAIサポート】財務・格付け診断アプリ", layout="wide")

st.title("🏦 財務・格付け診断 ＆ 逆算シミュレーション")
st.markdown("財務数値を入力・修正すると、銀行目線での分析指標とレーダーチャートがリアルタイムに変化します。")

# --- 補助関数：カンマ区切りの入力欄 ---
def input_with_comma(label, default_value):
    val_str = st.text_input(label, value=f"{default_value:,}")
    try:
        return int(val_str.replace(",", "").replace(" ", "").replace(" ", ""))
    except ValueError:
        return 0

# --- 補助関数：ゼロ割りを防ぐ ---
def safe_div(n, d):
    return n / d if d else 0

# 1. PDFアップロード機能
uploaded_file = st.file_uploader("bixidのPDFをアップロードしてください", type="pdf")

data = {
    "決算月": "",
    "流動資産": 0, "売上債権": 0, "棚卸資産": 0, "固定資産": 0, "繰延資産": 0, "総資産": 0,
    "流動負債": 0, "仕入債務": 0, "短期借入金": 0, "固定負債": 0, "長期借入金": 0, "社債": 0, "純資産": 0,
    "売上高": 0, "売上原価": 0, "売上総利益": 0, "人件費": 0, "販管費": 0, "減価償却費": 0,
    "営業利益": 0, "受取利息・配当金": 0, "支払利息": 0, "経常利益": 0, "当期純利益": 0
}

if uploaded_file is not None:
    with pdfplumber.open(uploaded_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
        
        month_match = re.search(r"\[(\d{4}/\d{1,2})\]", text)
        if month_match:
            data["決算月"] = month_match.group(1)
        
        patterns = {
            "流動資産": r"流動資産[\s\|]*([\d,\.]+)", "売上債権": r"売上債権[\s\|]*([\d,\.]+)",
            "棚卸資産": r"棚卸資産[\s\|]*([\d,\.]+)", "固定資産": r"固定資産[\s\|]*([\d,\.]+)",
            "繰延資産": r"繰延資産[\s\|]*([\d,\.]+)", "総資産": r"総資産[\s\|]*([\d,\.]+)",
            "流動負債": r"流動負債[\s\|]*([\d,\.]+)", "仕入債務": r"仕入債務[\s\|]*([\d,\.]+)",
            "短期借入金": r"短期借入金[\s\|]*([\d,\.]+)", "固定負債": r"固定負債[\s\|]*([\d,\.]+)",
            "長期借入金": r"長期借入金[\s\|]*([\d,\.]+)", "社債": r"社債[\s\|]*([\d,\.]+)",
            "純資産": r"純資産[\s\|]*([-\d,\.]+)",
            "売上高": r"売上高[\s\|]*([\d,\.]+)", "売上原価": r"売上原価[\s\|]*([\d,\.]+)",
            "売上総利益": r"売上総利益[\s\|]*([-\d,\.]+)", "人件費": r"人件費[\s\|]*([\d,\.]+)",
            "販管費": r"販管費[\s\|]*([\d,\.]+)", "営業利益": r"営業利益[\s\|]*([-\d,\.]+)",
            "受取利息・配当金": r"受取利息・配当金[\s\|]*([\d,\.]+)", "支払利息": r"支払利息[\s\|]*([\d,\.]+)",
            "経常利益": r"経常利益[\s\|]*([-\d,\.]+)", "当期純利益": r"当期純利益[\s\|]*([-\d,\.]+)"
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                try:
                    data[key] = int(match.group(1).replace(",", "").replace(".", ""))
                except ValueError:
                    pass
                    
        total_dep = sum([int(d.replace(",", "").replace(".", "")) for d in re.findall(r"減価償却費[\s\|]*([\d,\.]+)", text)])
        if total_dep > 0: data["減価償却費"] = total_dep
            
    st.success("PDFの読み込みが完了しました。")

# メインタブの作成
tab1, tab2, tab3 = st.tabs(["📝 1.財務データ入力・修正", "📊 2.財務分析＆レーダーチャート", "💰 3.借入余力シミュレーション"])

with tab1:
    st.markdown("###### 実態修正（役員借入金の振替など）を行うと、隣のタブの分析結果やグラフが自動で改善されます。")
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1: company_name = st.text_input("企業名", placeholder="株式会社〇〇")
    with col_info2: kessan_tsuki = st.text_input("決算月", value=data["決算月"], placeholder="例：2026/3")
    with col_info3: jugyoin = st.number_input("従業員数（名）", min_value=1, value=10) # 効率性計算に必須
    
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

# --- 計算ロジック ---
kizon_kariire = tanki + chouki + shasai
kani_cf = eigyo + shokyaku

# 収益性
roa = safe_div(junrieki, sou_shisan) * 100
eigyo_rieki_ritsu = safe_div(eigyo, uriage) * 100
junrieki_ritsu = safe_div(junrieki, uriage) * 100

# 資金力
shokan_nensu = safe_div(kizon_kariire, kani_cf) if kani_cf > 0 else 999
gessho_bairitsu = safe_div(kizon_kariire, safe_div(uriage, 12))

# 安全性
ryudo_hiritsu = safe_div(ryudo_shisan, ryudo_fusai) * 100
jikoshihon_hiritsu = safe_div(jun_shisan, sou_shisan) * 100
kotei_choki_hiritsu = safe_div(kotei_shisan, (kotei_fusai + jun_shisan)) * 100

# 効率性
rodou_bunpai = safe_div(jinkenhi, sori) * 100
uriage_per_head = safe_div(uriage, jugyoin)
nenshu_per_head = safe_div(jinkenhi, jugyoin)

with tab2:
    st.markdown(f"### 📈 財務指標分析 （{company_name}）")
    
    col_chart, col_metrics = st.columns([1, 1.5])
    
    with col_chart:
        # 銀行目線の簡易スコアリング（5段階評価）
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
        st.markdown("#### 12の主要指標")
        m1, m2, m3 = st.columns(3)
        m1.metric("ROA (当期純利益)", f"{roa:.1f} %")
        m2.metric("売上高営業利益率", f"{eigyo_rieki_ritsu:.1f} %")
        m3.metric("売上高当期純利益率", f"{junrieki_ritsu:.1f} %")
        
        m4, m5, m6 = st.columns(3)
        m4.metric("簡易キャッシュフロー", f"{kani_cf:,} 円")
        m5.metric("簡易債務償還年数", f"{shokan_nensu:.1f} 年" if kani_cf > 0 else "測定不能 (赤字)")
        m6.metric("借入金対月商倍率", f"{gessho_bairitsu:.1f} ヶ月")

        m7, m8, m9 = st.columns(3)
        m7.metric("流動比率", f"{ryudo_hiritsu:.1f} %")
        m8.metric("自己資本比率", f"{jikoshihon_hiritsu:.1f} %")
        m9.metric("固定長期適合率", f"{kotei_choki_hiritsu:.1f} %")

        m10, m11, m12 = st.columns(3)
        m10.metric("一人当たり売上高", f"{int(uriage_per_head):,} 円")
        m11.metric("労働分配率", f"{rodou_bunpai:.1f} %")
        m12.metric("平均年収", f"{int(nenshu_per_head):,} 円")

with tab3:
    st.markdown("### 🏦 借入余力・逆算シミュレーション")
    col3_1, col3_2 = st.columns(2)
    with col3_1:
        st.subheader("【ブロック1】運転資金枠チェック")
        st.metric(label="正常運転資金（短期枠）", value=f"{(urio + tana - shii):,} 円")
        
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
        st.warning(f"社長、現状のままでは追加融資の稟議は通りません。融資を引き出すためには、来期の営業利益を今の状態から **{int(mokuhyo_eigyo - eigyo):,}円 改善** させる計画書が必要です。我々と一緒に、この利益を生み出すための具体的な経営改善計画を作りましょう。")
    else:
        st.success("現状の収益力でも十分に審査のテーブルに乗る可能性が高いです。具体的な事業計画書に落とし込みましょう。")
