# apis for ndp_d2 betaman edition
import requests
from owslib.wfs import WebFeatureService
from io import StringIO
import pandas as pd
import geopandas as gpd
import streamlit as st

mml_key = st.secrets['MML_MTK']
url_mt = 'https://avoin-paikkatieto.maanmittauslaitos.fi/maastotiedot/features/v1/collections/rakennus/items?'

@st.cache(allow_output_mutation=True)
def pno_data(kunta,vuosi=2021):
    url = 'http://geo.stat.fi/geoserver/postialue/wfs'  # vaestoruutu tai postialue
    wfs = WebFeatureService(url=url, version="2.0.0")
    layer = f'postialue:pno_tilasto_{vuosi}'
    data_ = wfs.getfeature(typename=layer, outputFormat='json')  # propertyname=['kunta'],
    gdf_all = gpd.read_file(data_)
    noneed = ['id', 'euref_x', 'euref_y', 'pinta_ala']
    paavodata = gdf_all.drop(columns=noneed)
    kuntakoodit = pd.read_csv('config/kunta_dict.csv', index_col=False, header=0).astype(str)
    kuntakoodit['koodi'] = kuntakoodit['koodi'].str.zfill(3)
    kunta_dict = pd.Series(kuntakoodit.kunta.values, index=kuntakoodit.koodi).to_dict()
    paavodata['kunta'] = paavodata['kunta'].apply(lambda x: kunta_dict[x])
    dict_feat = pd.read_csv('config/paavo2021_dict.csv', skipinitialspace=True, header=None, index_col=0,squeeze=True).to_dict()
    selkopaavo = paavodata.rename(columns=dict_feat).sort_values('Kunta')
    pno_valinta = selkopaavo[selkopaavo['Kunta'] == kunta].sort_values('Asukkaat yhteensä', ascending=False)
    return pno_valinta

