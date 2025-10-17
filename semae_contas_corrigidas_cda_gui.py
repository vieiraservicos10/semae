'''import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from datetime import datetime

# ----------------------------
# Configuração padrão
# ----------------------------
DATA_CALCULO_PADRAO = "30/09/2025"
TAXA_JUROS_MENSAL = 0.000167  # 0,0167% ao mês
TAXA_MULTA = 0.02  # 2%

# ----------------------------
# Carregar dados
# ----------------------------
def carregar_dados():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    contas_path = os.path.join(script_dir, "CONTASFORMATADAS.csv")
    indices_path = os.path.join(script_dir, "indice.csv")

    contas = pd.read_csv(contas_path, sep=",", quotechar='"', decimal=",")
    contas = contas.dropna(subset=["competencia", "vencimento", "valor"])
    contas["vencimento"] = pd.to_datetime(contas["vencimento"], dayfirst=True, errors="coerce")
    contas["valor"] = pd.to_numeric(contas["valor"], errors="coerce")

    igpm = pd.read_csv(indices_path, sep=",", quotechar='"', decimal=",")
    igpm["Data"] = pd.to_datetime(igpm["Data"], format="%m/%Y")
    igpm = igpm.set_index("Data").sort_index()
    igpm["fator"] = 1 + igpm["Indice"] / 100.0

    return contas, igpm

# ----------------------------
# Funções de cálculo
# ----------------------------
def calcular_meses_atraso(vencimento, data_fim):
    if pd.isna(vencimento):
        return 0
    inicio = vencimento.to_period("M") + 1
    fim = data_fim.to_period("M")
    return max(0, (fim - inicio).n + 1)

def aplicar_correcao_igpm(valor, vencimento, igpm_series, data_fim):
    if pd.isna(vencimento) or pd.isna(valor) or valor == 0:
        return 0.0
    inicio = (vencimento + pd.DateOffset(days=1)).to_period("M")
    fim = data_fim.to_period("M")
    if inicio > fim:
        return 0.0
    dt_inicio = inicio.start_time
    dt_fim = fim.end_time
    fatores = igpm_series.loc[dt_inicio:dt_fim]
    fator_acum = fatores.prod() if not fatores.empty else 1.0
    return valor * (fator_acum - 1)

def processar_contas(contas, igpm, data_fim):
    resultados = []
    igpm_fatores = igpm["fator"]
    for _, row in contas.iterrows():
        venc = row["vencimento"]
        valor_orig = row["valor"]
        if pd.isna(valor_orig) or pd.isna(venc):
            continue

        correcao = aplicar_correcao_igpm(valor_orig, venc, igpm_fatores, data_fim)
        multa = valor_orig * TAXA_MULTA
        n_meses = calcular_meses_atraso(venc, data_fim)
        juros = valor_orig * TAXA_JUROS_MENSAL * n_meses
        total = valor_orig + correcao + multa + juros

        resultados.append({
            "competencia": row["competencia"],
            "vencimento": venc,
            "valor_original": round(valor_orig, 2),
            "correcao_igpm": round(correcao, 2),
            "multa_2pct": round(multa, 2),
            "juros_00167pct": round(juros, 2),
            "total_semae": round(total, 2)
        })
    return pd.DataFrame(resultados)

# ----------------------------
# Interface gráfica
# ----------------------------
class SEMAEApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cálculo SEMAE - Multa + Juros + IGP-M")
        self.root.geometry("1000x600")

        try:
            self.contas, self.igpm = carregar_dados()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar arquivos:\n{e}")
            root.destroy()
            return

        self.df_resultado = None

        # Frame de controle
        frame_ctrl = ttk.Frame(root)
        frame_ctrl.pack(pady=10, padx=10, fill="x")

        ttk.Label(frame_ctrl, text="Data de cálculo (DD/MM/AAAA):").pack(side="left")
        self.entry_data = ttk.Entry(frame_ctrl, width=12)
        self.entry_data.insert(0, DATA_CALCULO_PADRAO)
        self.entry_data.pack(side="left", padx=5)

        ttk.Button(frame_ctrl, text="Calcular", command=self.calcular).pack(side="left", padx=5)
        ttk.Button(frame_ctrl, text="Exportar CSV", command=self.exportar).pack(side="left", padx=5)

        # Tabela
        frame_table = ttk.Frame(root)
        frame_table.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("competencia", "vencimento", "valor_original", "correcao_igpm", "multa_2pct", "juros_00167pct", "total_semae")
        self.tree = ttk.Treeview(frame_table, columns=cols, show="headings")
        headings = ["Competência", "Vencimento", "Valor Original", "Correção IGP-M", "Multa (2%)", "Juros (0,0167%/mês)", "Total SEMAE"]
        for col, txt in zip(cols, headings):
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=120, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.carregar_tabela()

    def carregar_tabela(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        # Mostra apenas as contas originais até calcular
        for _, row in self.contas.iterrows():
            venc = row["vencimento"].strftime("%d/%m/%Y") if pd.notna(row["vencimento"]) else ""
            self.tree.insert("", "end", values=(row["competencia"], venc, f"R$ {row['valor']:.2f}", "", "", "", ""))

    def calcular(self):
        data_str = self.entry_data.get().strip()
        try:
            data_fim = pd.to_datetime(data_str, format="%d/%m/%Y")
        except:
            messagebox.showerror("Erro", "Formato de data inválido. Use DD/MM/AAAA.")
            return

        try:
            self.df_resultado = processar_contas(self.contas, self.igpm, data_fim)
            self.atualizar_tabela()
            messagebox.showinfo("Sucesso", f"Cálculo concluído até {data_str}.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha no cálculo:\n{e}")

    def atualizar_tabela(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for _, row in self.df_resultado.iterrows():
            self.tree.insert("", "end", values=(
                row["competencia"],
                row["vencimento"].strftime("%d/%m/%Y"),
                f"R$ {row['valor_original']:.2f}",
                f"R$ {row['correcao_igpm']:.2f}",
                f"R$ {row['multa_2pct']:.2f}",
                f"R$ {row['juros_00167pct']:.2f}",
                f"R$ {row['total_semae']:.2f}"
            ))

    def exportar(self):
        if self.df_resultado is None:
            messagebox.showwarning("Atenção", "Calcule primeiro!")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Salvar cálculo SEMAE"
        )
        if not path:
            return

        # Formatar para padrão BR
        df_exp = self.df_resultado.copy()
        for col in ["valor_original", "correcao_igpm", "multa_2pct", "juros_00167pct", "total_semae"]:
            df_exp[col] = df_exp[col].map(lambda x: f"{x:.2f}".replace(".", ","))
        df_exp["vencimento"] = df_exp["vencimento"].dt.strftime("%d/%m/%Y")

        df_exp.to_csv(path, index=False, sep=";", decimal=",")
        messagebox.showinfo("Sucesso", f"Arquivo salvo:\n{path}")

# ----------------------------
# Executar
# ----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = SEMAEApp(root)
    root.mainloop()
'''
'''
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os

# ----------------------------
# Configurações
# ----------------------------
DATA_CALCULO_PADRAO = "30/09/2025"
TAXA_JUROS_MENSAL = 0.000167  # 0,0167% ao mês
TAXA_MULTA = 0.02             # 2%

# ----------------------------
# Carregar e limpar dados
# ----------------------------
def carregar_dados():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    contas_path = os.path.join(script_dir, "CONTASFORMATADAS.csv")
    indices_path = os.path.join(script_dir, "indice.csv")

    # Ler contas
    contas = pd.read_csv(contas_path, sep=",", quotechar='"', decimal=",")
    # Remover linhas sem competência, vencimento ou valor
    contas = contas.dropna(subset=["competencia", "vencimento", "valor"])
    # Converter valor: "55,86" → 55.86
    contas["valor"] = (
        contas["valor"]
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )
    # Converter vencimento
    contas["vencimento"] = pd.to_datetime(contas["vencimento"], dayfirst=True, errors="coerce")
    contas = contas.dropna(subset=["vencimento", "valor"])

    # Ler índices
    igpm = pd.read_csv(indices_path, sep=",", quotechar='"', decimal=",")
    igpm["Data"] = pd.to_datetime(igpm["Data"], format="%m/%Y")
    igpm = igpm.set_index("Data").sort_index()
    igpm["fator"] = 1 + igpm["Indice"] / 100.0

    return contas, igpm

# ----------------------------
# Funções de cálculo
# ----------------------------
def calcular_meses_atraso(vencimento, data_fim):
    inicio = vencimento.to_period("M") + 1
    fim = data_fim.to_period("M")
    return max(0, (fim - inicio).n + 1)

def aplicar_correcao_igpm(valor, vencimento, igpm_series, data_fim):
    inicio = (vencimento + pd.DateOffset(days=1)).to_period("M")
    fim = data_fim.to_period("M")
    if inicio > fim:
        return 0.0
    dt_inicio = inicio.start_time
    dt_fim = fim.end_time
    fatores = igpm_series.loc[dt_inicio:dt_fim]
    fator_acum = fatores.prod() if not fatores.empty else 1.0
    return valor * (fator_acum - 1)

def processar_contas(contas, igpm, data_fim):
    resultados = []
    igpm_fatores = igpm["fator"]
    for _, row in contas.iterrows():
        venc = row["vencimento"]
        valor_orig = row["valor"]

        correcao = aplicar_correcao_igpm(valor_orig, venc, igpm_fatores, data_fim)
        multa = valor_orig * TAXA_MULTA
        n_meses = calcular_meses_atraso(venc, data_fim)
        juros = valor_orig * TAXA_JUROS_MENSAL * n_meses
        total = valor_orig + correcao + multa + juros

        resultados.append({
            "competencia": row["competencia"],
            "vencimento": venc,
            "valor_original": round(valor_orig, 2),
            "correcao_igpm": round(correcao, 2),
            "multa_2pct": round(multa, 2),
            "juros_00167pct": round(juros, 2),
            "total_semae": round(total, 2)
        })
    return pd.DataFrame(resultados)

# ----------------------------
# Interface gráfica
# ----------------------------
class SEMAEApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cálculo SEMAE - Multa + Juros + IGP-M")
        self.root.geometry("1020x600")

        try:
            self.contas, self.igpm = carregar_dados()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar arquivos:\n{e}")
            root.destroy()
            return

        self.df_resultado = None

        # Controles
        frame_ctrl = ttk.Frame(root)
        frame_ctrl.pack(pady=10, padx=10, fill="x")
        ttk.Label(frame_ctrl, text="Data de cálculo (DD/MM/AAAA):").pack(side="left")
        self.entry_data = ttk.Entry(frame_ctrl, width=12)
        self.entry_data.insert(0, DATA_CALCULO_PADRAO)
        self.entry_data.pack(side="left", padx=5)
        ttk.Button(frame_ctrl, text="Calcular", command=self.calcular).pack(side="left", padx=5)
        ttk.Button(frame_ctrl, text="Exportar CSV", command=self.exportar).pack(side="left", padx=5)

        # Tabela
        frame_table = ttk.Frame(root)
        frame_table.pack(fill="both", expand=True, padx=10, pady=10)
        cols = ("competencia", "vencimento", "valor_original", "correcao_igpm", "multa_2pct", "juros_00167pct", "total_semae")
        self.tree = ttk.Treeview(frame_table, columns=cols, show="headings")
        headings = ["Competência", "Vencimento", "Valor Original", "Correção IGP-M", "Multa (2%)", "Juros (0,0167%/mês)", "Total SEMAE"]
        for col, txt in zip(cols, headings):
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=120, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.carregar_tabela()

    def carregar_tabela(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for _, row in self.contas.iterrows():
            venc = row["vencimento"].strftime("%d/%m/%Y")
            self.tree.insert("", "end", values=(row["competencia"], venc, f"R$ {row['valor']:.2f}", "", "", "", ""))

    def calcular(self):
        data_str = self.entry_data.get().strip()
        try:
            data_fim = pd.to_datetime(data_str, format="%d/%m/%Y")
        except:
            messagebox.showerror("Erro", "Formato de data inválido. Use DD/MM/AAAA.")
            return

        try:
            self.df_resultado = processar_contas(self.contas, self.igpm, data_fim)
            self.atualizar_tabela()
            messagebox.showinfo("Sucesso", f"Cálculo concluído até {data_str}.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha no cálculo:\n{e}")

    def atualizar_tabela(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for _, row in self.df_resultado.iterrows():
            self.tree.insert("", "end", values=(
                row["competencia"],
                row["vencimento"].strftime("%d/%m/%Y"),
                f"R$ {row['valor_original']:.2f}",
                f"R$ {row['correcao_igpm']:.2f}",
                f"R$ {row['multa_2pct']:.2f}",
                f"R$ {row['juros_00167pct']:.2f}",
                f"R$ {row['total_semae']:.2f}"
            ))

    def exportar(self):
        if self.df_resultado is None:
            messagebox.showwarning("Atenção", "Calcule primeiro!")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Salvar cálculo SEMAE"
        )
        if not path:
            return

        df_exp = self.df_resultado.copy()
        for col in ["valor_original", "correcao_igpm", "multa_2pct", "juros_00167pct", "total_semae"]:
            df_exp[col] = df_exp[col].map(lambda x: f"{x:.2f}".replace(".", ","))
        df_exp["vencimento"] = df_exp["vencimento"].dt.strftime("%d/%m/%Y")
        df_exp.to_csv(path, index=False, sep=";", decimal=",")
        messagebox.showinfo("Sucesso", f"Arquivo salvo:\n{path}")

# ----------------------------
# Executar
# ----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = SEMAEApp(root)
    root.mainloop()
'''
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import os

