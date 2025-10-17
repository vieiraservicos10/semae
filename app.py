# app.py
import streamlit as st
import pandas as pd
from datetime import date
from calculos import calcular_igpm_puro, calcular_conforme_cda, calcular_pratica_real

st.set_page_config(
    page_title="Comparador SEMAE - Valores Justos",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("⚖️ Comparador de Débitos da SEMAE (São Leopoldo/RS)")
st.markdown("""
Ferramenta pública para comparar **três formas de cálculo** de débitos de água/esgoto:
- **Valor justo**: apenas IGP-M (inflação real)
- **Conforme CDA**: multa + juros declarados
- **Prática real da SEMAE**: como aparece no demonstrativo oficial

> Código aberto e auditável: [github.com/vieiraservicos10/semae](https://github.com/vieiraservicos10/semae)  
> Atualizado até **30/09/2025**. Não coleta nem armazena dados.
""")

# Entrada do usuário
col1, col2 = st.columns(2)
with col1:
    valor_original = st.number_input("Valor original da fatura (R$)", min_value=0.0, value=100.0, step=10.0)
with col2:
    data_vencimento = st.date_input("Data de vencimento da fatura", value=date(2020, 6, 10))

data_fim_str = "09/2025"  # fixo conforme seu projeto

if st.button("🔍 Calcular os três cenários"):
    if valor_original <= 0:
        st.error("Por favor, informe um valor maior que zero.")
    else:
        # Executar os três cálculos
        val_justo = calcular_igpm_puro(valor_original, pd.to_datetime(data_vencimento), data_fim_str)
        val_cda = calcular_conforme_cda(valor_original, pd.to_datetime(data_vencimento), data_fim_str)
        val_real = calcular_pratica_real(valor_original, pd.to_datetime(data_vencimento), data_fim_str)

        # Exibir resultados
        st.subheader("📊 Resultados da comparação")
        df_result = pd.DataFrame({
            "Método": [
                "1. Valor justo (IGP-M puro)",
                "2. Conforme texto da CDA",
                "3. Prática real da SEMAE"
            ],
            "Valor corrigido (R$)": [
                f"{val_justo:,.2f}",
                f"{val_cda:,.2f}",
                f"{val_real:,.2f}"
            ],
            "Diferença vs. justo": [
                "—",
                f"+R$ {val_cda - val_justo:,.2f}",
                f"+R$ {val_real - val_justo:,.2f}"
            ]
        })
        st.dataframe(df_result, use_container_width=True, hide_index=True)

        # Explicações
        with st.expander("ℹ️ Como cada cálculo foi feito?"):
            st.markdown("""
            - **Valor justo**: apenas correção pelo IGP-M/FGV, sem multas ou juros.  
              → Base para proposta justa de quitação.
            - **Conforme CDA**: multa de **2%** + juros de **0,0167% ao mês**, ambos sobre o **valor original**.  
              → Conforme texto da Certidão de Dívida Ativa.
            - **Prática real da SEMAE**: multa de **2% sobre o valor corrigido** + juros implícitos de **~0,2345% ao mês**.  
              → Reproduz o demonstrativo oficial (`cda.csv`).
            """)

st.divider()
st.caption("Esta ferramenta é gratuita, sem fins lucrativos e destinada à transparência e resolução extrajudicial de débitos.")
