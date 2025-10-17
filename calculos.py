'''# calculos.py
import pandas as pd
import os
from datetime import datetime

def carregar_dados():
    """Carrega CONTASFORMATADAS.csv e indice.csv da raiz do projeto."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    contas_path = os.path.join(script_dir, "CONTASFORMATADAS.csv")
    indices_path = os.path.join(script_dir, "indice.csv")

    # Carregar contas
    contas = pd.read_csv(
        contas_path,
        sep=",",
        quotechar='"',
        decimal=",",
        dtype={"competencia": str, "tipo": str}
    )
    contas = contas.dropna(subset=["competencia", "vencimento", "valor"])
    contas["valor"] = pd.to_numeric(
        contas["valor"].astype(str).str.replace(".", "").str.replace(",", "."),
        errors="coerce"
    )
    contas["vencimento"] = pd.to_datetime(contas["vencimento"], dayfirst=True, errors="coerce")

    # Carregar IGP-M
    igpm = pd.read_csv(indices_path, sep=",", quotechar='"', decimal=",")
    igpm["Data"] = pd.to_datetime(igpm["Data"], format="%m/%Y")
    igpm = igpm.set_index("Data").sort_index()
    igpm["fator"] = 1 + igpm["Indice"] / 100.0

    return contas, igpm

def calcular_igpm_puro(valor_original, data_vencimento, data_fim_str="09/2025"):
    """
    Calcula o valor corrigido apenas pelo IGP-M.
    
    Parâmetros:
        valor_original (float): valor da fatura
        data_vencimento (datetime): data de vencimento da fatura
        data_fim_str (str): data final no formato "MM/AAAA" (ex: "09/2025")
    
    Retorna:
        float: valor corrigido
    """
    if pd.isna(valor_original) or pd.isna(data_vencimento):
        return valor_original

    _, igpm = carregar_dados()  # Só precisamos do igpm

    try:
        mes_fim = pd.Period(data_fim_str, freq="M")
    except:
        raise ValueError("Formato de data final inválido. Use MM/AAAA.")

    mes_inicio = data_vencimento.to_period("M") + 1
    if mes_inicio > mes_fim:
        return valor_original

    dt_inicio = mes_inicio.start_time
    dt_fim = mes_fim.end_time
    fatores = igpm.loc[dt_inicio:dt_fim, "fator"]
    fator_acum = fatores.prod() if not fatores.empty else 1.0

    return round(valor_original * fator_acum, 2)
'''
# calculos.py 
# versão com 3 scripts.
import pandas as pd
import os
from datetime import datetime

def carregar_dados():
    """Carrega CONTASFORMATADAS.csv e indice.csv da raiz do projeto."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    contas_path = os.path.join(script_dir, "CONTASFORMATADAS.csv")
    indices_path = os.path.join(script_dir, "indice.csv")

    # Carregar contas
    contas = pd.read_csv(
        contas_path,
        sep=",",
        quotechar='"',
        decimal=",",
        dtype={"competencia": str, "tipo": str}
    )
    contas = contas.dropna(subset=["competencia", "vencimento", "valor"])
    contas["valor"] = pd.to_numeric(
        contas["valor"].astype(str).str.replace(".", "").str.replace(",", "."),
        errors="coerce"
    )
    contas["vencimento"] = pd.to_datetime(contas["vencimento"], dayfirst=True, errors="coerce")

    # Carregar IGP-M
    igpm = pd.read_csv(indices_path, sep=",", quotechar='"', decimal=",")
    igpm["Data"] = pd.to_datetime(igpm["Data"], format="%m/%Y")
    igpm = igpm.set_index("Data").sort_index()
    igpm["fator"] = 1 + igpm["Indice"] / 100.0

    return contas, igpm

def calcular_igpm_puro(valor_original, data_vencimento, data_fim_str="09/2025"):
    """
    Calcula o valor corrigido apenas pelo IGP-M.
    
    Parâmetros:
        valor_original (float): valor da fatura
        data_vencimento (datetime): data de vencimento da fatura
        data_fim_str (str): data final no formato "MM/AAAA" (ex: "09/2025")
    
    Retorna:
        float: valor corrigido
    """
    if pd.isna(valor_original) or pd.isna(data_vencimento):
        return valor_original

    _, igpm = carregar_dados()  # Só precisamos do igpm

    try:
        mes_fim = pd.Period(data_fim_str, freq="M")
    except:
        raise ValueError("Formato de data final inválido. Use MM/AAAA.")

    mes_inicio = data_vencimento.to_period("M") + 1
    if mes_inicio > mes_fim:
        return valor_original

    dt_inicio = mes_inicio.start_time
    dt_fim = mes_fim.end_time
    fatores = igpm.loc[dt_inicio:dt_fim, "fator"]
    fator_acum = fatores.prod() if not fatores.empty else 1.0

    return round(valor_original * fator_acum, 2)
