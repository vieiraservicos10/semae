'''## 🐍 3. `corretor_igpm_gui.py` (CÓDIGO COMPLETO)

import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os

# ----------------------------
# Carregar dados
# ----------------------------
def carregar_dados():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    contas_path = os.path.join(script_dir, "CONTASFORMATADAS.csv")
    indices_path = os.path.join(script_dir, "indice.csv")

    # Ler contas
    contas = pd.read_csv(
        contas_path,
        sep=",",
        quotechar='"',
        thousands=None,
        decimal=",",
        dtype={"competencia": str, "tipo": str, "valor": str}
    )
    # Limpar linhas vazias
    contas = contas.dropna(subset=["competencia", "vencimento", "valor"])
    contas["valor"] = pd.to_numeric(contas["valor"].str.replace(".", "").str.replace(",", "."), errors="coerce")
    contas["vencimento"] = pd.to_datetime(contas["vencimento"], dayfirst=True, errors="coerce")

    # Ler índices
    igpm = pd.read_csv(
        indices_path,
        sep=",",
        quotechar='"',
        decimal=","
    )
    igpm["Data"] = pd.to_datetime(igpm["Data"], format="%m/%Y")
    igpm = igpm.set_index("Data").sort_index()
    igpm["fator"] = 1 + igpm["Indice"] / 100.0

    return contas, igpm

# ----------------------------
# Gerar demonstrativo analítico
# ----------------------------
def gerar_demonstrativo(conta_row, igpm_series, mes_fim_str):
    vencimento = conta_row["vencimento"]
    valor_inicial = conta_row["valor"]
    competencia = conta_row["competencia"]

    if pd.isna(vencimento) or pd.isna(valor_inicial):
        return pd.DataFrame()

    try:
        mes_fim = pd.Period(mes_fim_str, freq="M")
    except:
        raise ValueError("Formato de data inválido. Use MM/AAAA.")

    mes_inicio = vencimento.to_period("M") + 1
    if mes_inicio > mes_fim:
        return pd.DataFrame([{
            "Competência Original": competencia,
            "Mês de Correção": "—",
            "Índice (%)": 0.0000,
            "Fator": 1.000000,
            "Valor Atualizado": valor_inicial
        }])

    dt_inicio = mes_inicio.start_time
    dt_fim = mes_fim.end_time
    fatores = igpm_series.loc[dt_inicio:dt_fim]

    if fatores.empty:
        return pd.DataFrame([{
            "Competência Original": competencia,
            "Mês de Correção": "Sem índices",
            "Índice (%)": 0.0000,
            "Fator": 1.000000,
            "Valor Atualizado": valor_inicial
        }])

    evolucao = []
    valor_atual = valor_inicial

    for dt, row in fatores.iterrows():
        mes_str = dt.strftime("%m/%Y")
        indice_pct = (row["fator"] - 1) * 100
        fator = row["fator"]
        valor_atual *= fator
        evolucao.append({
            "Competência Original": competencia,
            "Mês de Correção": mes_str,
            "Índice (%)": round(indice_pct, 4),
            "Fator": round(fator, 6),
            "Valor Atualizado": round(valor_atual, 2)
        })

    return pd.DataFrame(evolucao)

# ----------------------------
# Aplicação principal
# ----------------------------
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Corretor de Contas pelo IGP-M")
        self.root.geometry("950x600")

        try:
            self.contas_original, self.igpm = carregar_dados()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar arquivos:\n{e}")
            root.destroy()
            return

        self.contas_corrigidas = None

        # Frame de controle
        frame_ctrl = ttk.Frame(root)
        frame_ctrl.pack(pady=10, padx=10, fill="x")

        ttk.Label(frame_ctrl, text="Corrigir até (MM/AAAA):").pack(side="left")
        self.entry_mes = ttk.Entry(frame_ctrl, width=10)
        self.entry_mes.insert(0, "09/2025")
        self.entry_mes.pack(side="left", padx=5)

        ttk.Button(frame_ctrl, text="Calcular Correção", command=self.calcular_correcao).pack(side="left", padx=5)
        ttk.Button(frame_ctrl, text="Demonstrativo Analítico", command=self.mostrar_demonstrativo).pack(side="left", padx=5)

        # Tabela principal
        frame_table = ttk.Frame(root)
        frame_table.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("competencia", "vencimento", "valor", "valor_corrigido")
        self.tree = ttk.Treeview(frame_table, columns=cols, show="headings")
        for col, txt in zip(cols, ["Competência", "Vencimento", "Valor Original", "Valor Corrigido"]):
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=150, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.carregar_tabela()

    def carregar_tabela(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        df = self.contas_original if self.contas_corrigidas is None else self.contas_corrigidas
        for _, row in df.iterrows():
            venc = row["vencimento"].strftime("%d/%m/%Y") if pd.notna(row["vencimento"]) else ""
            val_orig = f"R$ {row['valor']:.2f}" if pd.notna(row["valor"]) else ""
            val_corr = f"R$ {row.get('valor_corrigido', ''):.2f}" if self.contas_corrigidas is not None and pd.notna(row.get('valor_corrigido', None)) else ""
            self.tree.insert("", "end", values=(row["competencia"], venc, val_orig, val_corr))

    def calcular_correcao(self):
        mes_fim = self.entry_mes.get().strip()
        if not mes_fim:
            mes_fim = "09/2025"

        try:
            mes_fim_period = pd.Period(mes_fim, freq="M")
        except:
            messagebox.showerror("Erro", "Formato de data inválido. Use MM/AAAA.")
            return

        def aplicar(row):
            venc = row["vencimento"]
            if pd.isna(venc):
                return row["valor"]
            mes_inicio = venc.to_period("M") + 1
            if mes_inicio > mes_fim_period:
                return row["valor"]
            dt_inicio = mes_inicio.start_time
            dt_fim = mes_fim_period.end_time
            fatores = self.igpm.loc[dt_inicio:dt_fim, "fator"]
            fator_acum = fatores.prod() if not fatores.empty else 1.0
            return row["valor"] * fator_acum

        self.contas_corrigidas = self.contas_original.copy()
        self.contas_corrigidas["valor_corrigido"] = self.contas_corrigidas.apply(aplicar, axis=1)
        self.contas_corrigidas["valor_corrigido"] = self.contas_corrigidas["valor_corrigido"].round(2)
        self.carregar_tabela()
        messagebox.showinfo("Sucesso", "Correção calculada até " + mes_fim + ".")

    def mostrar_demonstrativo(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione uma conta na tabela.")
            return

        valores = self.tree.item(selected, "values")
        competencia_sel = valores[0]

        df_base = self.contas_corrigidas if self.contas_corrigidas is not None else self.contas_original
        conta = df_base[df_base["competencia"] == competencia_sel]
        if conta.empty:
            messagebox.showerror("Erro", "Conta não encontrada.")
            return
        conta_row = conta.iloc[0]

        mes_fim = self.entry_mes.get().strip() or "09/2025"
        try:
            df_demo = gerar_demonstrativo(conta_row, self.igpm[["fator"]], mes_fim)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao gerar demonstrativo:\n{e}")
            return

        # Janela de demonstrativo
        top = tk.Toplevel(self.root)
        top.title(f"Demonstrativo Analítico - {competencia_sel}")
        top.geometry("800x500")

        frame = ttk.Frame(top)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        cols = list(df_demo.columns)
        tree_demo = ttk.Treeview(frame, columns=cols, show="headings")
        for col in cols:
            tree_demo.heading(col, text=col)
            tree_demo.column(col, width=130, anchor="center")
        tree_demo.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree_demo.yview)
        scroll.pack(side="right", fill="y")
        tree_demo.configure(yscrollcommand=scroll.set)

        for _, row in df_demo.iterrows():
            vals = []
            for col in cols:
                if col == "Valor Atualizado":
                    vals.append(f"R$ {row[col]:.2f}")
                elif col == "Índice (%)":
                    vals.append(f"{row[col]:.4f}")
                elif col == "Fator":
                    vals.append(f"{row[col]:.6f}")
                else:
                    vals.append(row[col])
            tree_demo.insert("", "end", values=vals)

        def exportar_demo():
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Salvar Demonstrativo Analítico"
            )
            if path:
                df_demo.to_csv(path, index=False, sep=";", decimal=",")
                messagebox.showinfo("Sucesso", "Demonstrativo exportado!")

        ttk.Button(top, text="Exportar Demonstrativo", command=exportar_demo).pack(pady=5)

# ----------------------------
# Executar
# ----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
'''
'''
# versao com impressão
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# ----------------------------
# Carregar dados
# ----------------------------
def carregar_dados():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    contas_path = os.path.join(script_dir, "CONTASFORMATADAS.csv")
    indices_path = os.path.join(script_dir, "indice.csv")

    contas = pd.read_csv(
        contas_path,
        sep=",",
        quotechar='"',
        decimal=",",
        dtype={"competencia": str, "tipo": str}
    )
    contas = contas.dropna(subset=["competencia", "vencimento", "valor"])
    contas["valor"] = pd.to_numeric(contas["valor"].astype(str).str.replace(".", "").str.replace(",", "."), errors="coerce")
    contas["vencimento"] = pd.to_datetime(contas["vencimento"], dayfirst=True, errors="coerce")

    igpm = pd.read_csv(indices_path, sep=",", quotechar='"', decimal=",")
    igpm["Data"] = pd.to_datetime(igpm["Data"], format="%m/%Y")
    igpm = igpm.set_index("Data").sort_index()
    igpm["fator"] = 1 + igpm["Indice"] / 100.0

    return contas, igpm

# ----------------------------
# Gerar demonstrativo
# ----------------------------
def gerar_demonstrativo(conta_row, igpm_series, mes_fim_str):
    vencimento = conta_row["vencimento"]
    valor_inicial = conta_row["valor"]
    competencia = conta_row["competencia"]

    if pd.isna(vencimento) or pd.isna(valor_inicial):
        return pd.DataFrame()

    try:
        mes_fim = pd.Period(mes_fim_str, freq="M")
    except:
        raise ValueError("Formato de data inválido. Use MM/AAAA.")

    mes_inicio = vencimento.to_period("M") + 1
    if mes_inicio > mes_fim:
        return pd.DataFrame([{
            "Competência Original": competencia,
            "Mês de Correção": "—",
            "Índice (%)": 0.0000,
            "Fator": 1.000000,
            "Valor Atualizado": valor_inicial
        }])

    dt_inicio = mes_inicio.start_time
    dt_fim = mes_fim.end_time
    fatores = igpm_series.loc[dt_inicio:dt_fim]

    if fatores.empty:
        return pd.DataFrame([{
            "Competência Original": competencia,
            "Mês de Correção": "Sem índices",
            "Índice (%)": 0.0000,
            "Fator": 1.000000,
            "Valor Atualizado": valor_inicial
        }])

    evolucao = []
    valor_atual = valor_inicial
    for dt, row in fatores.iterrows():
        mes_str = dt.strftime("%m/%Y")
        indice_pct = (row["fator"] - 1) * 100
        fator = row["fator"]
        valor_atual *= fator
        evolucao.append({
            "Competência Original": competencia,
            "Mês de Correção": mes_str,
            "Índice (%)": round(indice_pct, 4),
            "Fator": round(fator, 6),
            "Valor Atualizado": round(valor_atual, 2)
        })
    return pd.DataFrame(evolucao)

# ----------------------------
# Gerar PDF do demonstrativo
# ----------------------------
def gerar_pdf_demonstrativo(df_demo, competencia, filepath):
    doc = SimpleDocTemplate(filepath, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    title = Paragraph(f"Demonstrativo Analítico - Competência {competencia}", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))

    # Cabeçalho
    data = [list(df_demo.columns)]
    for _, row in df_demo.iterrows():
        linha = []
        for col in df_demo.columns:
            if col == "Valor Atualizado":
                linha.append(f"R$ {row[col]:.2f}")
            elif col == "Índice (%)":
                linha.append(f"{row[col]:.4f}")
            elif col == "Fator":
                linha.append(f"{row[col]:.6f}")
            else:
                linha.append(str(row[col]))
        data.append(linha)

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTSIZE', (0,1), (-1,-1), 9),
    ]))

    story.append(table)
    doc.build(story)

# ----------------------------
# Aplicação principal
# ----------------------------
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Corretor de Contas pelo IGP-M")
        self.root.geometry("980x620")

        try:
            self.contas_original, self.igpm = carregar_dados()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar arquivos:\n{e}")
            root.destroy()
            return

        self.contas_corrigidas = None

        # Frame de controle
        frame_ctrl = ttk.Frame(root)
        frame_ctrl.pack(pady=10, padx=10, fill="x")

        ttk.Label(frame_ctrl, text="Corrigir até (MM/AAAA):").pack(side="left")
        self.entry_mes = ttk.Entry(frame_ctrl, width=10)
        self.entry_mes.insert(0, "09/2025")
        self.entry_mes.pack(side="left", padx=5)

        ttk.Button(frame_ctrl, text="Calcular Correção", command=self.calcular_correcao).pack(side="left", padx=5)
        ttk.Button(frame_ctrl, text="Demonstrativo Analítico", command=self.mostrar_demonstrativo).pack(side="left", padx=5)
        ttk.Button(frame_ctrl, text="Exportar Todas as Contas", command=self.exportar_todas).pack(side="left", padx=5)

        # Tabela
        frame_table = ttk.Frame(root)
        frame_table.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("competencia", "vencimento", "valor", "valor_corrigido")
        self.tree = ttk.Treeview(frame_table, columns=cols, show="headings")
        for col, txt in zip(cols, ["Competência", "Vencimento", "Valor Original", "Valor Corrigido"]):
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=150, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.carregar_tabela()

    def carregar_tabela(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        df = self.contas_original if self.contas_corrigidas is None else self.contas_corrigidas
        for _, row in df.iterrows():
            venc = row["vencimento"].strftime("%d/%m/%Y") if pd.notna(row["vencimento"]) else ""
            val_orig = f"R$ {row['valor']:.2f}" if pd.notna(row["valor"]) else ""
            val_corr = f"R$ {row.get('valor_corrigido', ''):.2f}" if self.contas_corrigidas is not None and pd.notna(row.get('valor_corrigido', None)) else ""
            self.tree.insert("", "end", values=(row["competencia"], venc, val_orig, val_corr))

    def calcular_correcao(self):
        mes_fim = self.entry_mes.get().strip() or "09/2025"
        try:
            mes_fim_period = pd.Period(mes_fim, freq="M")
        except:
            messagebox.showerror("Erro", "Formato de data inválido. Use MM/AAAA.")
            return

        def aplicar(row):
            venc = row["vencimento"]
            if pd.isna(venc):
                return row["valor"]
            mes_inicio = venc.to_period("M") + 1
            if mes_inicio > mes_fim_period:
                return row["valor"]
            dt_inicio = mes_inicio.start_time
            dt_fim = mes_fim_period.end_time
            fatores = self.igpm.loc[dt_inicio:dt_fim, "fator"]
            fator_acum = fatores.prod() if not fatores.empty else 1.0
            return row["valor"] * fator_acum

        self.contas_corrigidas = self.contas_original.copy()
        self.contas_corrigidas["valor_corrigido"] = self.contas_corrigidas.apply(aplicar, axis=1)
        self.contas_corrigidas["valor_corrigido"] = self.contas_corrigidas["valor_corrigido"].round(2)
        self.carregar_tabela()
        messagebox.showinfo("Sucesso", f"Correção calculada até {mes_fim}.")

    def mostrar_demonstrativo(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione uma conta na tabela.")
            return

        valores = self.tree.item(selected, "values")
        competencia_sel = valores[0]

        df_base = self.contas_corrigidas if self.contas_corrigidas is not None else self.contas_original
        conta = df_base[df_base["competencia"] == competencia_sel]
        if conta.empty:
            messagebox.showerror("Erro", "Conta não encontrada.")
            return
        conta_row = conta.iloc[0]

        mes_fim = self.entry_mes.get().strip() or "09/2025"
        try:
            df_demo = gerar_demonstrativo(conta_row, self.igpm[["fator"]], mes_fim)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao gerar demonstrativo:\n{e}")
            return

        top = tk.Toplevel(self.root)
        top.title(f"Demonstrativo Analítico - {competencia_sel}")
        top.geometry("820x520")

        frame = ttk.Frame(top)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        cols = list(df_demo.columns)
        tree_demo = ttk.Treeview(frame, columns=cols, show="headings")
        for col in cols:
            tree_demo.heading(col, text=col)
            tree_demo.column(col, width=130, anchor="center")
        tree_demo.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree_demo.yview)
        scroll.pack(side="right", fill="y")
        tree_demo.configure(yscrollcommand=scroll.set)

        for _, row in df_demo.iterrows():
            vals = []
            for col in cols:
                if col == "Valor Atualizado":
                    vals.append(f"R$ {row[col]:.2f}")
                elif col == "Índice (%)":
                    vals.append(f"{row[col]:.4f}")
                elif col == "Fator":
                    vals.append(f"{row[col]:.6f}")
                else:
                    vals.append(row[col])
            tree_demo.insert("", "end", values=vals)

        def exportar_demo_csv():
            path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
            if path:
                df_demo.to_csv(path, index=False, sep=";", decimal=",")
                messagebox.showinfo("Sucesso", "Demonstrativo exportado em CSV!")

        def exportar_demo_pdf():
            path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
            if path:
                try:
                    gerar_pdf_demonstrativo(df_demo, competencia_sel, path)
                    messagebox.showinfo("Sucesso", "PDF gerado com sucesso!")
                except Exception as e:
                    messagebox.showerror("Erro", f"Falha ao gerar PDF:\n{e}")

        btn_frame = ttk.Frame(top)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Exportar CSV", command=exportar_demo_csv).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Gerar PDF", command=exportar_demo_pdf).pack(side="left", padx=5)

    def exportar_todas(self):
        if self.contas_corrigidas is None:
            messagebox.showwarning("Atenção", "Calcule a correção primeiro!")
            return

        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return

        df_export = self.contas_corrigidas.copy()
        df_export["valor"] = df_export["valor"].map(lambda x: f"{x:.2f}".replace(".", ","))
        df_export["valor_corrigido"] = df_export["valor_corrigido"].map(lambda x: f"{x:.2f}".replace(".", ","))
        df_export.to_csv(path, index=False, sep=";", decimal=",")
        messagebox.showinfo("Sucesso", f"Todas as contas corrigidas foram exportadas!\nArquivo: {path}")

# ----------------------------
# Executar
# ----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
'''
'''
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import os

# ----------------------------
# Configuração
# ----------------------------
DATA_FIM = pd.to_datetime("2025-09-30")  # Até setembro/2025

METODOLOGIA = """
Cálculo de atualização monetária justa,  
com valores corrigidos apenas pelo IGP-M até 30/09/2025.

Fontes dos dados:
- CONTASFORMATADAS.csv: extraído do site https://agenciaweb.semae.rs.gov.br/Home/InfoSegundaViaFaturas em 16/10/2025
- indice.csv: extraído do site https://extra-ibre.fgv.br/IBRE/sitefgvdados/visualizaconsulta.aspx em 16/10/2025

Metodologia:
1. VALOR ORIGINAL = coluna 'valor' do CONTASFORMATADAS.csv
2. CORREÇÃO MONETÁRIA:
   - Índice: IGP-M (arquivo indice.csv)
   - Período: do mês seguinte ao vencimento até SETEMBRO/2025
   - Aplicada sobre o VALOR ORIGINAL
3. NÃO são aplicados:
   - Multa
   - Juros
   - Quaisquer encargos administrativos

Este cálculo representa o valor atualizado apenas pela inflação,
sem penalidades, conforme princípios de justiça e proporcionalidade.
Para fins de acordo, para resolver a contenda. E evitar, um processo
moroso, oneroso e custoso. onde as custas(honorários, custas judiciais,
tempo empregado, peritos), superariam em muito o valor da causa. 
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
# Cálculo da correção
# ----------------------------
def aplicar_correcao_igpm(valor, vencimento, igpm_series):
    inicio = (vencimento + pd.DateOffset(days=1)).to_period("M")
    fim = DATA_FIM.to_period("M")
    if inicio > fim:
        return valor  # sem correção
    dt_inicio = inicio.start_time
    dt_fim = fim.end_time
    fatores = igpm_series.loc[dt_inicio:dt_fim]
    fator_acum = fatores.prod() if not fatores.empty else 1.0
    return valor * fator_acum

def processar_contas(contas, igpm):
    resultados = []
    igpm_fatores = igpm["fator"]
    for _, row in contas.iterrows():
        venc = row["vencimento"]
        valor_orig = row["valor"]
        valor_corrigido = aplicar_correcao_igpm(valor_orig, venc, igpm_fatores)
        resultados.append({
            "competencia": row["competencia"],
            "vencimento": venc,
            "valor_original": round(valor_orig, 2),
            "valor_corrigido_igpm": round(valor_corrigido, 2)
        })
    return pd.DataFrame(resultados)

# ----------------------------
# Interface gráfica
# ----------------------------
class CorretorIGPMApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Corretor pelo IGP-M (até 30/09/2025)")
        self.root.geometry("800x500")

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
        cols = ("competencia", "vencimento", "valor_original", "valor_corrigido_igpm")
        self.tree = ttk.Treeview(frame_table, columns=cols, show="headings")
        headings = ["Competência", "Vencimento", "Valor Original", "Valor Corrigido (IGP-M)"]
        for col, txt in zip(cols, headings):
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=150, anchor="center")
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
            self.tree.insert("", "end", values=(row["competencia"], venc, f"R$ {row['valor']:.2f}", ""))

    def calcular(self):
        try:
            self.df_resultado = processar_contas(self.contas, self.igpm)
            self.atualizar_tabela()
            messagebox.showinfo("Sucesso", "Correção pelo IGP-M concluída até 30/09/2025.")
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
                f"R$ {row['valor_corrigido_igpm']:.2f}"
            ))

    def exportar(self):
        if self.df_resultado is None:
            messagebox.showwarning("Atenção", "Calcule primeiro!")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Salvar correção pelo IGP-M"
        )
        if not path:
            return

        df_exp = self.df_resultado.copy()
        for col in ["valor_original", "valor_corrigido_igpm"]:
            df_exp[col] = df_exp[col].map(lambda x: f"{x:.2f}".replace(".", ","))
        df_exp["vencimento"] = df_exp["vencimento"].dt.strftime("%d/%m/%Y")
        df_exp.to_csv(path, index=False, sep=";", decimal=",")
        messagebox.showinfo("Sucesso", f"Arquivo salvo:\n{path}")

    def mostrar_metodologia(self):
        top = tk.Toplevel(self.root)
        top.title("Metodologia de Cálculo")
        top.geometry("720x400")
        text_area = scrolledtext.ScrolledText(top, wrap=tk.WORD, font=("Arial", 10))
        text_area.insert(tk.END, METODOLOGIA)
        text_area.configure(state="disabled")
        text_area.pack(padx=10, pady=10, fill="both", expand=True)

# ----------------------------
# Executar
# ----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = CorretorIGPMApp(root)
    root.mainloop()
'''
# versao com impressão
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# ----------------------------
# Metodologia explicativa
# ----------------------------
METODOLOGIA = """
Cálculo de atualização monetária justa,  
com valores corrigidos apenas pelo IGP-M até 30/09/2025.

Fontes dos dados:
- CONTASFORMATADAS.csv: extraído do site https://agenciaweb.semae.rs.gov.br/Home/InfoSegundaViaFaturas em 16/10/2025
- indice.csv: extraído do site https://extra-ibre.fgv.br/IBRE/sitefgvdados/visualizaconsulta.aspx em 16/10/2025

Metodologia:
1. VALOR ORIGINAL = coluna 'valor' do CONTASFORMATADAS.csv
2. CORREÇÃO MONETÁRIA:
   - Índice: IGP-M (arquivo indice.csv)
   - Período: do mês seguinte ao vencimento até SETEMBRO/2025
   - Aplicada sobre o VALOR ORIGINAL
3. NÃO são aplicados:
   - Multa
   - Juros
   - Quaisquer encargos administrativos

Este cálculo representa o valor atualizado apenas pela inflação,
sem penalidades, conforme princípios de justiça e proporcionalidade.
Para fins de acordo, para resolver a contenda. E evitar, um processo
moroso, oneroso e custoso. onde as custas(honorários, custas judiciais,
tempo empregado, peritos), superariam em muito o valor da causa. 
A proposta é simples. 
Pagamento das faturas com até 10 anos. Contadas a partir de outubro de 
2025. Atualizadas pelo IGP-M da FGV.
Sem multas ou juros.
Pagas da seguinte forma: 4000 a vista. e o restante com cheque para 30
dias. 
"""

