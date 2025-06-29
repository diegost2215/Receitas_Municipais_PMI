import pandas as pd
import streamlit as st
from copy import deepcopy
import requests
from datetime import date, datetime
import plotly.express as px

#Em desenvolvimento
mypallete = list(px.colors.qualitative.Antique) + list(px.colors.qualitative.T10)
st.set_page_config(layout ="wide", initial_sidebar_state="auto")


@st.cache_data(ttl ="1d")
def load_data():
  #data = pd.read_feather('teste_receitas.feather')  
  cod_UG = 1
  data=pd.DataFrame()
  tipos_movimentos = ['Apropriação de retenção/consignação', 'Arrecadação de receita', 'Estorno de apropriação de retenção/consignação',
                      'Estorno de arrecadação de receita', 'Estorno de reconhecimento de receita', 'Estorno de restituição de receita', 
                      'Previsão de Receita','Reconhecimento de receita', 'Restituição de receita', ]

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

    temp_pivot = pd.pivot_table(temp,index = ['Ano', 'Mês', 'Dia', 'Competência', 'cod_UG', 'registro.naturezaReceita.subdetalhamento3.codigo', 'registro.naturezaReceita.categoriaEconomica.denominacao',
        'registro.naturezaReceita.origem.denominacao', 'registro.naturezaReceita.especie.denominacao',
        'registro.naturezaReceita.rubrica.denominacao', 'registro.naturezaReceita.alinea.denominacao',
        'registro.naturezaReceita.subalinea.denominacao','registro.naturezaReceita.subdetalhamento1.denominacao',
        'registro.naturezaReceita.subdetalhamento2.denominacao','registro.naturezaReceita.subdetalhamento3.denominacao',],
                                columns= 'tipoMovimento', values='valorMovimento', aggfunc='sum',fill_value=0 )
    temp_pivot.reset_index(inplace=True)

    for tipo in tipos_movimentos:
      if tipo not in temp_pivot.columns:
        temp_pivot.insert(len(temp_pivot.columns),tipo, 0)

    temp_pivot['Lançado'] = temp_pivot['Reconhecimento de receita'] - temp_pivot['Estorno de reconhecimento de receita']
    temp_pivot['Arrecadação Líquida'] = (temp_pivot['Arrecadação de receita'] +temp_pivot['Apropriação de retenção/consignação']+temp_pivot['Restituição de receita']-
                        temp_pivot['Estorno de apropriação de retenção/consignação']-temp_pivot['Estorno de arrecadação de receita']-
                        temp_pivot['Estorno de restituição de receita'])




    data = pd.concat([data, temp_pivot])

  dict_subalinea_receitas = {"Imposto sobre a Propriedade Predial e Territorial Urbana":"IPTU",
  "Imposto sobre Transmissão “Inter Vivos” de Bens Imóveis e de Direitos Reais sobre Imóveis":"ITBI",
  "Impostos sobre Transmissão “Inter Vivos” de Bens Imóveis e de Direitos Reais sobre Imóveis":"ITBI",
  'Impostos sobre Transmissão "Inter Vivos" de Bens Imóveis e de Direitos Reais sobre Imóveis':"ITBI",
  "Imposto sobre a Renda":"I. Renda",
  "Imposto sobre Serviços de Qualquer Natureza":"ISS",
  "Taxa":"Taxas",
  "Taxass":"Taxas",
  "ISS - ISSQN":"ISS",
  "Contribuição para o Custeio do Serviço de Iluminação Pública":"COSIP",
  "Cota-Parte do ICMS":"ICMS",
  "Cota-Parte do IPI - Municípios":"IPI",
  "Cota-Parte do IPVA": "IPVA",
  "Cota-Parte do Fundo de Participação do Municípios":"FPM",
  "Cota-Parte do Fundo de Participação dos Municípios":"FPM",
  "FUNDEB":"FUNDEB¹"}


  for key in dict_subalinea_receitas:
    mask = data['registro.naturezaReceita.subalinea.denominacao'].str.contains(key, case=False)
    data.loc[mask,'Classificação'] = dict_subalinea_receitas[key]
    data['registro.naturezaReceita.subdetalhamento1.denominacao'] = data['registro.naturezaReceita.subdetalhamento1.denominacao'].str.replace(key,dict_subalinea_receitas[key], case=False)
    data['registro.naturezaReceita.subdetalhamento2.denominacao'] = data['registro.naturezaReceita.subdetalhamento2.denominacao'].str.replace(key,dict_subalinea_receitas[key], case=False)



  #mask_a1 = data['registro.naturezaReceita.origem.denominacao'].str.contains("Transferências Correntes", regex=True)
  mask_a1 = data['registro.naturezaReceita.subdetalhamento3.codigo'].str.startswith('17')
  data.loc[mask_a1,'Classificação'] = data.loc[mask_a1,'Classificação'].fillna('Outras Transferências')

  mask = data['registro.naturezaReceita.subdetalhamento3.codigo'].str.startswith('7')
  data.loc[mask,'Classificação'] = 'Receitas Correntes Intraorçamentárias'

  mask = data['registro.naturezaReceita.subdetalhamento3.codigo'].str.startswith('8')
  data.loc[mask,'Classificação'] = 'Receitas de Capital Intraorçamentárias'

  mask = data['registro.naturezaReceita.subdetalhamento3.codigo'].str.startswith('2')
  data.loc[mask,'Classificação'] = 'Receitas de Capital'

  data['Classificação'] = data['Classificação'].fillna('Outras Receitas')

  data['data_registro'] = pd.to_datetime(pd.DataFrame({'year': data['Ano'],'month': data['Mês'],'day': data['Dia']}))

  data_atualizacao = date.today()


  return data, data_atualizacao
  

