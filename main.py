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
TOKEN_TELEGRAM = "8811939851:AAFK5KsKWEzfn2vU7WuHtK"  # Atualizado conforme seu print
ID_TELEGRAM = "971501251"                             # Atualizado conforme seu print
# =====================================================================

def enviar_alerta_telegram(mensagem):
    """Função automática que dispara o alerta para o Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
        payload = {"chat_id": ID_TELEGRAM, "text": mensagem, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
        time.sleep(1.2)
    except Exception as e:
        pass

# Configuração de Tela Cheia e Tema do App
st.set_page_config(page_title="Terminal Quant - Scanner & Checklist", layout="wide")
st.title("🛡️ Terminal Quantitativo & Validador de Opções")
st.caption("Filtros automáticos baseados em IV Rank/Setups e Checklist de Gestão de Risco Profissional.")

# Mecanismo de estado para controle de alertas
if "alertas_enviados" not in st.session_state:
    st.session_state.alertas_enviados = {}

@st.fragment(run_every=300)
def loop_principal():
    # Tickers limpos e corrigidos com ".sa" minúsculo para evitar erros no Yahoo Finance
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
            
            # --- DIMENSÕES DE PREÇO ---
            df['MME_9'] = df['Close'].ewm(span=9, adjust=False).mean()
            df['MMA_21'] = df['Close'].rolling(window=21).mean()
            df['MMA_80'] = df['Close'].rolling(window=80).mean()
            df['MMA_200'] = df['Close'].rolling(window=200).mean()
            ultimo_preço = df['Close'].iloc[-1]
            
            # --- CÁLCULO DA VOLATILIDADE HISTÓRICA ---
            df['Retornos'] = df['Close'].pct_change()
            df['Vol_21d'] = df['Retornos'].rolling(window=21).std() * np.sqrt(252) * 100
            
            historico_vol = df['Vol_21d'].tail(252).dropna()
            if len(historico_vol) < 200:
                continue
                
            iv_atual = historico_vol.iloc[-1]
            iv_minimo = historico_vol.min()
            iv_maximo = historico_vol.max()
            
            if iv_maximo != iv_minimo:
                iv_rank = ((iv_atual - iv_minimo) / (iv_maximo - iv_minimo)) * 100
            else:
                iv_rank = 0.0
                
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

            # --- ESTRATÉGIAS ---
            estrategia_sugerida = "Aguardar Oportunidade"
            cor_alerta = "⚪"

            if iv_rank >= 70:
                if direcao_mercado == "Alta":
                    estrategia_sugerida = "💎 Trava de Alta com Put (Crédito) / Lançamento Coberto"
                    cor_alerta = "🟢"
                elif direcao_mercado == "Baixa":
                    estrategia_sugerida = "💎 Trava de Baixa com Call (Crédito)"
                    cor_alerta = "🔴"
                else:
                    estrategia_sugerida = "💎 Venda Volatilidade (Iron Condor / Straddle Vendido)"
                    cor_alerta = "🔵"
            elif iv_rank <= 25:
                if direcao_mercado == "Alta":
                    estrategia_sugerida = "⚡ Compra Seca Call / Trava Alta Call (Débito)"
                    cor_alerta = "🟢"
                elif direcao_mercado == "Baixa":
                    estrategia_sugerida = "⚡ Compra Seca Put / Trava Baixa Put (Débito)"
                    cor_alerta = "🔴"
                else:
                    estrategia_sugerida = "⚡ Compra Volatilidade (Straddle / Strangle Comprado)"
                    cor_alerta = "🔵"
            else:
                if direcao_mercado == "Alta":
                    estrategia_sugerida = "📈 Call Spread (Trava de Alta) / Compra Call"
                    cor_alerta = "🟢"
                elif direcao_mercado == "Baixa":
                    estrategia_sugerida = "📉 Put Spread (Trava de Baixa) / Compra Put"
                    cor_alerta = "🔴"

            ticker_nome = ticker.replace('.sa', '').upper()

            resultados.append({
                "Sinal": cor_alerta,
                "Acao (Ativo Objeto)": ticker_nome,
                "Preco Atual": f"R$ {ultimo_preço:.2f}",
                "IV Rank": iv_rank,
                "IV Percentil": iv_percentil,
                "Setup Gráfico": sinal_setup,
                "Estratégia Sugerida": estrategia_sugerida,
                "ticker_chave": ticker
            })
        except Exception as e:
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
    
    # --- ÁREA DO CHECKLIST OPERACIONAL ---
    if resultados:
        col_grafico, col_checklist = st.columns([1.2, 1.0])
        
        with col_grafico:
            st.subheader("📊 Gráfico Técnico de Apoio")
            acao_selecionada = st.selectbox("Selecione para Analisar & Validar:", [r["Acao (Ativo Objeto)"] for r in resultados])
            
            # Encontra a linha de dados correspondente
            dados_linha = df_resultados[df_resultados["Acao (Ativo Objeto)"] == acao_selecionada].iloc[0]
            ticker_chave = dados_linha["ticker_chave"]
            iv_rank_ativo = dados_linha["IV Rank"]

            if ticker_chave in dados_acoes:
                df_grafico = dados_acoes[ticker_chave].tail(60)
                fig = go.Figure(data=[go.Candlestick(
                    x=df_grafico.index, open=df_grafico['Open'], high=df_grafico['High'],
                    low=df_grafico['Low'], close=df_grafico['Close'], name="Preço"
                )])
                fig.add_trace(go.Scatter(x=df_grafico.index, y=df_grafico['MME_9'], mode='lines', name='MME 9', line=dict(color='cyan', width=1.5)))
                fig.add_trace(go.Scatter(x=df_grafico.index, y=df_grafico['MMA_21'], mode='lines', name='MMA 21', line=dict(color='lightgreen', width=1.5)))
                fig.add_trace(go.Scatter(x=df_grafico.index, y=df_grafico['MMA_80'], mode='lines', name='MMA 80', line=dict(color='orange', width=2)))
                fig.add_trace(go.Scatter(x=df_grafico.index, y=df_grafico['MMA_200'], mode='lines', name='MMA 200', line=dict(color='red', width=2.5)))
                fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)

        with col_checklist:
            st.subheader(f"📝 Checklist de Operação: {acao_selecionada}")
            st.info("Valide os 10 mandamentos antes de abrir a operação no seu Home Broker:")
            
            tipo_op = st.radio("Tipo da Operação Planejada:", ["Compra (Call/Put Seca ou Débito)", "Venda (Lançamento Coberto ou Crédito)"], horizontal=True)
            
            chk1 = st.checkbox("1. DIREÇÃO: Tendência clara no Diário? (LTA ou LTB confirmada)")
            chk2 = st.checkbox("2. ELLIOTT: Qual onda estamos? (Marque apenas se NÃO for onda 4, 5 ou B)")
            chk3 = st.checkbox("3. SETUP: Padrão gráfico (9.1, 9.2, 9.3 ou PC) confirmado?")
            
            # 4. VALIDAÇÃO DE VOLATILIDADE AUTOMÁTICA
            if tipo_op == "Compra (Call/Put Seca ou Débito)":
                if iv_rank_ativo < 30:
                    st.success(f"4. VOLATILIDADE: IV Rank atual ({iv_rank_ativo:.1f}%) está ABAIXO de 30. (Gatilho Perfeito!)")
                    chk4 = True
                else:
                    st.error(f"4. VOLATILIDADE: IV Rank atual ({iv_rank_ativo:.1f}%) está ACIMA de 30! Alto risco de compressão de volatilidade.")
                    chk4 = False
            else:
                if iv_rank_ativo > 70:
                    st.success(f"4. VOLATILIDADE: IV Rank atual ({iv_rank_ativo:.1f}%) está ACIMA de 70. (Gatilho Perfeito!)")
                    chk4 = True
                else:
                    st.error(f"4. VOLATILIDADE: IV Rank atual ({iv_rank_ativo:.1f}%) está ABAIXO de 70! Prêmios baixos para coletar crédito.")
                    chk4 = False

            chk5 = st.checkbox("5. TEMPO (Vencimento): Se < 25 dias úteis para o vencimento, o seu setup gráfico é EXCELENTE?")
            
            if tipo_op == "Compra (Call/Put Seca ou Débito)":
                chk6 = st.checkbox("6. DELTA: Entre 0.50 e 0.70 (Opção ATM ou ligeiramente ITM)?")
                chk7 = st.checkbox("7. GAMMA: Positivo verificado? (Vai acelerar o seu prêmio a favor do movimento)")
                chk8 = st.checkbox("8. VEGA: Positivo? (IV baixa inicial expandindo vai valorizar a sua opção)")
            else:
                chk6 = st.checkbox("6. DELTA: Entre 0.15 e 0.30 (Opção bem OTM)?")
                chk7 = st.checkbox("7. GAMMA: Negativo controlado? (Fique atento para rolar ou sair se o delta subir rápido)")
                chk8 = st.checkbox("8. VEGA: Negativo? (IV alta derretendo vai acelerar o seu lucro)")
                
            chk9 = st.checkbox("9. STOP: Valor máximo de perda aceitável definido em carteira antes de clicar?")
            chk10 = st.checkbox("10. ALVO: Parciais e alvo final traçados matematicamente no gráfico?")

            total_checados = sum([chk1, chk2, chk3, chk4, chk5, chk6, chk7, chk8, chk9, chk10])
            
            st.markdown("---")
            if total_checados == 10:
                st.balloons()
                st.success(f"🚀 *OPERAÇÃO 100% VALIDADA (10/10):* Todos os critérios técnicos batem perfeitamente. Siga seu plano!")
            elif total_checados >= 7:
                st.warning(f"⚠️ *OPERAÇÃO DE RISCO MODERADO ({total_checados}/10):* Atenção dobrada nos itens não marcados.")
            else:
                st.error(f"❌ *TRADE REPROVADO ({total_checados}/10):* Fora dos parâmetros operacionais. Proteja seu capital!")

loop_principal()
st.success("Scanner & Checklist Operacional sincronizados com sucesso!")
