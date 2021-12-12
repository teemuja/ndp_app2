# ndp d2 app for smoooth rdm...
import streamlit as st
import pandas as pd
import numpy as np

from st_aggrid import AgGrid
import plotly.express as px

from apis import pno_data
from apis import mtk_rak_pno

# page setups
st.set_page_config(page_title="NDP App d2", layout="wide")
padding = 3
st.markdown(f""" <style>
    .reportview-container .main .block-container{{
        padding-top: {padding}rem;
        padding-right: {padding}rem;
        padding-left: {padding}rem;
        padding-bottom: {padding}rem;
    }} </style> """, unsafe_allow_html=True)

header = '<p style="font-family:sans-serif; color:grey; font-size: 12px;">\
        NDP project app2 V0.75 "Another Betaman"\
        </p>'
st.markdown(header, unsafe_allow_html=True)

# page title
header_title = '''
:see_no_evil: **Naked Density Project**
'''
st.subheader(header_title)
st.markdown("""---""")
st.title('Rakennukset postinumeroalueittain Suomessa')

kuntakoodit = pd.read_csv('config/kunta_dict.csv', index_col=False, header=0).astype(str)
kuntalista = kuntakoodit['kunta'].tolist()
default_ix = kuntalista.index('Espoo')
st.title(':point_down:')
valinta = st.selectbox('Valitse kunta ja taulukosta postinumeroalue', kuntalista, index=default_ix)
taulukkodata = pno_data(valinta)

# TABLE ..
from st_aggrid.grid_options_builder import GridOptionsBuilder

gb = GridOptionsBuilder.from_dataframe(taulukkodata)
gb.configure_selection(selection_mode="single", use_checkbox=True)  # (selection_mode="multiple", use_checkbox=True)
gridOptions = gb.build()
from st_aggrid.shared import GridUpdateMode

data = AgGrid(taulukkodata,
              gridOptions=gridOptions,
              enable_enterprise_modules=True,
              allow_unsafe_jscode=True,
              update_mode=GridUpdateMode.SELECTION_CHANGED)

selected_row = data["selected_rows"]
pno_alue = pd.DataFrame(selected_row)

# map
if len(selected_row) != 0:
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
                               opacity=0.5,
                               width=1200,
                               height=700
                               )
    fig.update_layout(title_text="Plot", margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=700)

    # generate plot
    with st.spinner('Kokoaa rakennuksia...'):
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Kerrosalamäärän jakautuminen"):
        with st.spinner('Analysoi rakennuksia...'):
            # poista ääripäät histogrammia varten
            high_limit = plot['kerrosala-arvio'].quantile(0.98)
            low_limit = plot['kerrosala-arvio'].quantile(0.02)
            plot_out = plot[(plot['kerrosala-arvio'] < high_limit) & (plot['kerrosala-arvio'] > low_limit)]
            #kemvalinta = st.radio('Valitse:',('kerrosala-arvio','klusterikerrosala'))
            fig_h = px.histogram(plot_out,
                                 title=f'{pno_alue_nimi} - Kerrosalahistogrammi (kvantaalit 2-98%)',
                                 x='kerrosala-arvio', color="kayttotarkoitus", barmode="overlay",
                                 color_discrete_map={
                                     "Asuinrakennus": "brown",
                                     "Liike- tai julkinen rakennus": "orange",
                                     "Lomarakennus": "yellow",
                                     "Teollinen rakennus": "grey",
                                     "Muu rakennus": "black",
                                     "Luokittelematon": "light grey",
                                     "Kirkkorakennus": "magenta",
                                     "Kirkollinen rakennus": "purple"}
                                 )
            st.plotly_chart(fig_h, use_container_width=True)

        selite = '''
        Kerrosala-arviot ovat karkeita arvioita maastotietokannan rakennusten kerroslukuluokan ja rakennustyypin perusteella.
        ([MML](https://www.maanmittauslaitos.fi/rakennusten-kyselypalvelu/tekninen-kuvaus))
        '''
        st.markdown(selite, unsafe_allow_html=True)

        def df_csv(df):
            df_csv = df.drop(columns=['kerrosala-arvio'])
            return df_csv.to_csv().encode('utf-8')
        csv = df_csv(plot.round(0))
        st.download_button(label="Lataa rakennukset CSVnä", data=csv, file_name=f'rakennukset_{pno_alue_nimi}.csv', mime='text/csv')


footer_title = '''
---
:see_no_evil: **Naked Density Project** 
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
'''
st.markdown(footer_title) # https://gist.github.com/rxaviers/7360908

footer_fin = '<p style="font-family:sans-serif; color:grey; font-size: 12px;">\
        Naked Density Projekti on osa Teemu Jaman väitöskirjatutkimusta Aalto Yliopistossa. \
        Projektissa tutkitaan maankäytön tehokkuuden ja kaupunkirakenteen fyysisten piirteiden\
        vaikutuksia palveluiden kehittymiseen data-analytiikan ja koneoppimisen avulla.\
        </p>'

st.markdown(footer_fin, unsafe_allow_html=True)