@st.cache(allow_output_mutation=True)
def mtk_rak_pno(pno):
    # func to get buildings
    def mtk_rak(bbox,api_key=mml_key):
        bbox_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}" # need to be string for mml
        url_mt = 'https://avoin-paikkatieto.maanmittauslaitos.fi/maastotiedot/features/v1/collections/rakennus/items?'
        params = {
        'bbox': bbox_str,
        'bbox-crs':'http://www.opengis.net/def/crs/EPSG/0/3067',
        'crs':'http://www.opengis.net/def/crs/EPSG/0/3067'
        }
        r= requests.get(url = url_mt,params=params, auth=(api_key,''))
        gdf = gpd.read_file(StringIO(r.text))\
            .set_crs(epsg=3067, allow_override=True)\
                .iloc[:,3:]
        return gdf
    # func to get 1x1km grid to cover pno-areas
    def pno_grid(pno, year=2020):
        box = pno.to_crs(4326).total_bounds
        bounds = box[0], box[1], box[2], box[3]
        bbox = bounds + tuple(['urn:ogc:def:crs:EPSG::4326'])
        # set the query
        url = 'http://geo.stat.fi/geoserver/vaestoruutu/wfs'
        wfs = WebFeatureService(url=url, version="2.0.0")
        layer = 'vaestoruutu:vaki{}_1km'.format(year)
        data = wfs.getfeature(typename=layer, bbox=bbox, outputFormat='json')
        data = gpd.read_file(data)
        gdf = data.to_crs(epsg=3067)
        return gdf
    # get the grid over pno-areas
    pop = pno_grid(pno)
    # iterate grid cells to get buildings for each cell
    gdf_out = gpd.GeoDataFrame()
    for index, row in pop.iterrows():
        cellbox = row['geometry'].bounds
        gdf_out = gdf_out.append(mtk_rak(cellbox,mml_key), ignore_index=True)
    # classify
    def classify_kayttotarkoitus(gdf):
        gdf.loc[gdf["kayttotarkoitus"] == 1, 'kayttotarkoitus'] = "Asuinrakennus"
        gdf.loc[gdf["kayttotarkoitus"] == 2, 'kayttotarkoitus'] = "Liike- tai julkinen rakennus"
        gdf.loc[gdf["kayttotarkoitus"] == 3, 'kayttotarkoitus'] = "Lomarakennus"
        gdf.loc[gdf["kayttotarkoitus"] == 4, 'kayttotarkoitus'] = "Teollinen rakennus"
        gdf.loc[gdf["kayttotarkoitus"] == 5, 'kayttotarkoitus'] = "Kirkollinen rakennus"
        gdf.loc[gdf["kayttotarkoitus"] == 6, 'kayttotarkoitus'] = "Muu rakennus"
        gdf.loc[gdf["kayttotarkoitus"] == 7, 'kayttotarkoitus'] = "Luokittelematon"
        gdf.loc[gdf["kayttotarkoitus"] == 8, 'kayttotarkoitus'] = "Kirkkorakennus"
        return gdf

    def classify_kohdeluokka(gdf):
        gdf.loc[gdf["kohdeluokka"] == 42210, 'rakennustyyppi'] = "Asuinrakennus, kerrosluku määrittelemätön"
        gdf.loc[gdf["kohdeluokka"] == 42211, 'rakennustyyppi'] = "Asuinrakennus, 1-2 krs"
        gdf.loc[gdf["kohdeluokka"] == 42212, 'rakennustyyppi'] = "Asuinrakennus, 3- krs"

        gdf.loc[gdf["kohdeluokka"] == 42220, 'rakennustyyppi'] = "Liike- tai julkinen rakennus, kerrosluku määrittelemätön"
        gdf.loc[gdf["kohdeluokka"] == 42221, 'rakennustyyppi'] = "Liike- tai julkinen rakennus, 1-2 krs"
        gdf.loc[gdf["kohdeluokka"] == 42222, 'rakennustyyppi'] = "Liike- tai julkinen rakennus, 3- krs"

        gdf.loc[gdf["kohdeluokka"] == 42230, 'rakennustyyppi'] = "Lomarakennus, kerrosluku määrittelemätön"
        gdf.loc[gdf["kohdeluokka"] == 42231, 'rakennustyyppi'] = "Lomarakennus, 1-2 krs"
        gdf.loc[gdf["kohdeluokka"] == 42232, 'rakennustyyppi'] = "Lomarakennus, 3- krs"

        gdf.loc[gdf["kohdeluokka"] == 42240, 'rakennustyyppi'] = "Teollinen rakennus, kerrosluku määrittelemätön"
        gdf.loc[gdf["kohdeluokka"] == 42241, 'rakennustyyppi'] = "Teollinen rakennus, 1-2 krs"
        gdf.loc[gdf["kohdeluokka"] == 42242, 'rakennustyyppi'] = "Teollinen rakennus, 3- krs"

        gdf.loc[gdf["kohdeluokka"] == 42270, 'rakennustyyppi'] = "Kirkko"
        gdf.loc[gdf["kohdeluokka"] == 42250, 'rakennustyyppi'] = "Kirkollinen rakennus, kerrosluku määrittelemätön"
        gdf.loc[gdf["kohdeluokka"] == 42251, 'rakennustyyppi'] = "Kirkollinen rakennus, 1-2 krs"
        gdf.loc[gdf["kohdeluokka"] == 42252, 'rakennustyyppi'] = "Kirkollinen rakennus, 3- krs"

        gdf.loc[gdf["kohdeluokka"] == 42260, 'rakennustyyppi'] = "Muu rakennus, kerrosluku määrittelemätön"
        gdf.loc[gdf["kohdeluokka"] == 42261, 'rakennustyyppi'] = "Muu rakennus, 1-2 krs"
        gdf.loc[gdf["kohdeluokka"] == 42262, 'rakennustyyppi'] = "Muu rakennus, 3- krs"

        return gdf
    gdf_out = classify_kayttotarkoitus(gdf_out)
    gdf_out = classify_kohdeluokka(gdf_out)
    return gdf_out

# eipävissiin