# ----------------------------
# Configurações (conforme texto da CDA)
# ----------------------------
DATA_FIM = pd.to_datetime("2025-09-30")  # Até setembro/2025
TAXA_JUROS_DECLARADA = 0.000167  # 0,0167% ao mês (conforme CDA)
TAXA_MULTA = 0.02                # 2%

METODOLOGIA = """
Cálculo conforme o texto literal da CDA 0000510/2023 da SEMAE,  
com valores atualizados até 30/09/2025.

Fontes dos dados:
- CONTASFORMATADAS.csv: extraído do site https://agenciaweb.semae.rs.gov.br/Home/InfoSegundaViaFaturas em 16/10/2025
- indice.csv: extraído do site https://extra-ibre.fgv.br/IBRE/sitefgvdados/visualizaconsulta.aspx em 16/10/2025

Metodologia (conforme descrito na CDA):
1. VALOR ORIGINAL = coluna 'valor' do CONTASFORMATADAS.csv
2. CORREÇÃO MONETÁRIA:
   - Índice: IGP-M (arquivo indice.csv)
   - Período: do mês seguinte ao vencimento até SETEMBRO/2025
   - Aplicada sobre o VALOR ORIGINAL
3. MULTA: 2% do VALOR ORIGINAL (única, não cumulativa)
4. JUROS: 0,0167% ao mês (simples) sobre o VALOR ORIGINAL
   - Período: do mês seguinte ao vencimento até SETEMBRO/2025

Este cálculo segue rigorosamente o que está declarado na CDA,  
ainda que difira da prática efetivamente aplicada.
"""

