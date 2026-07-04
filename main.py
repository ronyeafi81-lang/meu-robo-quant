import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import requests
import time

# =====================================================================
# CONFIGURAÇÃO DO TELEGRAM
# =====================================================================
TOKEN_TELEGRAM = "8811939851:AAFK5KsKWEzfn2vU7WuHtK"
ID_TELEGRAM = "971501251"
# =====================================================================

def enviar_alerta_telegram(mensagem):
    """Função automática que dispara o alerta para o Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
        payload = {"chat_id": ID_TELEGRAM, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
        time.sleep(1.2)
    except Exception as e:
        pass

# Configuração de Tela Cheia e Tema do App
st.set_page_config(page_title="Terminal Quant - Scanner & Checklist", layout="wide")
st.title("🛡️ Terminal Quantitativo & Validador de Opções")
st.caption("Filtros automáticos baseados em IV Rank/Setups, LTA/LTB Automáticas e Ondas de Elliott.")

if "alertas_enviados" not in st.session_state:
    st.session_state.alertas_enviados = {}

def detectar_pivots(df, window=5):
    """Detecta Topos e Fundos relativos no dataframe para traçar Elliott e LTA/LTB"""
    df = df.copy()
    df['Topo'] = False
    df['Fundo'] = False
    
    for i in range(window, len(df) - window):
        sub_high = df['High'].iloc[i-window:i+window+1]
        sub_low = df['Low'].iloc[i-window:i+window+1]
        
        if df['High'].iloc[i] == sub_high.max():
            df.at[df.index[i], 'Topo'] = True
        if df['Low'].iloc[i] == sub_low.min():
            df.at[df.index[i], 'Fundo'] = True
            
    return df

@st.fragment(run_every=300)
def loop_principal():
    carteira = [
        "abev3.sa", "alos3.sa", "alpa4.sa", "arzz3.sa", "asai3.sa", "azul4.sa", "b3sa3.sa", 
        "bbas3.sa", "bbdc3.sa", "bbdc4.sa", "bbse3.sa", "beef3.sa", "bpac11.sa", "brap4.sa", 
        "brfs3.sa", "brkm5.sa", "ccro3.sa", "cmig4.sa", "cmin3.sa", "cogn3.sa", "cpfe3.sa", 
        "cple6.sa", "crfb3.sa", "csan3.sa", "csna3.sa", "cyre3.sa", "dirr3.sa", "dxco3.sa", 
        "elet3.sa", "elet6.sa", "embr3.sa", "enev3.sa", "engi11.sa", "eqtl3.sa", "eztc3.sa", 
        "flry3.sa", "ggbr4.sa", "goau4.sa", "hapv3.sa", "hype3.sa", "igti11.sa", "irbr3.sa", 
        "itsa4.sa", "itub4.sa", "jbss3.sa", "klbn11.sa", "lren3.sa", "lwsa3.sa", "mglu3.sa", 
        "mrfg3.sa", "mrve3.sa", "mult3.sa", "ntco3.sa", "pcar3.sa", "petr3.sa", "petr4.sa", 
        "recv3.sa", "rail3.sa", "radl3.sa", "raiz4.sa", "rent3.sa", "sanb11.sa", "suzb3.sa", 
        "taee11.sa", "tims3.sa", "tots3.sa", "trpl4.sa", "ugpa3.sa", "usim5.sa", "vale3.sa", 
        "vamo3.sa", "vbbr3.sa", "viva3.sa", "wege3.sa", "yduq3.sa"
    ]
    
    resultados = []
    dados_acoes = {}
    st.cache_data.clear()

    progresso = st.progress(0, text="Escaneando mercado para Opções...")
    total_ativos = len(carteira)

    for idx, ticker in enumerate(carteira):
        try:
            progresso.progress((idx + 1) / total_ativos, text=f"Analisando: {ticker.upper()}")
            acao = yf.Ticker(ticker)
            df = acao.history(period="350d")
            if len(df) < 252:
                continue
            dados_acoes[ticker] = df
            
            # MME e MMA
            df['MME_9'] = df['Close'].ewm(span=9, adjust=False).mean()
            df['MMA_21'] = df['Close'].rolling(window=21).mean()
            df['MMA_80'] = df['Close'].rolling(window=80).mean()
            df['MMA_200'] = df['Close'].rolling(window=200).mean()
            ultimo_preço = df['Close'].iloc[-1]
            
            # Volatilidade
            df['Retornos'] = df['Close'].pct_change()
            df['Vol_21d'] = df['Retornos'].rolling(window=21).std() * np.sqrt(252) * 100
            
            historico_vol = df['Vol_21d'].tail(252).dropna()
            if len(historico_vol) < 200:
                continue
                
            iv_atual = historico_vol.iloc[-1]
            iv_minimo = historico_vol.min()
            iv_maximo = historico_vol.max()
            
            iv_rank = ((iv_atual - iv_minimo) / (iv_maximo - iv_minimo)) * 100 if iv_maximo != iv_minimo else 0.0
            iv_percentil = ((historico_vol < iv_atual).sum() / 252) * 100
            
            # Setups
            direcao_mercado = "Neutro"
            sinal_setup = "Aguardando Padrão"
            c, o, h, l = df['Close'].values, df['Open'].values, df['High'].values, df['Low'].values
            mme9, mma21 = df['MME_9'].values, df['MMA_21'].values
            
            if mme9[-1] > mme9[-2] and mme9[-2] <= mme9[-3]:
                sinal_setup = "9.1 COMPRA"
                direcao_mercado = "Alta"
            elif mme9[-1] < mme9[-2] and mme9[-2] >= mme9[-3]:
                sinal_setup = "9.1 VENDA"
                direcao_mercado = "Baixa"
            elif mme9[-1] > mme9[-2] and c[-1] < c[-2] and c[-1] < o[-1]:
                sinal_setup = "9.2/9.3 Armado (Compra)"
                direcao_mercado = "Alta"
            elif mme9[-1] < mme9[-2] and c[-1] > c[-2] and c[-1] > o[-1]:
                sinal_setup = "9.2/9.3 Armado (Venda)"
                direcao_mercado = "Baixa"
                
            if sinal_setup == "Aguardando Padrão":
                if c[-1] > mma21[-1] and l[-1] <= mma21[-1] and mma21[-1] > mma21[-2]:
                    sinal_setup = "PC COMPRA"
                    direcao_mercado = "Alta"
                elif c[-1] < mma21[-1] and h[-1] >= mma21[-1] and mma21[-1] < mma21[-2]:
                    sinal_setup = "PC VENDA"
                    direcao_mercado = "Baixa"

            # Estratégias sugeridas
            estrategia_sugerida = "Aguardar Oportunidade"
            cor_alerta = "⚪"
            if iv_rank >= 70:
                estrategia_sugerida = "💎 Trava de Alta com Put (Crédito)" if direcao_mercado == "Alta" else "💎 Trava de Baixa com Call (Crédito)" if direcao_mercado == "Baixa" else "💎 Venda Volatilidade (Iron Condor)"
                cor_alerta = "🟢" if direcao_mercado == "Alta" else "🔴" if direcao_mercado == "Baixa" else "🔵"
            elif iv_rank <= 25:
                estrategia_sugerida = "⚡ Compra Seca Call / Débito" if direcao_mercado == "Alta" else "⚡ Compra Seca Put / Débito" if direcao_mercado == "Baixa" else "⚡ Compra Volatilidade"
                cor_alerta = "🟢" if direcao_mercado == "Alta" else "🔴" if direcao_mercado == "Baixa" else "🔵"
            else:
                estrategia_sugerida = "📈 Call Spread (Trava de Alta)" if direcao_mercado == "Alta" else "📉 Put Spread (Trava de Baixa)"

            resultados.append({
                "Sinal": cor_alerta, "Acao (Ativo Objeto)": ticker.replace('.sa', '').upper(),
                "Preco Atual": f"R$ {ultimo_preço:.2f}", "IV Rank": iv_rank, "IV Percentil": iv_percentil,
                "Setup Gráfico": sinal_setup, "Estratégia Sugerida": estrategia_sugerida, "ticker_chave": ticker
            })
        except Exception:
            pass

    progresso.empty()

    st.subheader("📋 Matriz de Estratégias para Opções B3")
    df_resultados = pd.DataFrame(resultados)
    if not df_resultados.empty:
        df_resultados = df_resultados.sort_values(by=["IV Rank"], ascending=False)
        df_exibicao = df_resultados.copy()
        df_exibicao["IV Rank"] = df_exibicao["IV Rank"].map("{:.1f}%".format)
        df_exibicao["IV Percentil"] = df_exibicao["IV Percentil"].map("{:.1f}%".format)
        st.dataframe(df_exibicao.drop(columns=["ticker_chave"]), use_container_width=True, hide_index=True)

    st.markdown("---")
    
    if resultados:
        col_grafico, col_checklist = st.columns([1.3, 0.9])
        
        with col_grafico:
            st.subheader("📊 Gráfico Técnico com LTA/LTB & Ondas de Elliott")
            acao_selecionada = st.selectbox("Selecione para Analisar & Validar:", [r["Acao (Ativo Objeto)"] for r in resultados])
            
            dados_linha = df_resultados[df_resultados["Acao (Ativo Objeto)"] == acao_selecionada].iloc[0]
            ticker_chave = dados_linha["ticker_chave"]
            iv_rank_ativo = dados_linha["IV Rank"]

            if ticker_chave in dados_acoes:
                # Pegamos os dados e rodamos o algoritmo de pivots
                df_completo = dados_acoes[ticker_chave]
                df_pivots = detectar_pivots(df_completo, window=4)
                df_grafico = df_pivots.tail(60).copy()
                
                fig = go.Figure(data=[go.Candlestick(
                    x=df_grafico.index, open=df_grafico['Open'], high=df_grafico['High'],
                    low=df_grafico['Low'], close=df_grafico['Close'], name="Preço"
                )])
                
                # Desenhar as Médias Móveis
                fig.add_trace(go.Scatter(x=df_grafico.index, y=df_grafico['MME_9'], mode='lines', name='MME 9', line=dict(color='cyan', width=1.2)))
                fig.add_trace(go.Scatter(x=df_grafico.index, y=df_grafico['MMA_21'], mode='lines', name='MMA 21', line=dict(color='lightgreen', width=1.2)))
                fig.add_trace(go.Scatter(x=df_grafico.index, y=df_grafico['MMA_200'], mode='lines', name='MMA 200', line=dict(color='red', width=2)))

                # --- CÁLCULO DINÂMICO DE LTA / LTB ---
                topos = df_grafico[df_grafico['Topo'] == True]
                fundos = df_grafico[df_grafico['Fundo'] == True]
                
                # Se o preço está acima da MMA 21 = Viés de Alta (Desenhar LTA se houver 2 fundos ascendentes)
                if df_grafico['Close'].iloc[-1] >= df_grafico['MMA_21'].iloc[-1] and len(fundos) >= 2:
                    for i in range(len(fundos) - 1):
                        f1, f2 = fundos.iloc[i], fundos.iloc[i+1]
                        if f2['Low'] > f1['Low']: # Fundos ascendentes confirmados
                            fig.add_trace(go.Scatter(
                                x=[fundos.index[i], fundos.index[i+1], df_grafico.index[-1]],
                                y=[f1['Low'], f2['Low'], f2['Low'] + (f2['Low'] - f1['Low']) * 1.5],
                                mode='lines', name='LTA', line=dict(color='lightgreen', width=2.5, dash='dash')
                            ))
                            break # Desenha a LTA mais expressiva e para
                            
                # Se o preço está abaixo da MMA 21 = Viés de Baixa (Desenhar LTB se houver 2 topos descendentes)
                elif df_grafico['Close'].iloc[-1] < df_grafico['MMA_21'].iloc[-1] and len(topos) >= 2:
                    for i in range(len(topos) - 1):
                        t1, t2 = topos.iloc[i], topos.iloc[i+1]
                        if t2['High'] < t1['High']: # Topos descendentes confirmados
                            fig.add_trace(go.Scatter(
                                x=[topos.index[i], topos.index[i+1], df_grafico.index[-1]],
                                y=[t1['High'], t2['High'], t2['High'] - (t1['High'] - t2['High']) * 1.5],
                                mode='lines', name='LTB', line=dict(color='orange', width=2.5, dash='dash')
                            ))
                            break

                # --- PROJEÇÃO AUTOMÁTICA DAS ONDAS DE ELLIOTT (1,2,3,4,5, A,B,C) ---
                # Mescla e ordena todos os pivots encontrados cronologicamente
                pivots_cronologicos = df_grafico[(df_grafico['Topo'] == True) | (df_grafico['Fundo'] == True)].sort_index()
                
                rotulos_elliott = ['1', '2', '3', '4', '5', 'A', 'B', 'C']
                x_elliott = []
                y_elliott = []
                text_elliott = []
                
                # Associa sequencialmente os rótulos de Elliott aos pivots gerados pelo mercado
                for idx_pivot, (data_hora, linha_pivot) in enumerate(pivots_cronologicos.tail(8).iterrows()):
                    if idx_pivot < len(rotulos_elliott):
                        label = rotulos_elliott[idx_pivot]
                        x_elliott.append(data_hora)
                        # Se for número (onda impulsiva), plota o rótulo no Topo; se for letra (onda corretiva) ou fundo, ajusta posição
                        valor_y = linha_pivot['High'] * 1.015 if label in ['1', '3', '5', 'B'] else linha_pivot['Low'] * 0.985
                        y_elliott.append(valor_y)
                        text_elliott.append(f"<b>({label})</b>")
                
                # Adiciona a linha conectando as Ondas de Elliott
                if x_elliott:
                    fig.add_trace(go.Scatter(
                        x=x_elliott, y=y_elliott, mode='lines+text+markers',
                        text=text_elliott, textposition="top center",
                        name="Ondas Elliott",
                        line=dict(color='yellow', width=2),
                        marker=dict(size=7, color='gold', symbol='diamond'),
                        textfont=dict(color='yellow', size=12)
                    ))

                fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)

        with col_checklist:
            st.subheader(f"📝 Checklist de Operação: {acao_selecionada}")
            st.info("Valide os 10 mandamentos antes de abrir a operação no seu Home Broker:")
            
            tipo_op = st.radio("Tipo da Operação Planejada:", ["Compra (Call/Put Seca ou Débito)", "Venda (Lançamento Coberto ou Crédito)"], horizontal=True)
            
            chk1 = st.checkbox("1. DIREÇÃO: Tendência clara no Diário? (LTA ou LTB confirmada graficamente)")
            chk2 = st.checkbox("2. ELLIOTT: Identificou a onda do ciclo atual no gráfico ao lado?")
            chk3 = st.checkbox("3. SETUP: Padrão gráfico (9.1, 9.2, 9.3 ou PC) confirmado?")
            
            if tipo_op == "Compra (Call/Put Seca ou Débito)":
                if iv_rank_ativo < 30:
                    st.success(f"4. VOLATILIDADE: IV Rank atual ({iv_rank_ativo:.1f}%) está ABAIXO de 30. (Gatilho Perfeito!)")
                    chk4 = True
                else:
                    st.error(f"4. VOLATILIDADE: IV Rank atual ({iv_rank_ativo:.1f}%) está ACIMA de 30!")
                    chk4 = False
            else:
                if iv_rank_ativo > 70:
                    st.success(f"4. VOLATILIDADE: IV Rank atual ({iv_rank_ativo:.1f}%) está ACIMA de 70. (Gatilho Perfeito!)")
                    chk4 = True
                else:
                    st.error(f"4. VOLATILIDADE: IV Rank atual ({iv_rank_ativo:.1f}%) está ABAIXO de 70!")
                    chk4 = False

            chk5 = st.checkbox("5. TEMPO (Vencimento): Se < 25 dias úteis, o timing é excelente?")
            chk6 = st.checkbox("6. DELTA: Alinhado e ajustado para o tipo de operação?")
            chk7 = st.checkbox("7. GAMMA: Favorável ou sob controle matemático?")
            chk8 = st.checkbox("8. VEGA: Alinhado com a projeção de volatilidade implícita?")
            chk9 = st.checkbox("9. STOP: Perda máxima aceitável calculada antes do clique?")
            chk10 = st.checkbox("10. ALVO: Alvos matemáticos e parciais traçados no gráfico?")

            total_checados = sum([chk1, chk2, chk3, chk4, chk5, chk6, chk7, chk8, chk9, chk10])
            
            st.markdown("---")
            if total_checados == 10:
                st.balloons()
                st.success(f"🚀 *OPERAÇÃO 100% VALIDADA (10/10):* Critérios batem perfeitamente!")
            elif total_checados >= 7:
                st.warning(f"⚠️ *OPERAÇÃO DE RISCO MODERADO ({total_checados}/10):* Atenção redobrada.")
            else:
                st.error(f"❌ *TRADE REPROVADO ({total_checados}/10):* Fora dos parâmetros operacionais.")

loop_principal()
st.success("Refinamento gráfico de tendências e Elliott injetado com sucesso!")