# ----------------------------
# Carregar dados
# ----------------------------
def carregar_dados():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    contas_path = os.path.join(script_dir, "CONTASFORMATADAS.csv")
    indices_path = os.path.join(script_dir, "indice.csv")

    contas = pd.read_csv(
        contas_path,
        sep=",",
        quotechar='"',
        decimal=",",
        dtype={"competencia": str, "tipo": str}
    )
    contas = contas.dropna(subset=["competencia", "vencimento", "valor"])
    contas["valor"] = pd.to_numeric(contas["valor"].astype(str).str.replace(".", "").str.replace(",", "."), errors="coerce")
    contas["vencimento"] = pd.to_datetime(contas["vencimento"], dayfirst=True, errors="coerce")

    igpm = pd.read_csv(indices_path, sep=",", quotechar='"', decimal=",")
    igpm["Data"] = pd.to_datetime(igpm["Data"], format="%m/%Y")
    igpm = igpm.set_index("Data").sort_index()
    igpm["fator"] = 1 + igpm["Indice"] / 100.0

    return contas, igpm

# ----------------------------
# Gerar demonstrativo
# ----------------------------
def gerar_demonstrativo(conta_row, igpm_series, mes_fim_str):
    vencimento = conta_row["vencimento"]
    valor_inicial = conta_row["valor"]
    competencia = conta_row["competencia"]

    if pd.isna(vencimento) or pd.isna(valor_inicial):
        return pd.DataFrame()

    try:
        mes_fim = pd.Period(mes_fim_str, freq="M")
    except:
        raise ValueError("Formato de data inválido. Use MM/AAAA.")

    mes_inicio = vencimento.to_period("M") + 1
    if mes_inicio > mes_fim:
        return pd.DataFrame([{
            "Competência Original": competencia,
            "Mês de Correção": "—",
            "Índice (%)": 0.0000,
            "Fator": 1.000000,
            "Valor Atualizado": valor_inicial
        }])

    dt_inicio = mes_inicio.start_time
    dt_fim = mes_fim.end_time
    fatores = igpm_series.loc[dt_inicio:dt_fim]

    if fatores.empty:
        return pd.DataFrame([{
            "Competência Original": competencia,
            "Mês de Correção": "Sem índices",
            "Índice (%)": 0.0000,
            "Fator": 1.000000,
            "Valor Atualizado": valor_inicial
        }])

    evolucao = []
    valor_atual = valor_inicial
    for dt, row in fatores.iterrows():
        mes_str = dt.strftime("%m/%Y")
        indice_pct = (row["fator"] - 1) * 100
        fator = row["fator"]
        valor_atual *= fator
        evolucao.append({
            "Competência Original": competencia,
            "Mês de Correção": mes_str,
            "Índice (%)": round(indice_pct, 4),
            "Fator": round(fator, 6),
            "Valor Atualizado": round(valor_atual, 2)
        })
    return pd.DataFrame(evolucao)