'''
try:
  if data_atualizacao != date.today():
    load_data.clear()
except:
  pass
'''
data, data_atualizacao = load_data()

col0A,  col0B = st.columns([0.85,0.15])
with col0A:
   st.header('Painel de Receitas - Município de Itajaí - Em Desenvolvimento')
   #st.image(image='banner3 - Copia.png')
with col0B:
  st.caption('')
  st.caption('')
  st.caption(f'Última Atualização em {data_atualizacao}')


with st.container(border=True):
  col1A,col1B, col1D = st.columns([0.33,0.33, 0.33])
  with col1D:
    data_base = st.date_input('Selecione a data de referência', value="today", min_value="2019-01-01", max_value = 'today',
                              on_change=None, format="DD/MM/YYYY", disabled=False, label_visibility="visible",)

    data_until = pd.DataFrame()
    for year in range(2018, datetime.now().year+1):
      temp_until = data[(data['Ano'] == str(year)) & (data['data_registro'] <=datetime(year, data_base.month, data_base.day))]
      data_until = pd.concat([data_until, temp_until])

    data_until_arrecadado = pd.pivot_table(data_until, index=['Ano', 'Classificação'], aggfunc='sum', values='Arrecadação Líquida')
    data_until_arrecadado.rename(columns={'Arrecadação Líquida':'Arrecadação Líquida Parcial'}, inplace = True)
    receita_prevista = pd.pivot_table(data, index=['Ano', 'Classificação'], aggfunc='sum', values='Previsão de Receita')
    data_total_arrecadado = pd.pivot_table(data, index=['Ano', 'Classificação'], aggfunc='sum', values='Arrecadação Líquida')
    data_total_arrecadado.rename(columns={'Arrecadação Líquida':'Arrecadação Líquida Total'}, inplace=True)
    data_joined = pd.concat([receita_prevista, data_until_arrecadado, data_total_arrecadado], axis=1)
    data_joined.reset_index(inplace = True)
    data_joined['% Arrecadado da Previsão'] = data_joined['Arrecadação Líquida Parcial']/data_joined['Previsão de Receita']
    data_joined['% Arrecadado do total anual'] = data_joined['Arrecadação Líquida Parcial']/data_joined['Arrecadação Líquida Total']
    data_joined['% Arrecadado Total da Previsão'] = data_joined['Arrecadação Líquida Total']/data_joined['Previsão de Receita']
    data_joined_somado = pd.pivot_table(data_joined, index='Ano', aggfunc='sum', values = ['Arrecadação Líquida Parcial','Previsão de Receita', 'Arrecadação Líquida Total'])
    data_joined_somado['% Arrecadado da Previsão'] = data_joined_somado['Arrecadação Líquida Parcial']/data_joined_somado['Previsão de Receita']
    data_joined_somado.reset_index(inplace = True)
    year_today = data_base.year
    year_last = year_today - 1
    metric_A = (data_joined[data_joined['Ano'] == str(year_today)])['Previsão de Receita'].sum()/1000000
    metric_B = (data_joined[data_joined['Ano'] == str(year_today)])['Arrecadação Líquida Parcial'].sum()/1000000
    metric_A_0 = (data_joined[data_joined['Ano'] == str(year_last)])['Previsão de Receita'].sum()/1000000
    metric_B_0 = (data_joined[data_joined['Ano'] == str(year_last)])['Arrecadação Líquida Parcial'].sum()/1000000
    delta_A = (metric_A-metric_A_0)/metric_A_0
    delta_B = (metric_B-metric_B_0)/metric_B_0

  with col1A:
    st.metric(label = f"Receita Prevista - {year_today}", value = f"R$ {metric_A:.1f} milhões", delta = f"{delta_A:.2%} em relação à {year_last}")

  with col1B:
    st.metric(label = f'Total Arrecadado até {data_base.strftime("%d/%m/%y")}', value = f"R$ {metric_B:.1f} milhões", delta = f'{delta_B:.2%} em relação à {data_base.strftime("%d/%m")}/{year_last}' )


