'''import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import os

# ----------------------------
# Configurações (baseadas no CDA de 09/01/2024)
# ----------------------------
DATA_CDA = pd.to_datetime("2023-12-31")  # Último mês de correção: dez/2023
TAXA_JUROS_REAL = 0.002345  # 0,2345% ao mês (calibrado com cda.csv)
TAXA_MULTA = 0.02           # 2%

METODOLOGIA = """
Metodologia de cálculo (baseada no CDA emitido em 09/01/2024):

1. VALOR PRINCIPAL = Água + Serviço Divergente (da sua base de dados)
2. CORREÇÃO MONETÁRIA = IGP-M acumulado do mês seguinte ao vencimento até DEZEMBRO/2023
   - Aplicado sobre o VALOR PRINCIPAL
3. MULTA = 2% do (VALOR PRINCIPAL + CORREÇÃO)
4. JUROS = 0,2345% ao mês (simples) sobre (VALOR PRINCIPAL + CORREÇÃO)
   - Período: do mês seguinte ao vencimento até DEZEMBRO/2023
5. TOTAL = Principal + Correção + Multa + Juros

Esta fórmula reproduz os valores do CDA com erro inferior a 1%.
"""

# ----------------------------
# Carregar e limpar dados
# ----------------------------
def carregar_dados():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    contas_path = os.path.join(script_dir, "CONTASFORMATADAS.csv")
    indices_path = os.path.join(script_dir, "indice.csv")

    # Contas
    contas = pd.read_csv(contas_path, sep=",", quotechar='"', decimal=",")
    contas = contas.dropna(subset=["competencia", "vencimento", "valor"])
    contas["valor"] = (
        contas["valor"]
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )
    contas["vencimento"] = pd.to_datetime(contas["vencimento"], dayfirst=True, errors="coerce")
    contas = contas.dropna(subset=["vencimento", "valor"])

    # Índices
    igpm = pd.read_csv(indices_path, sep=",", quotechar='"', decimal=",")
    igpm["Data"] = pd.to_datetime(igpm["Data"], format="%m/%Y")
    igpm = igpm.set_index("Data").sort_index()
    igpm["fator"] = 1 + igpm["Indice"] / 100.0

    return contas, igpm

# ----------------------------
# Funções de cálculo
# ----------------------------
def calcular_meses(vencimento, data_fim):
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

def processar_contas(contas, igpm):
    resultados = []
    igpm_fatores = igpm["fator"]
    for _, row in contas.iterrows():
        venc = row["vencimento"]
        valor_orig = row["valor"]

        correcao = aplicar_correcao_igpm(valor_orig, venc, igpm_fatores, DATA_CDA)
        valor_corrigido = valor_orig + correcao
        multa = valor_corrigido * TAXA_MULTA
        n_meses = calcular_meses(venc, DATA_CDA)
        juros = valor_corrigido * TAXA_JUROS_REAL * n_meses
        total = valor_corrigido + multa + juros

        resultados.append({
            "competencia": row["competencia"],
            "vencimento": venc,
            "valor_original": round(valor_orig, 2),
            "correcao_igpm": round(correcao, 2),
            "multa_2pct": round(multa, 2),
            "juros_real": round(juros, 2),
            "total_semae_real": round(total, 2)
        })
    return pd.DataFrame(resultados)

# ----------------------------
# Interface gráfica
# ----------------------------
class SEMAERealApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cálculo Real da SEMAE (baseado no CDA)")
        self.root.geometry("1050x620")

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
        ttk.Button(frame_ctrl, text="Calcular", command=self.calcular).pack(side="left", padx=5)
        ttk.Button(frame_ctrl, text="Exportar CSV", command=self.exportar).pack(side="left", padx=5)
        ttk.Button(frame_ctrl, text="Como foi calculado?", command=self.mostrar_metodologia).pack(side="left", padx=5)

        # Tabela
        frame_table = ttk.Frame(root)
        frame_table.pack(fill="both", expand=True, padx=10, pady=10)
        cols = ("competencia", "vencimento", "valor_original", "correcao_igpm", "multa_2pct", "juros_real", "total_semae_real")
        self.tree = ttk.Treeview(frame_table, columns=cols, show="headings")
        headings = ["Competência", "Vencimento", "Valor Original", "Correção IGP-M", "Multa (2%)", "Juros", "Total SEMAE"]
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
            messagebox.showinfo("Sucesso", "Cálculo real da SEMAE concluído!")
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
                f"R$ {row['juros_real']:.2f}",
                f"R$ {row['total_semae_real']:.2f}"
            ))

    def exportar(self):
        if self.df_resultado is None:
            messagebox.showwarning("Atenção", "Calcule primeiro!")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Salvar cálculo real da SEMAE"
        )
        if not path:
            return

        df_exp = self.df_resultado.copy()
        for col in ["valor_original", "correcao_igpm", "multa_2pct", "juros_real", "total_semae_real"]:
            df_exp[col] = df_exp[col].map(lambda x: f"{x:.2f}".replace(".", ","))
        df_exp["vencimento"] = df_exp["vencimento"].dt.strftime("%d/%m/%Y")
        df_exp.to_csv(path, index=False, sep=";", decimal=",")
        messagebox.showinfo("Sucesso", f"Arquivo salvo:\n{path}")

    def mostrar_metodologia(self):
        top = tk.Toplevel(self.root)
        top.title("Metodologia de Cálculo")
        top.geometry("700x400")
        text_area = scrolledtext.ScrolledText(top, wrap=tk.WORD, font=("Arial", 10))
        text_area.insert(tk.END, METODOLOGIA)
        text_area.configure(state="disabled")
        text_area.pack(padx=10, pady=10, fill="both", expand=True)

# ----------------------------
# Executar
# ----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = SEMAERealApp(root)
    root.mainloop()
'''
'''
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import os

# ----------------------------
# Configurações (até setembro/2025)
# ----------------------------
DATA_FIM = pd.to_datetime("2025-09-30")  # Correção até set/2025
TAXA_JUROS_REAL = 0.002345  # 0,2345% ao mês (calibrado com cda.csv)
TAXA_MULTA = 0.02           # 2%

METODOLOGIA = """
Cálculo baseado na metodologia real da CDA da SEMAE:

1. VALOR ORIGINAL = coluna 'valor' do CONTASFORMATADAS.csv
2. CORREÇÃO MONETÁRIA:
   - Índice: IGP-M (arquivo indice.csv)
   - Período: mês seguinte ao vencimento até SETEMBRO/2025
   - Aplicada sobre o VALOR ORIGINAL
3. MULTA: 2% do (VALOR ORIGINAL + CORREÇÃO)
4. JUROS: 0,2345% ao mês (simples) sobre (VALOR ORIGINAL + CORREÇÃO)
   - Período: mesmo da correção
   - Taxa calibrada para reproduzir os valores do cda.csv

Esta fórmula replica com alta fidelidade o cálculo real da SEMAE.
"""

# ----------------------------
# Carregar dados
# ----------------------------
def carregar_dados():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    contas_path = os.path.join(script_dir, "CONTASFORMATADAS.csv")
    indices_path = os.path.join(script_dir, "indice.csv")

    # Contas
    contas = pd.read_csv(contas_path, sep=",", quotechar='"', decimal=",")
    contas = contas.dropna(subset=["competencia", "vencimento", "valor"])
    # Remove linha espúria no final ("3.308,39")
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

    # Índices
    igpm = pd.read_csv(indices_path, sep=",", quotechar='"', decimal=",")
    igpm["Data"] = pd.to_datetime(igpm["Data"], format="%m/%Y")
    igpm = igpm.set_index("Data").sort_index()
    igpm["fator"] = 1 + igpm["Indice"] / 100.0

    return contas, igpm

# ----------------------------
# Cálculo
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
        valor_corrigido = valor_orig + correcao
        multa = valor_corrigido * TAXA_MULTA
        n_meses = calcular_meses(venc)
        juros = valor_corrigido * TAXA_JUROS_REAL * n_meses
        total = valor_corrigido + multa + juros

        resultados.append({
            "competencia": row["competencia"],
            "vencimento": venc,
            "valor_original": round(valor_orig, 2),
            "correcao_igpm": round(correcao, 2),
            "multa_2pct": round(multa, 2),
            "juros_real": round(juros, 2),
            "total_semae_real": round(total, 2)
        })
    return pd.DataFrame(resultados)

# ----------------------------
# Interface gráfica
# ----------------------------
class SEMAERealApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cálculo Real da SEMAE (até setembro/2025)")
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
        cols = ("competencia", "vencimento", "valor_original", "correcao_igpm", "multa_2pct", "juros_real", "total_semae_real")
        self.tree = ttk.Treeview(frame_table, columns=cols, show="headings")
        headings = ["Competência", "Vencimento", "Valor Original", "Correção IGP-M", "Multa (2%)", "Juros", "Total SEMAE"]
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
            messagebox.showinfo("Sucesso", "Cálculo concluído até setembro/2025.")
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
                f"R$ {row['juros_real']:.2f}",
                f"R$ {row['total_semae_real']:.2f}"
            ))

    def exportar(self):
        if self.df_resultado is None:
            messagebox.showwarning("Atenção", "Calcule primeiro!")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Salvar cálculo real da SEMAE"
        )
        if not path:
            return

        df_exp = self.df_resultado.copy()
        for col in ["valor_original", "correcao_igpm", "multa_2pct", "juros_real", "total_semae_real"]:
            df_exp[col] = df_exp[col].map(lambda x: f"{x:.2f}".replace(".", ","))
        df_exp["vencimento"] = df_exp["vencimento"].dt.strftime("%d/%m/%Y")
        df_exp.to_csv(path, index=False, sep=";", decimal=",")
        messagebox.showinfo("Sucesso", f"Arquivo salvo:\n{path}")

    def mostrar_metodologia(self):
        top = tk.Toplevel(self.root)
        top.title("Metodologia de Cálculo")
        top.geometry("700x400")
        text_area = scrolledtext.ScrolledText(top, wrap=tk.WORD, font=("Arial", 10))
        text_area.insert(tk.END, METODOLOGIA)
        text_area.configure(state="disabled")
        text_area.pack(padx=10, pady=10, fill="both", expand=True)

# ----------------------------
# Executar
# ----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = SEMAERealApp(root)
    root.mainloop()
'''
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import os

