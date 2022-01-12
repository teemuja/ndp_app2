# ndp d2 app for smoooth rdm...
import streamlit as st
import pandas as pd
import numpy as np

from st_aggrid import AgGrid
import plotly.express as px

from apis import pno_data
from apis import mtk_rak_pno
from apis import pno_hist

# page setup
st.set_page_config(page_title="NDP App d3", layout="wide")
padding = 2
st.markdown(f""" <style>
    .reportview-container .main .block-container{{
        padding-top: {padding}rem;
        padding-right: {padding}rem;
        padding-left: {padding}rem;
        padding-bottom: {padding}rem;
    }} </style> """, unsafe_allow_html=True)

header = '<p style="font-family:sans-serif; color:grey; font-size: 12px;">\
        NDP project app2 V0.77 "Another Betaman"\
        </p>'
st.markdown(header, unsafe_allow_html=True)
# plot size setup
#px.defaults.width = 600
px.defaults.height = 600

# page title
header_title = '''
:see_no_evil: **Naked Density Project**
'''
st.subheader(header_title)
header_text = '''
<p style="font-family:sans-serif; color:Dimgrey; font-size: 12px;">
Naked Density Projekti on <a href="https://github.com/teemuja" target="_blank">Teemu Jaman</a> väitöskirjatutkimus Aalto Yliopistossa.
Projektissa tutkitaan maankäytön tehokkuuden ja kaupunkirakenteen fyysisten piirteiden
vaikutuksia kestävään kehitykseen data-analytiikan avulla.
</p>
'''
st.markdown(header_text, unsafe_allow_html=True)

st.markdown("""---""")
st.title('Rakennukset postinumeroalueittain Suomessa')

kuntakoodit = pd.read_csv('config/kunta_dict.csv', index_col=False, header=0).astype(str)
kuntalista = kuntakoodit['kunta'].tolist()
default_ix = kuntalista.index('Espoo')
st.title(':point_down:')
# kuntavalitsin
valinta = st.selectbox('Valitse kunta ja taulukosta postinumeroalue', kuntalista, index=default_ix)
# hae pno data..
taulukkodata = pno_data(valinta)

# scat
with st.expander(f"Kuntagraafi {valinta}"):
    featlist = taulukkodata.columns.tolist()
    default_x = featlist.index('Rakennukset yhteensä')
    default_y = featlist.index('Asukkaat yhteensä')
    col1,col2 = st.columns([1,1])
    xaks = col1.selectbox('Valitse X-akselin tieto', featlist, index=default_x)
    yaks = col2.selectbox('Valitse Y-akselin tieto', featlist, index=default_y)

    @st.cache(allow_output_mutation=True)
    def scatplot1(df):
        scat1 = px.scatter(df, x=xaks, y=yaks, color='Postinumeroalueen nimi',
                           hover_name='Postinumeroalueen nimi')
        scat1.update_layout(legend={'traceorder': 'normal'})
        return scat1
    scat1 = scatplot1(taulukkodata)
    st.plotly_chart(scat1, use_container_width=True)
    # save csv nappi
    pno_csv = taulukkodata.to_crs(4326).to_csv().encode('utf-8')
    st.download_button(label="Lataa postinumeroalueet CSV-tiedostona", data=pno_csv, file_name=f'pno-alueet_{valinta}.csv',mime='text/csv')

# TABLE ..
from st_aggrid.grid_options_builder import GridOptionsBuilder

gb = GridOptionsBuilder.from_dataframe(taulukkodata)
gb.configure_selection(selection_mode="single", use_checkbox=True)  # (selection_mode="multiple", use_checkbox=True)
gridOptions = gb.build()
from st_aggrid.shared import GridUpdateMode

data = AgGrid(taulukkodata,
              gridOptions=gridOptions,
              enable_enterprise_modules=False,
              allow_unsafe_jscode=True,
              update_mode=GridUpdateMode.SELECTION_CHANGED)
selected_row = data["selected_rows"]
pno_alue = pd.DataFrame(selected_row) # valinta taulukosta

