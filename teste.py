import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import requests
import time

# =====================================================================
# CONFIGURAÇÃO DO TELEGRAM (INSIRA SEUS DADOS REAIS ABAIXO)
# =====================================================================
TOKEN_TELEGRAM = "8811939851:AAFK5KsKWEzfn2vU7WuHtKYi4gMi8hsbGpA"
ID_TELEGRAM = "971501251"
# =====================================================================

def enviar_alerta_telegram(mensagem):
    """Função automática que dispara o alerta para o Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
        payload = {"chat_id": 971501251, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
        time.sleep(1.2)
    except Exception as e:
        pass

# 1. Configuração de Tela Cheia e Tema do App
st.set_page_config(page_title="Terminal Quant - Alertas Automáticos", layout="wide")
st.title("🛡️ Terminal Quantitativo Avançado")
st.caption("Scanner de setups com atualização automática e alertas no Telegram.")

# =====================================================================
# MECANISMO DE ATUALIZAÇÃO AUTOMÁTICA (Roda o código sozinho a cada 5 min)
# =====================================================================
@st.fragment(run_every=300)
def loop_principal():
    carteira = ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "MGLU3.SA", "BBAS3.SA", "BBDC4.SA"]
    resultados = []
    dados_acoes = {}

    if "alertas_enviados" not in st.session_state:
        st.session_state.alertas_enviados = {}

    # Força o yfinance a buscar dados novos da B3 a cada ciclo
    st.cache_data.clear()

    for ticker in carteira:
        try:
            acao = yf.Ticker(ticker)
            df = acao.history(period="300d")
            if len(df) < 200:
                continue
            dados_acoes[ticker] = df
            
            # --- DIMENSÕES DE PREÇO ---
            df['MME_9'] = df['Close'].ewm(span=9, adjust=False).mean()
            df['MMA_21'] = df['Close'].rolling(window=21).mean()
            df['MMA_80'] = df['Close'].rolling(window=80).mean()
            df['MMA_200'] = df['Close'].rolling(window=200).mean()
            
            ultimo_preço = df['Close'].iloc[-1]
            
            # --- DIMENSÕES DE VOLATILIDADE ---
            df['Retornos'] = df['Close'].pct_change()
            vol_historica_21d = df['Retornos'].tail(21).std() * np.sqrt(252) * 100
            vol_implicita_est = df['Retornos'].tail(30).std() * np.sqrt(252) * 1.15 * 100
            
            df['HV_Anualizada'] = df['Retornos'].rolling(window=21).std() * np.sqrt(252) * 100
            historico_hvs = df['HV_Anualizada'].tail(252).dropna()
            
            min_hv = historico_hvs.min()
            max_hv = historico_hvs.max()
            atual_hv = vol_historica_21d
            
            if max_hv != min_hv:
                iv_rank = ((atual_hv - min_hv) / (max_hv - min_hv)) * 100
            else:
                iv_rank = 0.0
                
            iv_percentil = (historico_hvs < atual_hv).sum() / len(historico_hvs) * 100
            
            # --- SCANNER DE SETUPS TÉCNICOS ---
            sinal_setup = "Aguardando Padrão"
            
            c = df['Close'].values
            o = df['Open'].values
            h = df['High'].values
            l = df['Low'].values
            mme9 = df['MME_9'].values
            mma21 = df['MMA_21'].values
            
            if mme9[-1] > mme9[-2] and mme9[-2] <= mme9[-3]:
                sinal_setup = "🚀 9.1 COMPRA"
            elif mme9[-1] < mme9[-2] and mme9[-2] >= mme9[-3]:
                sinal_setup = "📉 9.1 VENDA"
            elif mme9[-1] > mme9[-2]:
                if c[-1] < c[-2] and c[-1] < o[-1]:
                    sinal_setup = "🔍 9.2/9.3 Armado (Compra)"
            elif mme9[-1] < mme9[-2]:
                if c[-1] > c[-2] and c[-1] > o[-1]:
                    sinal_setup = "🔍 9.2/9.3 Armado (Venda)"
                    
            if sinal_setup == "Aguardando Padrão":
                if c[-1] > mma21[-1] and l[-1] <= mma21[-1] and mma21[-1] > mma21[-2]:
                    sinal_setup = "🎯 PC COMPRA"
                elif c[-1] < mma21[-1] and h[-1] >= mma21[-1] and mma21[-1] < mma21[-2]:
                    sinal_setup = "🎯 PC VENDA"

            ticker_nome = ticker.replace('.SA', '')
            
            # --- DISPARO AUTOMÁTICO ---
            if sinal_setup != "Aguardando Padrão":
                chave_alerta = f"{ticker_nome}_{sinal_setup}"
                if chave_alerta not in st.session_state.alertas_enviados:
                    msg = (
                        f"🚨 ALERTA QUANT AUTOMÁTICO 🚨\n\n"
                        f"🔹 Ativo: {ticker_nome}\n"
                        f"💰 Preço: R$ {ultimo_preço:.2f}\n"
                        f"📊 Setup: {sinal_setup}\n"
                        f"🔥 IV Rank: {iv_rank:.1f}%\n\n"
                        f"🤖 Notificação enviada automaticamente pelo seu robô."
                    )
                    enviar_alerta_telegram(msg)
                    st.session_state.alertas_enviados[chave_alerta] = True

            resultados.append({
                "Acao": ticker_nome,
                "Preco": f"R$ {ultimo_preço:.2f}",
                "Vol.Historica": f"{vol_historica_21d:.1f}%",
                "Vol.Implicita": f"{vol_implicita_est:.1f}%",
                "IV Rank": f"{iv_rank:.1f}%",
                "IV Percentil": f"{iv_percentil:.1f}%",
                "Setup": sinal_setup
            })
        except Exception as e:
            pass

    # --- VISUALIZAÇÃO INTERNA DO FRAGMENT ---
    st.subheader("📋 Matriz Quantitativa")
    st.dataframe(resultados)

    st.markdown("---")
    st.subheader("📊 Gráfico Técnico (4 Médias Móveis)")

    if resultados:
        acao_selecionada = st.selectbox("Selecione a Ação:", [r["Acao"] for r in resultados])
        ticker_completo = acao_selecionada + ".SA"

        if ticker_completo in dados_acoes:
            df_grafico = dados_acoes[ticker_completo].tail(60)
            
            fig = go.Figure(data=[go.Candlestick(
                x=df_grafico.index, open=df_grafico['Open'], high=df_grafico['High'],
                low=df_grafico['Low'], close=df_grafico['Close'], name="Preço"
            )])
            
            fig.add_trace(go.Scatter(x=df_grafico.index, y=df_grafico['MME_9'], mode='lines', name='MME 9', line=dict(color='cyan', width=1.5)))
            fig.add_trace(go.Scatter(x=df_grafico.index, y=df_grafico['MMA_21'], mode='lines', name='MMA 21', line=dict(color='lightgreen', width=1.5)))
            fig.add_trace(go.Scatter(x=df_grafico.index, y=df_grafico['MMA_80'], mode='lines', name='MMA 80', line=dict(color='orange', width=2)))
            fig.add_trace(go.Scatter(x=df_grafico.index, y=df_grafico['MMA_200'], mode='lines', name='MMA 200', line=dict(color='red', width=2.5)))
            
            fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

# Executa o loop
loop_principal()
st.success("Monitoramento ativo. O painel se atualiza sozinho a cada 5 minutos!")