# ----------------------------
# Configurações (até setembro/2025)
# ----------------------------
DATA_FIM = pd.to_datetime("2025-09-30")  # Correção até set/2025
TAXA_JUROS_REAL = 0.002345  # 0,2345% ao mês (calibrado com cda.csv)
TAXA_MULTA = 0.02           # 2%

METODOLOGIA = """
Cálculo baseado na metodologia real da CDA 0000510/2023 da SEMAE, 
com valores atualizados até 30/09/2025.

Fontes dos dados:
- CONTASFORMATADAS.csv: extraído do site https://agenciaweb.semae.rs.gov.br/Home/InfoSegundaViaFaturas em 16/10/2025
- indice.csv: extraído do site https://extra-ibre.fgv.br/IBRE/sitefgvdados/visualizaconsulta.aspx em 16/10/2025

Metodologia:
1. VALOR ORIGINAL = coluna 'valor' do CONTASFORMATADAS.csv
2. CORREÇÃO MONETÁRIA:
   - Índice: IGP-M (arquivo indice.csv)
   - Período: mês seguinte ao vencimento até SETEMBRO/2025
   - Aplicada sobre o VALOR ORIGINAL
3. MULTA: 2% do (VALOR ORIGINAL + CORREÇÃO)
4. JUROS: 0,2345% ao mês (simples) sobre (VALOR ORIGINAL + CORREÇÃO)
   - Período: mesmo da correção
   - Taxa calibrada para reproduzir os valores do cda 0000510/2023

Esta fórmula tenta replicar com alta fidelidade o cálculo real da SEMAE.
conforme o que pudemos apurar na CDA 0000510/2023
"""