# ----------------------------
# Carregar dados
# ----------------------------
def carregar_dados():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    contas_path = os.path.join(script_dir, "CONTASFORMATADAS.csv")
    indices_path = os.path.join(script_dir, "indice.csv")

    contas = pd.read_csv(contas_path, sep=",", quotechar='"', decimal=",")
    contas = contas.dropna(subset=["competencia", "vencimento", "valor"])
    contas = contas[contas["competencia"].str.match(r"\d{2}/\d{4}", na=False)]
    contas["valor"] = (
        contas["valor"]
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )
    contas["vencimento"] = pd.to_datetime(contas["vencimento"], dayfirst=True, errors="coerce")
    contas = contas.dropna(subset=["vencimento", "valor"])

    igpm = pd.read_csv(indices_path, sep=",", quotechar='"', decimal=",")
    igpm["Data"] = pd.to_datetime(igpm["Data"], format="%m/%Y")
    igpm = igpm.set_index("Data").sort_index()
    igpm["fator"] = 1 + igpm["Indice"] / 100.0

    return contas, igpm

# ----------------------------
# Funções de cálculo
# ----------------------------
def calcular_meses(vencimento):
    inicio = vencimento.to_period("M") + 1
    fim = DATA_FIM.to_period("M")
    return max(0, (fim - inicio).n + 1)