with st.container(border=True):
  col2A, col2B = st.columns([0.4,0.6])
  with col2A:
    fig2A = px.pie(data_until[data_until['Ano']==str(data_base.year)], values='Arrecadação Líquida', names='registro.naturezaReceita.origem.denominacao', color_discrete_sequence=mypallete, template ="plotly_white", hole =0.5, title =f'Origem das receitas arrecadadas até {data_base.strftime("%d/%m/%y")}')
    fig2A.update_traces(textposition='inside', textinfo='percent')
    fig2A.update_layout(uniformtext_minsize=12, uniformtext_mode='hide')
    fig2A.update_layout(title={'x': 0.5,'xanchor': 'center'} )    
    st.plotly_chart(fig2A, use_container_width =True,)
  with col2B:
    fig2B = px.bar(data_joined_somado, y="Ano", x='Arrecadação Líquida Parcial',title = f'Arrecadação Líquida até o dia {data_base.strftime("%d/%m")} de cada ano' ,
                  template = 'plotly_white', color = 'Ano',color_discrete_sequence=mypallete, orientation = 'h',  text_auto='.2s')
    fig2B.update_traces(width=1, texttemplate='R$ %{x:.3s}')    
    fig2B.update_layout(xaxis_title=None, yaxis_title=None, title={'x': 0.5,'xanchor': 'center'} )
    st.plotly_chart(fig2B,use_container_width=True,  config = {'staticPlot': True} )



arrecadacao_mensal_parcial_A = pd.pivot_table(data = data_until[data_until['Ano']==str(data_base.year)], index= ['Classificação', 'registro.naturezaReceita.origem.denominacao'], columns='Competência', values = 'Arrecadação Líquida', fill_value=0, aggfunc='sum')/1000000
arrecadacao_mensal_parcial_A["Total Atual"] = arrecadacao_mensal_parcial_A.sum(axis=1,numeric_only=True)
arrecadacao_mensal_parcial_0 = pd.pivot_table(data = data_until[data_until['Ano']==str(data_base.year-1)], index= ['Classificação', 'registro.naturezaReceita.origem.denominacao'], columns='Competência', values = 'Arrecadação Líquida', fill_value=0, aggfunc='sum')/1000000
arrecadacao_mensal_parcial_0["Ano Anterior"] = arrecadacao_mensal_parcial_0.sum(axis=1,numeric_only=True)
arrecadacao_mensal_parcial_A = arrecadacao_mensal_parcial_A.join(arrecadacao_mensal_parcial_0["Ano Anterior"], how='outer')
arrecadacao_mensal_parcial_A['Variação R$'] = arrecadacao_mensal_parcial_A['Total Atual'] - arrecadacao_mensal_parcial_A['Ano Anterior']
arrecadacao_mensal_parcial_A.sort_values(by='Total Atual', inplace= True,ascending=False)
arrecadacao_mensal_parcial_A.reset_index('registro.naturezaReceita.origem.denominacao'	,inplace=True)
arrecadacao_mensal_parcial_A.rename(columns={'registro.naturezaReceita.origem.denominacao':'Natureza da Receita - Origem', 'Classificação':'Receita'}, inplace=True)
arrecadacao_mensal_parcial_A.loc['Total'] = arrecadacao_mensal_parcial_A.sum(numeric_only=True)
arrecadacao_mensal_parcial_A['Variação %'] = (arrecadacao_mensal_parcial_A['Total Atual'] - arrecadacao_mensal_parcial_A['Ano Anterior'])/arrecadacao_mensal_parcial_A['Ano Anterior']
arrecadacao_mensal_parcial_A.fillna(0, inplace = True)
arrecadacao_mensal_parcial_A.rename_axis('Receita', inplace=True)
arrecadacao_mensal_parcial_A.at['Total', 'Natureza da Receita - Origem'] = ''
subset = list(arrecadacao_mensal_parcial_A.columns)[1:-1]
arrecadacao_mensal_parcial_A_format = arrecadacao_mensal_parcial_A.style.format(subset = subset, formatter='{:.2f}M', decimal=',')
arrecadacao_mensal_parcial_A_format.format(subset = 'Variação %', formatter ='{:.1%}')
#arrecadacao_mensal_parcial_A_format.set_caption(f'Arrecadação Líquida até {data_base.strftime("%d/%m")} de cada ano')
#arrecadacao_mensal_parcial_A_format

