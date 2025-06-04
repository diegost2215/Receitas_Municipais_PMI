import pandas as pd
import streamlit as st
from copy import deepcopy
import requests
from datetime import datetime
import plotly.express as px

#Em desenvolvimento

st.set_page_config(layout ="wide", initial_sidebar_state="auto")
@st.cache_data
def load_data():
  cod_UG = 1
  data=pd.DataFrame()
  tipos_movimentos = ['Apropriação de retenção/consignação', 'Arrecadação de receita', 'Estorno de apropriação de retenção/consignação',
        'Estorno de arrecadação de receita', 'Estorno de reconhecimento de receita', 'Estorno de restituição de receita', 'Previsão de Receita',
        'Reconhecimento de receita', 'Restituição de receita', ]

  for year in range(2018,(datetime.now().year+1)):
    link = f'http://portaltransparencia.itajai.sc.gov.br/epublica-portal/rest/itajai/api/v1/receita?periodo_inicial=01/{year}&periodo_final=12/{year}&codigo_unidade={cod_UG}'
    r = requests.get(link)
    data_json = r.json()
    temp = pd.json_normalize(data_json['registros'], meta=[['registro', 'naturezaReceita', 'subdetalhamento3' ,'codigo'], ['registro', 'receita', 'tipoReceita'],['registro','unidadeGestora', 'codigo'],['registro','unidadeGestora', 'denominacao'],
                              ['registro', 'naturezaReceita', 'categoriaEconomica', 'denominacao'], ['registro','naturezaReceita', 'origem', 'denominacao'], ['registro','naturezaReceita', 'especie', 'denominacao'],
                              ['registro','naturezaReceita', 'rubrica', 'denominacao'],  ['registro', 'naturezaReceita', 'alinea', 'denominacao'],['registro', 'naturezaReceita', 'subalinea','denominacao'],
                              ['registro', 'naturezaReceita', 'subdetalhamento1','denominacao'], ['registro', 'naturezaReceita', 'subdetalhamento2','denominacao'], ['registro','naturezaReceita', 'subdetalhamento3','denominacao'], ['registro', 'listFonteRecursos']],
                              record_path=['registro','listMovimentos'])
    temp['Ano'], temp['Mês'], temp['Dia'] = temp['dataMovimento'].str.split("-", expand=True)[0], temp['dataMovimento'].str.split("-", expand=True)[1], temp['dataMovimento'].str.split("-", expand=True)[2]
    temp['Competência'] =  temp['Ano'] + "-"+ temp['Mês']
    temp['cod_UG'] = cod_UG

    temp_pivot = pd.pivot_table(temp,index = ['Ano', 'Mês', 'Competência', 'cod_UG', 'registro.naturezaReceita.categoriaEconomica.denominacao',
        'registro.naturezaReceita.origem.denominacao', 'registro.naturezaReceita.especie.denominacao',
        'registro.naturezaReceita.rubrica.denominacao', 'registro.naturezaReceita.alinea.denominacao',
        'registro.naturezaReceita.subalinea.denominacao','registro.naturezaReceita.subdetalhamento1.denominacao',
        'registro.naturezaReceita.subdetalhamento2.denominacao','registro.naturezaReceita.subdetalhamento3.denominacao',],
                                columns= 'tipoMovimento', values='valorMovimento', aggfunc='sum',fill_value=0 )
    temp_pivot.reset_index(inplace=True)

    for tipo in tipos_movimentos:
      if tipo not in temp_pivot.columns:
        temp_pivot.insert(len(temp_pivot.columns),tipo, 0)
    temp_pivot['lançado'] = temp_pivot['Reconhecimento de receita'] - temp_pivot['Estorno de reconhecimento de receita']

    temp_pivot['arrecadado'] = (temp_pivot['Arrecadação de receita'] +temp_pivot['Apropriação de retenção/consignação']+temp_pivot['Restituição de receita']-
                        temp_pivot['Estorno de apropriação de retenção/consignação']-temp_pivot['Estorno de arrecadação de receita']-
                        temp_pivot['Estorno de restituição de receita'])
    data = pd.concat([data, temp_pivot])



  dict_subalinea_propria = {"Imposto sobre a Propriedade Predial e Territorial Urbana":"IPTU",
  "Imposto sobre Transmissão “Inter Vivos” de Bens Imóveis e de Direitos Reais sobre Imóveis":"ITBI",
  "Impostos sobre Transmissão “Inter Vivos” de Bens Imóveis e de Direitos Reais sobre Imóveis":"ITBI",
  "Imposto sobre a Renda":"I. Renda",
  "Imposto sobre Serviços de Qualquer Natureza":"ISS",
  "Taxa":"Taxas",
  "Contribuição para o Custeio do Serviço de Iluminação Pública":"COSIP"}

  dict_subalinea_transferencias = {"Cota-Parte do ICMS":"ICMS",
  "Cota-Parte do IPI - Municípios":"IPI",
  "Cota-Parte do IPVA": "IPVA",
  "Cota-Parte do Fundo de Participação do Municípios":"FPM",
  "Cota-Parte do Fundo de Participação dos Municípios":"FPM",
  "FUNDEB":"FUNDEB¹"}

  for key in dict_subalinea_propria:
    mask = data['registro.naturezaReceita.subalinea.denominacao'].str.contains(key, case=False)
    data.loc[mask,'Classificação'] = dict_subalinea_propria[key]
    data.loc[mask,'Tipo'] = 'R. Própria'

  for key in dict_subalinea_transferencias:
    mask = data['registro.naturezaReceita.subalinea.denominacao'].str.contains(key, case=False)
    data.loc[mask,'Classificação'] = dict_subalinea_transferencias[key]
    data.loc[mask,'Tipo'] = 'Transferências'

  mask = data['registro.naturezaReceita.categoriaEconomica.denominacao']=='Receitas Correntes Intraorçamentárias'
  data.loc[mask,'Classificação'] = 'Receita Intraorçamentária'
  data.loc[mask,'Tipo'] = 'R. Própria'

  mask_a1 = data['registro.naturezaReceita.origem.denominacao'].str.contains("Transferências de Capital|Transferências Correntes", regex=True)
  data.loc[mask_a1,'Classificação'] = data.loc[mask_a1,'Classificação'].fillna('Outras Transferências')
  data.loc[mask_a1,'Tipo'] = data.loc[mask_a1,'Tipo'].fillna('Transferências')

  data['Classificação'] = data['Classificação'].fillna('Outras Receitas')
  data['Tipo'] = data['Tipo'].fillna('R. Própria')
  return data