def aplicar_correcao_igpm(valor, vencimento, igpm_series):
    inicio = (vencimento + pd.DateOffset(days=1)).to_period("M")
    fim = DATA_FIM.to_period("M")
    if inicio > fim:
        return 0.0
    dt_inicio = inicio.start_time
    dt_fim = fim.end_time
    fatores = igpm_series.loc[dt_inicio:dt_fim]
    fator_acum = fatores.prod() if not fatores.empty else 1.0
    return valor * (fator_acum - 1)

def processar_contas(contas, igpm):
    resultados = []
    igpm_fatores = igpm["fator"]
    for _, row in contas.iterrows():
        venc = row["vencimento"]
        valor_orig = row["valor"]

        correcao = aplicar_correcao_igpm(valor_orig, venc, igpm_fatores)
        multa = valor_orig * TAXA_MULTA
        n_meses = calcular_meses(venc)
        juros = valor_orig * TAXA_JUROS_DECLARADA * n_meses
        total = valor_orig + correcao + multa + juros

        resultados.append({
            "competencia": row["competencia"],
            "vencimento": venc,
            "valor_original": round(valor_orig, 2),
            "correcao_igpm": round(correcao, 2),
            "multa_2pct": round(multa, 2),
            "juros_00167pct": round(juros, 2),
            "total_cda_texto": round(total, 2)
        })
    return pd.DataFrame(resultados)