# map
if len(selected_row) != 0:
    with st.expander("Postinumeroalueen rakennukset kartalla", expanded=True):
        pno_alue_nimi = pno_alue['Postinumeroalueen nimi'][0]
        pno_plot = taulukkodata[taulukkodata['Postinumeroalueen nimi'] == pno_alue_nimi]
        rak = mtk_rak_pno(pno_plot)
        # tehokkuusluvut
        rak['kerrosala-arvio'] = 0
        rak.loc[rak['kerrosluku'] == 2, 'kerrosala-arvio'] = rak.area * 5.5
        rak.loc[rak['kerrosluku'] == 1, 'kerrosala-arvio'] = rak.area * 1.4

        col_show = ['rakennustyyppi','kayttotarkoitus','kerrosala-arvio','geometry']
        plot = pno_plot.overlay(rak,how='intersection')[col_show].to_crs(4326)
        plot['kerrosala-arvio'] = (plot['kerrosala-arvio'] / 10).apply(np.ceil).astype(int) * 10
        # plot
        lat = plot.unary_union.centroid.y
        lon = plot.unary_union.centroid.x
        fig = px.choropleth_mapbox(plot,
                                   geojson=plot.geometry,
                                   locations=plot.index,
                                   color=plot['kayttotarkoitus'].astype(str),
                                   hover_name="kayttotarkoitus",
                                   hover_data=['kerrosala-arvio'],
                                   mapbox_style="carto-positron",
                                   #color_continuous_scale=px.colors.qualitative.G10,
                                   color_discrete_map={
                                       "Asuinrakennus": "brown",
                                       "Liike- tai julkinen rakennus": "orange",
                                       "Lomarakennus": "yellow",
                                       "Teollinen rakennus": "grey",
                                       "Muu rakennus": "black",
                                       "Luokittelematon": "light grey",
                                       "Kirkkorakennus": "magenta",
                                       "Kirkollinen rakennus": "purple"},
                                   center={"lat": lat, "lon": lon},
                                   zoom=13,
                                   opacity=0.8,
                                   width=1200,
                                   height=700
                                   )
        fig.update_layout(title_text="Plot", margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=700)

        # generate plot
        with st.spinner('Kokoaa rakennuksia...'):
            st.plotly_chart(fig, use_container_width=True)

            def raks_to_csv(df):
                df_csv = df.drop(columns=['kerrosala-arvio'])
                return df_csv.to_csv().encode('utf-8')
            raks_csv = raks_to_csv(plot.round(0))
            st.download_button(label="Lataa rakennukset CSV-tiedostona", data=raks_csv, file_name=f'rakennukset_{pno_alue_nimi}.csv', mime='text/csv')

    with st.expander("Kerrosalamäärän jakautuminen"):
        with st.spinner('Analysoi rakennuksia...'):
            # poista ääripäät histogrammia varten
            high_limit = plot['kerrosala-arvio'].quantile(0.98)
            low_limit = plot['kerrosala-arvio'].quantile(0.02)
            plot_out = plot[(plot['kerrosala-arvio'] < high_limit) & (plot['kerrosala-arvio'] > low_limit)]
            #kemvalinta = st.radio('Valitse:',('kerrosala-arvio','klusterikerrosala'))
            fig_h = px.histogram(plot_out,
                                 title=f'{pno_alue_nimi} - Kerrosalahistogrammi',
                                 x='kerrosala-arvio', color="kayttotarkoitus", barmode="overlay",
                                 color_discrete_map={
                                     "Asuinrakennus": "brown",
                                     "Liike- tai julkinen rakennus": "orange",
                                     "Lomarakennus": "yellow",
                                     "Teollinen rakennus": "grey",
                                     "Muu rakennus": "black",
                                     "Luokittelematon": "light grey",
                                     "Kirkkorakennus": "magenta",
                                     "Kirkollinen rakennus": "purple"},
                                 labels = {
                                    "kerrosala-arvio": "Rakennuskohtaisten kerrosalamäärien jakauma",
                                    "kayttotarkoitus": "Käyttötarkoitus"
                                 }
                                 )
            st.plotly_chart(fig_h, use_container_width=True)

        selite = '''
        Kerrosala-arviot ovat karkeita arvioita maastotietokannan rakennusten kerroslukuluokan ja rakennustyypin perusteella.
        ([MML](https://www.maanmittauslaitos.fi/rakennusten-kyselypalvelu/tekninen-kuvaus))
        Huom! Ala- ja yläkvantaaliprosentit (pienimmät ja suurimmat rakennukset) on poistettu graafista.
        '''
        st.markdown(selite, unsafe_allow_html=True)

with st.expander(f"Aluekehitys {pno_alue_nimi}"):
    historia = pno_hist(valinta,pno_alue_nimi)
    cols = historia.drop(columns=['index','Postinumeroalueen nimi','Vuosi']).columns.tolist()
    selected_cols = st.multiselect('Valitse tiedot',cols)
    fig_pno_hist = px.line(historia, x="Vuosi", y=selected_cols, log_y=False)
    st.plotly_chart(fig_pno_hist, use_container_width=True)

footer_title = '''
---
:see_no_evil: **Naked Density Project**
[![MIT license](https://img.shields.io/badge/License-MIT-yellow.svg)](https://lbesson.mit-license.org/) 
'''
st.markdown(footer_title)