def format_row_wise(styler, formatter):
    for row, row_formatter in formatter.items():
        row_num = styler.index.get_loc(row)

        for col_num in range(len(styler.columns)):
            styler._display_funcs[(row_num, col_num)] = row_formatter
    return styler


data = load_data()

st.header('Receitas Municipais - Em Desenvolvimento - Em Desenvolvimento', divider='red')


colA,colB = st.columns([0.8,0.2])
with colA:
  years = list(data['Ano'].unique())
  years.remove('2018')
  year =st.pills(label = '',options = years, selection_mode='single', default=str(datetime.now().year-1))     
  year_0 = str(int(year)-1)
  data_P0 = pd.pivot_table(data[data['Ano']==year_0], index='Classificação', columns='Mês', values='arrecadado', aggfunc='sum', fill_value=0)/1000000
  data_P0['Total'] = data_P0.sum(axis=1)
  data_P1 = pd.pivot_table(data[data['Ano']==year], index='Classificação', columns='Mês', values='arrecadado', aggfunc='sum', fill_value=0)/1000000
  data_P1['Total'] = data_P1.sum(axis=1)
  data_P1['Variação %'] = (data_P1['Total']-data_P0['Total'])/data_P0['Total']
  data_P1['Variação R$'] = (data_P1['Total']-data_P0['Total'])
  meses = {'01':'Janeiro', '02':'Fevereiro', '03':'Março', '04':'Abril', '05':'Maio', '06':'Junho', '07':'Julho', '08':'Agosto', '09':'Setembro', '10':'Outubro', '11':'Novembro', '12':'Dezembro'}
  data_P1.rename(columns=meses, inplace=True)
  data_P1_proprias = data_P1.loc[['COSIP','I. Renda', 'IPTU', 'ISS', 'ITBI', 'Outras Receitas',  'Taxas', 'Receita Intraorçamentária'],:]
  data_P1_transferencias = data_P1.loc[['FPM','FUNDEB¹', 'ICMS', 'IPI', 'IPVA', 'Outras Transferências'],:]
  data_proprias = data_P1_proprias.T.style.format('{:.2f}M', decimal=',')
  data_transf = data_P1_transferencias .T.style.format('{:.2f}M', decimal=',')
  formatters = {'Variação %':lambda x: f"{x:,.2%}"}
    
  data_proprias = deepcopy(format_row_wise(data_proprias, formatters))
  data_transf = deepcopy(format_row_wise(data_transf, formatters))
with colB:
   total_year = data_P1['Total'].sum()*1000000
   total_year_0 = data_P0['Total'].sum()*1000000
   delta = (total_year-total_year_0)/total_year_0*100
   st.metric(label = f"total arrecadado {year}", value = f"R$ {total_year:,.2f}", delta = f"{delta:.2f} %")


col1, col2 = st.columns([0.45,0.55])    
with col1:  

    
    st.subheader('Receitas Próprias (R$)',)
    st.table(data_proprias)   
    st.caption("")
    st.subheader('Transferências (R$)',)
    st.table(data_transf )
    
with col2:
   fig1 = px.treemap(data_frame=data[data['Ano']==year], values='arrecadado', path=['Ano','Tipo', 'Classificação',
       #'registro.naturezaReceita.subalinea.denominacao',
       'registro.naturezaReceita.subdetalhamento1.denominacao',
        'registro.naturezaReceita.subdetalhamento2.denominacao',
        'registro.naturezaReceita.subdetalhamento3.denominacao'], maxdepth=3, color='Classificação', color_discrete_map={'(?)':'black'}, 
        color_discrete_sequence=px.colors.qualitative.Set3, height = 520,)
   fig1.update_traces(textinfo='label+percent root+value')
   fig1.update_traces(hovertemplate='%{label}<br>Valor=R$ %{value}<extra></extra>')
   fig1.update_traces(textfont=dict(size=25))
   fig1.update_traces(marker=dict(cornerradius=8))
   fig1.update_layout(margin=dict(t=0, b=0))

   st.subheader('Estrutura da Receita', )
   st.plotly_chart(fig1, use_container_width=True,config = {'displayModeBar': False})   
   
   st.caption("")
   st.subheader('Evolução da Receita', )   
   colunas = st.pills(label = '', options = data['Classificação'].unique(), selection_mode = 'multi', default = ['ISS', 'ICMS'])
   data_p = pd.pivot_table(data, index=['Ano', 'Classificação'], aggfunc=sum, values='arrecadado')
   data_p.reset_index(inplace=True)        
   
   fig2 = px.bar(data_p[data_p['Classificação'].isin(colunas)], x="Ano", y="arrecadado",
             color='Classificação', barmode='group',
             height=400, title = 'Evolução das Receitas')
   fig2.update_layout(margin=dict(t=0, b=0))
   st.plotly_chart(fig2, use_container_width=True,  config = {'displayModeBar': False} )
   
   