# ----------------------------
# Interface gráfica
# ----------------------------
class SEMAECDATextoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cálculo conforme texto da CDA (até 30/09/2025)")
        self.root.geometry("1050x620")

        try:
            self.contas, self.igpm = carregar_dados()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar arquivos:\n{e}")
            root.destroy()
            return

        self.df_resultado = None

        frame_ctrl = ttk.Frame(root)
        frame_ctrl.pack(pady=10, padx=10, fill="x")
        ttk.Button(frame_ctrl, text="Calcular", command=self.calcular).pack(side="left", padx=5)
        ttk.Button(frame_ctrl, text="Exportar CSV", command=self.exportar).pack(side="left", padx=5)
        ttk.Button(frame_ctrl, text="Como foi calculado?", command=self.mostrar_metodologia).pack(side="left", padx=5)

        frame_table = ttk.Frame(root)
        frame_table.pack(fill="both", expand=True, padx=10, pady=10)
        cols = ("competencia", "vencimento", "valor_original", "correcao_igpm", "multa_2pct", "juros_00167pct", "total_cda_texto")
        self.tree = ttk.Treeview(frame_table, columns=cols, show="headings")
        headings = ["Competência", "Vencimento", "Valor Original", "Correção IGP-M", "Multa (2%)", "Juros (0,0167%/mês)", "Total (CDA-texto)"]
        for col, txt in zip(cols, headings):
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=120, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.carregar_tabela()

    def carregar_tabela(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for _, row in self.contas.iterrows():
            venc = row["vencimento"].strftime("%d/%m/%Y")
            self.tree.insert("", "end", values=(row["competencia"], venc, f"R$ {row['valor']:.2f}", "", "", "", ""))

    def calcular(self):
        try:
            self.df_resultado = processar_contas(self.contas, self.igpm)
            self.atualizar_tabela()
            messagebox.showinfo("Sucesso", "Cálculo conforme texto da CDA concluído até 30/09/2025.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha no cálculo:\n{e}")

    def atualizar_tabela(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for _, row in self.df_resultado.iterrows():
            self.tree.insert("", "end", values=(
                row["competencia"],
                row["vencimento"].strftime("%d/%m/%Y"),
                f"R$ {row['valor_original']:.2f}",
                f"R$ {row['correcao_igpm']:.2f}",
                f"R$ {row['multa_2pct']:.2f}",
                f"R$ {row['juros_00167pct']:.2f}",
                f"R$ {row['total_cda_texto']:.2f}"
            ))

    def exportar(self):
        if self.df_resultado is None:
            messagebox.showwarning("Atenção", "Calcule primeiro!")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Salvar cálculo conforme texto da CDA"
        )
        if not path:
            return

        df_exp = self.df_resultado.copy()
        for col in ["valor_original", "correcao_igpm", "multa_2pct", "juros_00167pct", "total_cda_texto"]:
            df_exp[col] = df_exp[col].map(lambda x: f"{x:.2f}".replace(".", ","))
        df_exp["vencimento"] = df_exp["vencimento"].dt.strftime("%d/%m/%Y")
        df_exp.to_csv(path, index=False, sep=";", decimal=",")
        messagebox.showinfo("Sucesso", f"Arquivo salvo:\n{path}")

    def mostrar_metodologia(self):
        top = tk.Toplevel(self.root)
        top.title("Metodologia de Cálculo")
        top.geometry("720x420")
        text_area = scrolledtext.ScrolledText(top, wrap=tk.WORD, font=("Arial", 10))
        text_area.insert(tk.END, METODOLOGIA)
        text_area.configure(state="disabled")
        text_area.pack(padx=10, pady=10, fill="both", expand=True)

# ----------------------------
# Executar
# ----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = SEMAECDATextoApp(root)
    root.mainloop()