# ----------------------------
# Gerar PDF do demonstrativo
# ----------------------------
def gerar_pdf_demonstrativo(df_demo, competencia, filepath):
    doc = SimpleDocTemplate(filepath, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    title = Paragraph(f"Demonstrativo Analítico - Competência {competencia}", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))

    # Cabeçalho
    data = [list(df_demo.columns)]
    for _, row in df_demo.iterrows():
        linha = []
        for col in df_demo.columns:
            if col == "Valor Atualizado":
                linha.append(f"R$ {row[col]:.2f}")
            elif col == "Índice (%)":
                linha.append(f"{row[col]:.4f}")
            elif col == "Fator":
                linha.append(f"{row[col]:.6f}")
            else:
                linha.append(str(row[col]))
        data.append(linha)

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTSIZE', (0,1), (-1,-1), 9),
    ]))

    story.append(table)
    doc.build(story)

# ----------------------------
# Aplicação principal
# ----------------------------
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Corretor de Contas pelo IGP-M")
        self.root.geometry("980x620")

        try:
            self.contas_original, self.igpm = carregar_dados()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar arquivos:\n{e}")
            root.destroy()
            return

        self.contas_corrigidas = None

        # Frame de controle
        frame_ctrl = ttk.Frame(root)
        frame_ctrl.pack(pady=10, padx=10, fill="x")

        ttk.Label(frame_ctrl, text="Corrigir até (MM/AAAA):").pack(side="left")
        self.entry_mes = ttk.Entry(frame_ctrl, width=10)
        self.entry_mes.insert(0, "09/2025")
        self.entry_mes.pack(side="left", padx=5)

        ttk.Button(frame_ctrl, text="Calcular Correção", command=self.calcular_correcao).pack(side="left", padx=5)
        ttk.Button(frame_ctrl, text="Demonstrativo Analítico", command=self.mostrar_demonstrativo).pack(side="left", padx=5)
        ttk.Button(frame_ctrl, text="Exportar Todas as Contas", command=self.exportar_todas).pack(side="left", padx=5)
        ttk.Button(frame_ctrl, text="Como foi calculado?", command=self.mostrar_metodologia).pack(side="left", padx=5)

        # Tabela
        frame_table = ttk.Frame(root)
        frame_table.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("competencia", "vencimento", "valor", "valor_corrigido")
        self.tree = ttk.Treeview(frame_table, columns=cols, show="headings")
        for col, txt in zip(cols, ["Competência", "Vencimento", "Valor Original", "Valor Corrigido"]):
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=150, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.carregar_tabela()

    def carregar_tabela(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        df = self.contas_original if self.contas_corrigidas is None else self.contas_corrigidas
        for _, row in df.iterrows():
            venc = row["vencimento"].strftime("%d/%m/%Y") if pd.notna(row["vencimento"]) else ""
            val_orig = f"R$ {row['valor']:.2f}" if pd.notna(row["valor"]) else ""
            val_corr = f"R$ {row.get('valor_corrigido', ''):.2f}" if self.contas_corrigidas is not None and pd.notna(row.get('valor_corrigido', None)) else ""
            self.tree.insert("", "end", values=(row["competencia"], venc, val_orig, val_corr))

    def calcular_correcao(self):
        mes_fim = self.entry_mes.get().strip() or "09/2025"
        try:
            mes_fim_period = pd.Period(mes_fim, freq="M")
        except:
            messagebox.showerror("Erro", "Formato de data inválido. Use MM/AAAA.")
            return

        def aplicar(row):
            venc = row["vencimento"]
            if pd.isna(venc):
                return row["valor"]
            mes_inicio = venc.to_period("M") + 1
            if mes_inicio > mes_fim_period:
                return row["valor"]
            dt_inicio = mes_inicio.start_time
            dt_fim = mes_fim_period.end_time
            fatores = self.igpm.loc[dt_inicio:dt_fim, "fator"]
            fator_acum = fatores.prod() if not fatores.empty else 1.0
            return row["valor"] * fator_acum

        self.contas_corrigidas = self.contas_original.copy()
        self.contas_corrigidas["valor_corrigido"] = self.contas_corrigidas.apply(aplicar, axis=1)
        self.contas_corrigidas["valor_corrigido"] = self.contas_corrigidas["valor_corrigido"].round(2)
        self.carregar_tabela()
        messagebox.showinfo("Sucesso", f"Correção calculada até {mes_fim}.")

    def mostrar_demonstrativo(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione uma conta na tabela.")
            return

        valores = self.tree.item(selected, "values")
        competencia_sel = valores[0]

        df_base = self.contas_corrigidas if self.contas_corrigidas is not None else self.contas_original
        conta = df_base[df_base["competencia"] == competencia_sel]
        if conta.empty:
            messagebox.showerror("Erro", "Conta não encontrada.")
            return
        conta_row = conta.iloc[0]

        mes_fim = self.entry_mes.get().strip() or "09/2025"
        try:
            df_demo = gerar_demonstrativo(conta_row, self.igpm[["fator"]], mes_fim)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao gerar demonstrativo:\n{e}")
            return

        top = tk.Toplevel(self.root)
        top.title(f"Demonstrativo Analítico - {competencia_sel}")
        top.geometry("820x520")

        frame = ttk.Frame(top)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        cols = list(df_demo.columns)
        tree_demo = ttk.Treeview(frame, columns=cols, show="headings")
        for col in cols:
            tree_demo.heading(col, text=col)
            tree_demo.column(col, width=130, anchor="center")
        tree_demo.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree_demo.yview)
        scroll.pack(side="right", fill="y")
        tree_demo.configure(yscrollcommand=scroll.set)

        for _, row in df_demo.iterrows():
            vals = []
            for col in cols:
                if col == "Valor Atualizado":
                    vals.append(f"R$ {row[col]:.2f}")
                elif col == "Índice (%)":
                    vals.append(f"{row[col]:.4f}")
                elif col == "Fator":
                    vals.append(f"{row[col]:.6f}")
                else:
                    vals.append(row[col])
            tree_demo.insert("", "end", values=vals)

        def exportar_demo_csv():
            path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
            if path:
                df_demo.to_csv(path, index=False, sep=";", decimal=",")
                messagebox.showinfo("Sucesso", "Demonstrativo exportado em CSV!")

        def exportar_demo_pdf():
            path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
            if path:
                try:
                    gerar_pdf_demonstrativo(df_demo, competencia_sel, path)
                    messagebox.showinfo("Sucesso", "PDF gerado com sucesso!")
                except Exception as e:
                    messagebox.showerror("Erro", f"Falha ao gerar PDF:\n{e}")

        btn_frame = ttk.Frame(top)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Exportar CSV", command=exportar_demo_csv).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Gerar PDF", command=exportar_demo_pdf).pack(side="left", padx=5)

    def exportar_todas(self):
        if self.contas_corrigidas is None:
            messagebox.showwarning("Atenção", "Calcule a correção primeiro!")
            return

        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return

        df_export = self.contas_corrigidas.copy()
        df_export["valor"] = df_export["valor"].map(lambda x: f"{x:.2f}".replace(".", ","))
        df_export["valor_corrigido"] = df_export["valor_corrigido"].map(lambda x: f"{x:.2f}".replace(".", ","))
        df_export.to_csv(path, index=False, sep=";", decimal=",")
        messagebox.showinfo("Sucesso", f"Todas as contas corrigidas foram exportadas!\nArquivo: {path}")

    def mostrar_metodologia(self):
        top = tk.Toplevel(self.root)
        top.title("Metodologia de Cálculo")
        top.geometry("720x400")
        
        text_frame = ttk.Frame(top)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, wrap="word", font=("Arial", 10))
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.insert("1.0", METODOLOGIA)
        text_widget.configure(state="disabled")
        
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

# ----------------------------
# Executar
# ----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
