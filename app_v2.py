import streamlit as st
from PIL import Image
from grading_engine_v2 import grade_coin_v2, validate_image
st.set_page_config(page_title='Canadian Coin Grader V2',layout='wide')
st.title('🇨🇦 Canadian Coin Grader V2 — Reference-Calibrated')
st.caption('Prototype de recherche: estimation photographique, pas une certification professionnelle.')
with st.sidebar:
    denomination=st.selectbox('Dénomination',['1-cent','5-cent','10-cent','25-cent','50-cent','1-dollar'])
    year=st.number_input('Année',1858,2026,1936,1)
    strike=st.selectbox('Frappe',['Business strike','Proof-Like','Specimen','Proof'])
c1,c2=st.columns(2)
with c1: obvf=st.file_uploader('Avers',type=['jpg','jpeg','png'],key='o')
with c2: revf=st.file_uploader('Revers',type=['jpg','jpeg','png'],key='r')
if obvf and revf:
    obv,rev=Image.open(obvf),Image.open(revf)
    c1.image(obv,use_container_width=True); c2.image(rev,use_container_width=True)
    issues=validate_image(obv,'avers')+validate_image(rev,'revers')
    for x in issues: st.warning(x)
    if st.button('Grader la pièce',type='primary'):
        r=grade_coin_v2(obv,rev,denomination,year,strike)
        st.metric('Grade estimé',r['grade'],f"Fourchette {r['range'][0]} – {r['range'][1]}")
        st.progress(r['confidence'],text=f"Confiance photographique: {r['confidence']:.0%}")
        st.write(f"**Avers:** {r['side_estimates']['obverse']}  |  **Revers:** {r['side_estimates']['reverse']}")
        cols=st.columns(5)
        for col,(k,v) in zip(cols,r['metrics'].items()): col.metric(k.replace('_',' ').title(),f'{v}/10')
        st.subheader('Pourquoi ce grade?')
        for x in r['reasons']: st.write('• '+x)
        st.subheader('Références les plus proches')
        st.dataframe(r['comparables'],use_container_width=True,hide_index=True)
        st.caption(f"Index local: {r['meta']['reference_count']} images de référence canadiennes gradées.")
