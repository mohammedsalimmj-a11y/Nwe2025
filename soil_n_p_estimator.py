
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Soil N & P Estimator", page_icon="🧪", layout="centered")

st.title("🧪 برنامج تقدير نسبة النيتروجين والفسفور في التربة")
st.write(
    """
    هذا البرنامج يساعدك على حساب **تركيز النيتروجين (N)** و**الفسفور (P)** في عينات التربة
    اعتماداً على قراءات الامتصاص الضوئي (Absorbance) ومنحنى المعايرة أو على قيم التركيز المباشرة (mg/L).
    
    **المخرجات**: mg/L في محلول الهضم/الاستخلاص، mg/kg في التربة، %N و %P، إضافةً إلى %P₂O₅ للفسفور.
    """
)

with st.expander("ℹ️ التعليمات المختصرة", expanded=False):
    st.markdown(
        """
        1) أدخل **بيانات المعايير** (تركيز–امتصاص) لـ N و/أو P لبناء **منحنى المعايرة** (انحدار خطي).
        2) أدخل **امتصاص العينة** أو **التركيز المباشر mg/L** إذا كان متوفراً.
        3) أدخل **وزن العينة (جم)**، **حجم الهضم/الاستخلاص (مل)**، وأي **تخفيف إضافي** تم قبل القياس.
        4) ستحصل على mg/kg و**النسبة المئوية**. للفسفور تُحسب أيضاً %P₂O₅ (معامل التحويل 2.291).
        
        > الصيغ الأساسية:
        >
        > - من الامتصاص: \\( C_{mg/L} = (A - b) / m \\) حيث \\(m\\) الميل و\\(b\\) الجزء المقطوع.
        > - التحويل إلى mg/kg: \\( C_{mg/kg} = \\frac{C_{mg/L} \\times V_{\\text{محلول}}(L) \\times DF}{\\text{وزن العينة (كجم)}} \\).
        > - التحويل إلى %: \\( \\% = \\frac{C_{mg/kg}}{10000} \\).
        > - \\( \\%P_2O_5 = \\%P \\times 2.291 \\).
        """
    )

def fit_curve(df):
    # Expect columns: "Conc_mg_L", "Abs"
    x = df["Conc_mg_L"].values.astype(float)
    y = df["Abs"].values.astype(float)
    if len(x) < 2 or len(y) < 2:
        return None
    # Linear regression y = m*x + b  -> m,b from least squares
    A = np.vstack([x, np.ones(len(x))]).T
    m, b = np.linalg.lstsq(A, y, rcond=None)[0]
    # R^2
    y_pred = m*x + b
    ss_res = np.sum((y - y_pred)**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r2 = 1 - ss_res/ss_tot if ss_tot != 0 else np.nan
    return {"m": m, "b": b, "r2": r2}

def calc_from_abs(A, m, b):
    if m == 0:
        return np.nan
    return (A - b) / m

def block(title):
    st.subheader(title)
    tab_curve, tab_sample = st.tabs(["منحنى المعايرة", "بيانات العينة"])
    with tab_curve:
        st.markdown("**أدخل نقاط المعايرة (تركيز–امتصاص):**")
        eg = st.toggle("إدراج مثال توضيحي", value=False)
        if eg:
            df_init = pd.DataFrame({
                "Conc_mg_L":[0, 1, 2, 5, 10],
                "Abs":[0.005, 0.09, 0.175, 0.46, 0.92]
            })
        else:
            df_init = pd.DataFrame({"Conc_mg_L":[0.0], "Abs":[0.0]})
        df = st.data_editor(df_init, num_rows="dynamic", use_container_width=True)
        curve = fit_curve(df) if len(df)>=2 else None
        if curve:
            st.success(f"معادلة الانحدار: A = m·C + b  →  m = {curve['m']:.6f}  |  b = {curve['b']:.6f}  |  R² = {curve['r2']:.4f}")
        else:
            st.info("أدخل نقطتين معايرة أو أكثر لحساب الانحدار.")
    with tab_sample:
        mode = st.radio("وضع الإدخال:", ["امتصاص العينة (A)", "التركيز المباشر (mg/L)"], horizontal=True)
        A = None
        C_direct = None
        if mode == "امتصاص العينة (A)":
            A = st.number_input("امتصاص العينة (A)", value=0.0, step=0.001, format="%.6f")
        else:
            C_direct = st.number_input("تركيز العينة المباشر (mg/L)", value=0.0, step=0.01, format="%.6f")
        st.markdown("**بارامترات الحساب:**")
        sample_mass_g = st.number_input("وزن العينة (جم)", value=1.00, step=0.01, min_value=0.0001, format="%.4f")
        digest_vol_mL = st.number_input("حجم الهضم/الاستخلاص النهائي (مل)", value=100.0, step=1.0, min_value=0.01, format="%.2f")
        aliquot_dilution = st.number_input("معامل التخفيف الإضافي قبل القياس (DF)", value=1.00, step=0.01, min_value=0.01, format="%.2f")
        
        # Compute concentration in mg/L
        if C_direct is not None and mode == "التركيز المباشر (mg/L)":
            C_mg_L = C_direct
        else:
            if curve and A is not None:
                C_mg_L = calc_from_abs(A, curve["m"], curve["b"])
            else:
                C_mg_L = None
        
        if C_mg_L is None or np.isnan(C_mg_L):
            st.warning("أكمل إدخال منحنى المعايرة و/أو بيانات الامتصاص أو التركيز المباشر.")
            return None
        
        # Unit conversions
        V_L = digest_vol_mL / 1000.0
        mass_kg = sample_mass_g / 1000.0
        C_mg_kg = (C_mg_L * V_L * aliquot_dilution) / mass_kg if mass_kg>0 else np.nan
        pct = C_mg_kg / 10000.0
        
        results = {
            "C_mg_L": C_mg_L,
            "C_mg_kg": C_mg_kg,
            "percent": pct
        }
        return results, curve

col1, col2 = st.columns(2)

with col1:
    res_N = block("النيتروجين (N)")
with col2:
    res_P = block("الفسفور (P)")

st.markdown("---")
if res_N is None and res_P is None:
    st.stop()

out_rows = []

if res_N is not None:
    data, curve = res_N
    out_rows.append({
        "Analyte":"N",
        "C (mg/L)": round(data["C_mg_L"], 6),
        "C (mg/kg)": round(data["C_mg_kg"], 3),
        "%": round(data["percent"]*100, 5)
    })

if res_P is not None:
    data, curve = res_P
    pctP = data["percent"]*100  # %P
    pctP2O5 = pctP * 2.291
    out_rows.append({
        "Analyte":"P",
        "C (mg/L)": round(data["C_mg_L"], 6),
        "C (mg/kg)": round(data["C_mg_kg"], 3),
        "%": round(pctP, 5),
        "% as P2O5": round(pctP2O5, 5)
    })

if out_rows:
    df_out = pd.DataFrame(out_rows).fillna("")
    st.subheader("النتائج")
    st.dataframe(df_out, use_container_width=True)
    
    # CSV download
    csv = df_out.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ تنزيل النتائج (CSV)", data=csv, file_name="soil_N_P_results.csv", mime="text/csv")

st.caption("ملاحظة: البرنامج لا يستبدل طرق التحليل المعتمدة مخبرياً، بل يساعد في الحسابات وتحويل الوحدات.")