with st.expander(label = f'Detalhar mensalmente as receitas do ano {data_base.year}', expanded=False, icon=None, ):
  st.table(arrecadacao_mensal_parcial_A_format)

with st.container(border=True):
  colunas = st.pills(label = '', options = data_joined['Classificação'].unique(), selection_mode = 'multi', default = ['ISS', 'ICMS'])
  col3A, col3B = st.columns([0.5,0.5])
  with col3A:
    fig3B = px.bar(data_joined[data_joined['Classificação'].isin(colunas)], x="Ano", y='Arrecadação Líquida Parcial', title = f'Arrecadação Líquida por rúbrica até o dia {data_base.strftime("%d/%m")} de cada ano',
              color='Classificação', barmode='group',text_auto='.3s', color_discrete_sequence=mypallete, template ="plotly_white")
    fig3B.update_layout(uniformtext_minsize=10, uniformtext_mode='hide')    
    fig3B.update_layout(legend=dict(x = 0.5, y=-0.25,xanchor="center",yanchor="bottom", orientation='h'), xaxis_title=None, yaxis_title=None, title={'x': 0.5,'xanchor': 'center'},)    
    st.plotly_chart(fig3B, use_container_width=True,  config = {'staticPlot': True} )
  with col3B:
    
    fig3A = px.bar(data_joined[data_joined['Classificação'].isin(colunas)], x="Ano", y='% Arrecadado da Previsão', title = f'Arrecadação Líquida em função da Receita Prevista até o dia {data_base.strftime("%d/%m")} de cada ano',
                   color='Classificação', barmode='group',text_auto='.2%', color_discrete_sequence=mypallete, template ="plotly_white")
    
    fig3A.update_layout(uniformtext_minsize=10, uniformtext_mode='hide')    
    fig3A.update_layout(legend=dict(x = 0.5, y=-0.25,xanchor="center",yanchor="bottom", orientation='h'), xaxis_title=None, yaxis_title=None, title={'x': 0.5,'xanchor': 'center'},)    
    st.plotly_chart(fig3A, use_container_width=True,  config = {'staticPlot': True} )    

with st.container(border=True):
  #st.badge('Estrutura das Receitas', width  = 'stretch')
  fig4 = px.treemap(data_frame=data_until[data_until['Ano']==str(data_base.year)], values='Arrecadação Líquida',
                    path=['Ano', 'Classificação','registro.naturezaReceita.subdetalhamento1.denominacao','registro.naturezaReceita.subdetalhamento2.denominacao',],
                    maxdepth=2, color='Classificação', color_discrete_map={'(?)':'white'},
                    color_discrete_sequence=mypallete)
  fig4.update_traces(textinfo='label+percent root+value')
  fig4.update_traces(hovertemplate='%{label}<br>Valor=R$ %{value}<extra></extra>',textfont=dict(size=20), marker=dict(cornerradius=8), marker_line_color="black")
  fig4.update_layout(margin=dict(t=0, b=0))
  st.plotly_chart(fig4, use_container_width=True)