# ----------------------------
# Carregar dados
# ----------------------------
def carregar_dados():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    contas_path = os.path.join(script_dir, "CONTASFORMATADAS.csv")
    indices_path = os.path.join(script_dir, "indice.csv")

    # Contas
    contas = pd.read_csv(contas_path, sep=",", quotechar='"', decimal=",")
    contas = contas.dropna(subset=["competencia", "vencimento", "valor"])
    # Remove linha espúria no final ("3.308,39")
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

    # Índices
    igpm = pd.read_csv(indices_path, sep=",", quotechar='"', decimal=",")
    igpm["Data"] = pd.to_datetime(igpm["Data"], format="%m/%Y")
    igpm = igpm.set_index("Data").sort_index()
    igpm["fator"] = 1 + igpm["Indice"] / 100.0

    return contas, igpm

# ----------------------------
# Cálculo
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
        valor_corrigido = valor_orig + correcao
        multa = valor_corrigido * TAXA_MULTA
        n_meses = calcular_meses(venc)
        juros = valor_corrigido * TAXA_JUROS_REAL * n_meses
        total = valor_corrigido + multa + juros

        resultados.append({
            "competencia": row["competencia"],
            "vencimento": venc,
            "valor_original": round(valor_orig, 2),
            "correcao_igpm": round(correcao, 2),
            "multa_2pct": round(multa, 2),
            "juros_real": round(juros, 2),
            "total_semae_real": round(total, 2)
        })
    return pd.DataFrame(resultados)

# ----------------------------
# Interface gráfica
# ----------------------------
class SEMAERealApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cálculo Real da SEMAE (atualizado até 30/09/2025)")
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
        cols = ("competencia", "vencimento", "valor_original", "correcao_igpm", "multa_2pct", "juros_real", "total_semae_real")
        self.tree = ttk.Treeview(frame_table, columns=cols, show="headings")
        headings = ["Competência", "Vencimento", "Valor Original", "Correção IGP-M", "Multa (2%)", "Juros", "Total SEMAE"]
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
            messagebox.showinfo("Sucesso", "Cálculo concluído até 30/09/2025.")
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
                f"R$ {row['juros_real']:.2f}",
                f"R$ {row['total_semae_real']:.2f}"
            ))

    def exportar(self):
        if self.df_resultado is None:
            messagebox.showwarning("Atenção", "Calcule primeiro!")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Salvar cálculo real da SEMAE"
        )
        if not path:
            return

        df_exp = self.df_resultado.copy()
        for col in ["valor_original", "correcao_igpm", "multa_2pct", "juros_real", "total_semae_real"]:
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
    app = SEMAERealApp(root)
    root.mainloop()
