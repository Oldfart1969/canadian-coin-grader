
import streamlit as st
from PIL import Image
from grading_engine import grade_coin, grade_explanation, validate_image
import pandas as pd

st.set_page_config(page_title="Canadian Coin Grader", page_icon="🪙", layout="wide")

st.title("🪙 Canadian Coin Grader — Prototype")
st.caption("Estimation photographique du grade d'une pièce canadienne. Ce prototype n'est pas une certification ICCS/PCGS/NGC.")

with st.sidebar:
    st.header("Identification")
    denomination = st.selectbox(
        "Dénomination",
        ["1 cent", "5 cents", "10 cents", "20 cents", "25 cents", "50 cents", "1 dollar", "2 dollars"]
    )
    year = st.number_input("Année", min_value=1858, max_value=2030, value=1953, step=1)
    strike = st.selectbox(
        "Type de frappe",
        ["Circulation", "Proof-Like (PL)", "Specimen (SP)", "Proof (PR/PF)"]
    )
    st.divider()
    st.markdown("**Conseils photo**")
    st.markdown(
        "- Pièce centrée et à plat\n"
        "- Éclairage diffus, sans reflet brûlé\n"
        "- Photo nette, résolution élevée\n"
        "- Même distance pour avers et revers\n"
        "- Ne pas appliquer de filtre"
    )

col1, col2 = st.columns(2)
with col1:
    st.subheader("Avers")
    obv_file = st.file_uploader("Téléverser l'avers", type=["jpg","jpeg","png","webp"], key="obv")
with col2:
    st.subheader("Revers")
    rev_file = st.file_uploader("Téléverser le revers", type=["jpg","jpeg","png","webp"], key="rev")

extra_files = st.file_uploader(
    "Photos additionnelles (optionnel : autre éclairage, gros plan, tranche)",
    type=["jpg","jpeg","png","webp"],
    accept_multiple_files=True,
)

if obv_file and rev_file:
    obv = Image.open(obv_file).convert("RGB")
    rev = Image.open(rev_file).convert("RGB")

    c1, c2 = st.columns(2)
    with c1:
        st.image(obv, caption="Avers", use_container_width=True)
    with c2:
        st.image(rev, caption="Revers", use_container_width=True)

    issues = validate_image(obv, "avers") + validate_image(rev, "revers")
    if issues:
        st.warning("Qualité photo : " + " ".join(issues))

    if st.button("Évaluer la pièce", type="primary", use_container_width=True):
        result = grade_coin(obv, rev, denomination, int(year), strike)

        st.divider()
        g1, g2, g3 = st.columns([1.1, 1, 1])
        g1.metric("Grade estimé", result["grade"])
        g2.metric("Indice numérique", f'{result["numeric_grade"]:.1f}/70')
        g3.metric("Confiance", f'{result["confidence"]:.0%}')

        low, high = result["range"]
        st.info(f"Fourchette plausible : **{low} à {high}**")

        st.subheader("Analyse visuelle")
        metrics_df = pd.DataFrame([
            ["Netteté / détails", result["metrics"]["detail_score"]],
            ["Qualité des surfaces", result["metrics"]["surface_score"]],
            ["Contraste / relief", result["metrics"]["contrast_score"]],
            ["Lustre (proxy photo)", result["metrics"]["luster_score"]],
            ["Pénalité marques", result["metrics"]["marks_penalty"]],
        ], columns=["Critère", "Score"])
        st.dataframe(metrics_df, hide_index=True, use_container_width=True)

        st.subheader("Interprétation")
        st.write(grade_explanation(result))

        if result["warnings"]:
            for w in result["warnings"]:
                st.warning(w)

        st.caption(
            "Important : le grading professionnel tient compte de facteurs difficiles à capturer sur deux photos "
            "(lustre en mouvement, hairlines, nettoyage, altérations, frappe faible, problèmes de surface, authenticité, etc.)."
        )

        with st.expander("Enregistrer un grade certifié pour améliorer une future version"):
            known = st.text_input("Grade réel/certifié (ex. ICCS MS-64)")
            cert = st.text_input("Certification / numéro (optionnel)")
            if st.button("Préparer l'exemple d'apprentissage"):
                if known.strip():
                    st.success(
                        "Dans une version avec base de données, cet exemple serait enregistré comme donnée étiquetée. "
                        "Le prototype livré n'envoie ni ne stocke automatiquement vos photos."
                    )
                else:
                    st.error("Inscris d'abord un grade certifié.")
else:
    st.info("Téléverse au minimum une photo de l'avers et une photo du revers.")

st.divider()
with st.expander("À propos de la méthode utilisée dans ce prototype"):
    st.write(
        "Cette première version utilise une analyse d'image locale (netteté, texture, contraste, "
        "densité de marques et proxies de lustre) afin de produire une estimation. "
        "Elle sert surtout à valider le parcours utilisateur. Pour obtenir un vrai modèle de grading, "
        "il faut entraîner un modèle sur un grand ensemble de pièces canadiennes dont le grade est connu."
    )
