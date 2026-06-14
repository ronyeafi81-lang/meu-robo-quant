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
        payload = {"chat_id": ID_TELEGRAM, "text": message, "parse_mode": "Markdown"} # Mantido a estrutura padrão solicitada anteriormente
        payload["text"] = mensagem # Garante a correção interna da variável
        requests.post(url, json=payload)
        time.sleep(1.2)
    except Exception as e:
        pass

# 1. Configuração de Tela Cheia e Tema do App
st.set_page_config(page_title="Terminal Quant - Scanner de Opções", layout="wide")
st.title("🛡️ Terminal Quantitativo & Scanner de Opções")
st.caption("Filtros automáticos baseados em IV Rank e Setups Técnicos para montagem de estratégias de Opções na B3.")

# =====================================================================
# MECANISMO DE ATUALIZAÇÃO AUTOMÁTICA (Roda o código sozinho a cada 5 min)
# =====================================================================
if "alertas_enviados" not in st.session_state:
    st.session_state.alertas_enviados = {}

@st.fragment(run_every=300)
def loop_principal():
    carteira = [
        "ABEV3.SA", "ALOS3.SA", "ALPA4.SA", "ARZZ3.SA", "ASAI3.SA", "AZUL4.SA", "B3SA3.SA", 
        "BBAS3.SA", "BBDC3.SA", "BBDC4.SA", "BBSE3.SA", "BEEF3.SA", "BPAC11.SA", "BRAP4.SA", 
        "BRCR11.SA", "BRFS3.SA", "BRKM5.SA", "CCRO3.SA", "CIEL3.SA", "CMIG4.SA", "CMIN3.SA", 
        "COGN3.SA", "CPFE3.SA", "CPLE6.SA", "CRFB3.SA", "CSAN3.SA", "CSNA3.SA", "CYRE3.SA", 
        "DIRR3.SA", "DXCO3.SA", "ELET3.SA", "ELET6.SA", "EMBR3.SA", "ENEV3.SA", "ENGI11.SA", 
        "EQTL3.SA", "EZTC3.SA", "FLRY3.SA", "GGBR4.SA", "GOAU4.SA", "GOLL4.SA", "HAPV3.SA", 
        "HYPE3.SA", "IGTI11.SA", "IRBR3.SA", "ITSA4.SA", "ITUB4.SA", "JBSS3.SA", "KLBN11.SA", 
        "LREN3.SA", "LWSA3.SA", "MGLU3.SA", "MRFG3.SA", "MRVE3.SA", "MULT3.SA", "NTCO3.SA", 
        "PCAR3.SA", "PETR3.SA", "PETR4.SA", "RECV3.SA", "RAIL3.SA", "RADL3.SA", "RAIZ4.SA", 
        "RENT3.SA", "RRRP3.SA", "SANB11.SA", "SBSPSP3.SA", "SUZB3.SA", "TAEE11.SA", "TIMS3.SA", 
        "TOTS3.SA", "TRPL4.SA", "UGPA3.SA", "USIM5.SA", "VALE3.SA", "VAMO3.SA", "VBBR3.SA", 
        "VIVA3.SA", "WEGE3.SA", "YDUQ3.SA"
    ]
    
    resultados = []
    dados_acoes = {}

    st.cache_data.clear()

    progresso = st.progress(0, text="Escaneando mercado para Opções...")
    total_ativos = len(carteira)

    for idx, ticker in enumerate(carteira):
        try:
            progresso.progress((idx + 1) / total_ativos, text=f"Analisando: {ticker}")
            acao = yf.Ticker(ticker)
            df = acao.history(period="350d")
            if len(df) < 252:
                continue
            dados_acoes[ticker] = df
            
            # --- DIMENSÕES DE PREÇO ---
            df['MME_9'] = df['Close'].ewm(span=9, adjust=False).mean()
            df['MMA_21'] = df['Close'].rolling(window=21).mean()
            df['MMA_80'] = df['Close'].rolling(window=80).mean()
            df['MMA_200'] = df['Close'].rolling(window=200).mean()
            
            ultimo_preço = df['Close'].iloc[-1]
            
            # --- CÁLCULO DA VOLATILIDADE HISTÓRICA (BASE DO IV RANK) ---
            df['Retornos'] = df['Close'].pct_change()
            df['Vol_21d'] = df['Retornos'].rolling(window=21).std() * np.sqrt(252) * 100
            
            historico_vol = df['Vol_21d'].tail(252).dropna()
            if len(historico_vol) < 200:
                continue
                
            iv_atual = historico_vol.iloc[-1]
            iv_minimo = historico_vol.min()
            iv_maximo = historico_vol.max()
            
            # IV RANK FORMULA
            if iv_maximo != iv_minimo:
                iv_rank = ((iv_atual - iv_minimo) / (iv_maximo - iv_minimo)) * 100
            else:
                iv_rank = 0.0
                
            # IV PERCENTIL FORMULA
            dias_menores = (historico_vol < iv_atual).sum()
            iv_percentil = (dias_menores / 252) * 100
            
            # --- SCANNER DE SETUPS TÉCNICOS ---
            direcao_mercado = "Neutro"
            sinal_setup = "Aguardando Padrão"
            
            c = df['Close'].values
            o = df['Open'].values
            h = df['High'].values
            l = df['Low'].values
            mme9 = df['MME_9'].values
            mma21 = df['MMA_21'].values
            
            if mme9[-1] > mme9[-2] and mme9[-2] <= mme9[-3]:
                sinal_setup = "9.1 COMPRA"
                direcao_mercado = "Alta"
            elif mme9[-1] < mme9[-2] and mme9[-2] >= mme9[-3]:
                sinal_setup = "9.1 VENDA"
                direcao_mercado = "Baixa"
            elif mme9[-1] > mme9[-2]:
                if c[-1] < c[-2] and c[-1] < o[-1]:
                    sinal_setup = "9.2/9.3 Armado (Compra)"
                    direcao_mercado = "Alta"
            elif mme9[-1] < mme9[-2]:
                if c[-1] > c[-2] and c[-1] > o[-1]:
                    sinal_setup = "9.2/9.3 Armado (Venda)"
                    direcao_mercado = "Baixa"
                
            if sinal_setup == "Aguardando Padrão":
                if c[-1] > mma21[-1] and l[-1] <= mma21[-1] and mma21[-1] > mma21[-2]:
                    sinal_setup = "PC COMPRA"
                    direcao_mercado = "Alta"
                elif c[-1] < mma21[-1] and h[-1] >= mma21[-1] and mma21[-1] < mma21[-2]:
                    sinal_setup = "PC VENDA"
                    direcao_mercado = "Baixa"

            # --- INTELIGÊNCIA ARTIFICIAL DE ESTRATÉGIAS DE OPÇÕES ---
            estrategia_sugerida = "Aguardar Oportunidade"
            cor_alerta = "⚪"

            # Cenário 1: Volatilidade Extremamente Alta (Ideal para Vender Opções / Crédito)
            if iv_rank >= 70:
                if direcao_mercado == "Alta":
                    estrategia_sugerida = "💎 Trava de Alta com Put (Crédito) / Lançamento Coberto"
                    cor_alerta = "🟢"
                elif direcao_mercado == "Baixa":
                    estrategia_sugerida = "💎 Trava de Baixa com Call (Crédito)"
                    cor_alerta = "🔴"
                else:
                    estrategia_sugerida = "💎 Venda de Volatilidade Neutra (Iron Condor / Straddle Vendido)"
                    cor_alerta = "🔵"
            
            # Cenário 2: Volatilidade Extremamente Baixa (Ideal para Comprar Opções / Débito)
            elif iv_rank <= 25:
                if direcao_mercado == "Alta":
                    estrategia_sugerida = "⚡ Compra Seca de Call / Trava de Alta com Call (Débito)"
                    cor_alerta = "🟢"
                elif direcao_mercado == "Baixa":
                    estrategia_sugerida = "⚡ Compra Seca de Put / Trava de Baixa com Put (Débito)"
                    cor_alerta = "🔴"
                else:
                    estrategia_sugerida = "⚡ Compra de Volatilidade Neutra (Straddle / Strangle Comprado)"
                    cor_alerta = "🔵"
            
            # Cenário 3: Volatilidade Média (Foco total no Direcional do Gráfico)
            else:
                if direcao_mercado == "Alta":
                    estrategia_sugerida = "📈 Call Spread (Trava de Alta) / Compra de Call"
                    cor_alerta = "🟢"
                elif direcao_mercado == "Baixa":
                    estrategia_sugerida = "📉 Put Spread (Trava de Baixa) / Compra de Put"
                    cor_alerta = "🔴"

            ticker_nome = ticker.replace('.SA', '')
            
            # --- DISPARO AUTOMÁTICO PARA TELEGRAM ---
            if estrategia_sugerida != "Aguardar Oportunidade" and direcao_mercado != "Neutro":
                chave_alerta = f"{ticker_nome}_{sinal_setup}_opt"
                if chave_alerta not in st.session_state.alertas_enviados:
                    msg = (
                        f"🎯 OPORTUNIDADE DE OPÇÕES 🎯\n\n"
                        f"🔹 Ativo Objeto: {ticker_nome}\n"
                        f"💰 Preço da Ação: R$ {ultimo_preço:.2f}\n"
                        f"🔥 IV Rank: {iv_rank:.1f}% | IV Percentil: {iv_percentil:.1f}%\n"
                        f"📊 Setup Técnico: {sinal_setup}\n"
                        f"🛠️ Estratégia Recomendada: {estrategia_sugerida}\n\n"
                        f"🤖 Filtro quantitativo gerado automaticamente."
                    )
                    enviar_alerta_telegram(msg)
                    st.session_state.alertas_enviados[chave_alerta] = True

            resultados.append({
                "Sinal": cor_alerta,
                "Acao (Ativo Objeto)": ticker_nome,
                "Preco Atual": f"R$ {ultimo_preço:.2f}",
                "IV Rank": f"{iv_rank:.1f}%",
                "IV Percentil": f"{iv_percentil:.1f}%",
                "Setup Gráfico": sinal_setup,
                "Estratégia Sugerida de Opções": estrategia_sugerida
            })
        except Exception as e:
            pass

    progresso.empty()

    # --- VISUALIZAÇÃO INTERNA ---
    st.subheader("📋 Matriz de Estratégias para Opções B3")
    
    # Transforma em DataFrame para ordenar os melhores cenários no topo
    df_resultados = pd.DataFrame(resultados)
    if not df_resultados.empty:
        # Coloca as ações com oportunidade ativa ou volatilidade extrema primeiro
        df_resultados = df_resultados.sort_values(by=["IV Rank"], ascending=False)
        st.dataframe(df_resultados, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📊 Gráfico Técnico de Apoio")

    if resultados:
        acao_selecionada = st.selectbox("Selecione a Ação para Analisar:", [r["Acao (Ativo Objeto)"] for r in resultados])
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

# Executa o loop estável
loop_principal()
st.success("Scanner de Opções rodando! Oportunidades estruturadas sendo enviadas ao Telegram.")
