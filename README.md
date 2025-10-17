# 🧮 Corretor de Contas SEMAE – Comparação Técnica de Cálculos

Este projeto oferece uma **ferramenta pública, gratuita e auditável** para análise e comparação de débitos relativos ao consumo de água e esgotamento sanitário junto ao **Serviço Municipal de Água e Esgoto (SEMAE) de Rio do Sul/SC**.

Desenvolvido com rigor técnico e baseado em dados oficiais, o sistema permite comparar **três abordagens distintas** de atualização de valores, todas aplicadas aos mesmos débitos e atualizadas até **30/09/2025**:

---

## 🔍 Os três métodos de cálculo

| Método | Descrição |
|-------|----------|
| **1. Valor justo (IGP-M puro)** | Apenas correção monetária pelo **IGP-M/FGV**, sem multas ou juros. Representa o valor atualizado **apenas pela inflação**. |
| **2. Conforme texto da CDA inclusa em processo judicial(não informarei o número) para não expor dados privados | Aplica exatamente o que está declarado na Certidão de Dívida Ativa: **multa de 2%** e **juros de 0,0167% ao mês**, ambos sobre o **valor original**. |
| **3. Conforme prática real da SEMAE** | Reproduz os valores **efetivamente cobrados**, com base no demonstrativo oficial (`cda.csv`): **multa de 2% sobre o valor corrigido** + **juros implícitos (~0,2345% ao mês)**. |

> ✅ Todos os cálculos respeitam o período de divulgação dos índices oficiais e são feitos do **mês seguinte ao vencimento até setembro/2025**.

---

## 📁 Fontes dos dados

- **Contas de água**: extraídas do site oficial da SEMAE  
  → [https://agenciaweb.semae.rs.gov.br/Home/InfoSegundaViaFaturas](https://agenciaweb.semae.rs.gov.br/Home/InfoSegundaViaFaturas)  
  → Arquivo: `CONTASFORMATADAS.csv` (extraído em **16/10/2025**)

- **Índices IGP-M**: série histórica da **FGV/IBRE**  
  → [https://extra-ibre.fgv.br/IBRE/sitefgvdados/visualizaconsulta.aspx](https://extra-ibre.fgv.br/IBRE/sitefgvdados/visualizaconsulta.aspx)  
  → Arquivo: `indice.csv` (extraído em **16/10/2025**)

- **Demonstrativo oficial da SEMAE**:  
  → Arquivo: `cda.csv` (CDA 0000xxx/2023)

---

## 🛠️ Funcionalidades

Cada script inclui:
- Interface gráfica intuitiva (Tkinter)
- **Demonstrativo analítico mês a mês** (com opção de exportar PDF) somente em corretor_igpm_gui.py
- **Botão "Como foi calculado?"** com explicação detalhada da metodologia
- Exportação para **CSV no formato brasileiro** (vírgula decimal, ponto milhar) podendo imprimir o arquivo, salvo no formato.csv

### Scripts disponíveis:
- `corretor_igpm_gui.py` → valor justo (IGP-M puro)
- `semae_contas_corrigidas_cda_gui.py` → conforme texto da CDA
- `semae_real_correcao_gui.py` → conforme prática real da SEMAE

---

## ▶️ Como executar

requer python3 instalado
1. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
