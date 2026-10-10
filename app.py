import io
import re
import csv
import math
import unicodedata
from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
import streamlit as st

st.set_page_config(page_title="Analitica de Facturacion en Salud", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

EXPECTED = [
    "ID_Factura", "Numero_Radicado", "Fecha_Servicio", "Fecha_Emision", "Fecha_Radicacion",
    "Fecha_Aceptacion", "Fecha_Pago", "Periodo_Cierre", "Codigo_Entidad", "Entidad_Pagadora",
    "Regimen", "Sede", "Codigo_Servicio", "Servicio", "Linea_Servicio", "Cantidad",
    "Canal_Radicacion", "Estado_Factura", "Dias_Emision_Radicacion", "Soporte_Completo",
    "Valor_Bruto", "Descuento", "Copago_Cuota", "Valor_Neto", "Glosa_Inicial",
    "Valor_Pagado", "Saldo_Cartera"
]
MINIMUM = ["ID_Factura", "Valor_Neto"]
RECOMMENDED = ["Entidad_Pagadora", "Estado_Factura", "Valor_Pagado", "Saldo_Cartera", "Glosa_Inicial"]
DATES = ["Fecha_Servicio", "Fecha_Emision", "Fecha_Radicacion", "Fecha_Aceptacion", "Fecha_Pago"]
MONEY = ["Valor_Bruto", "Descuento", "Copago_Cuota", "Valor_Neto", "Glosa_Inicial", "Valor_Pagado", "Saldo_Cartera"]
NUMERIC = ["Cantidad", "Dias_Emision_Radicacion"] + MONEY
MONTHS = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}
PALETTE = ["#0B3C5D", "#1D70A2", "#00A6A6", "#F4A261", "#D1495B", "#6C757D"]

ALIASES = {
    "id_factura":"ID_Factura", "factura":"ID_Factura", "numero_factura":"ID_Factura",
    "numero_radicado":"Numero_Radicado", "nro_radicado":"Numero_Radicado", "radicado":"Numero_Radicado",
    "fecha_servicio":"Fecha_Servicio", "fecha_emision":"Fecha_Emision", "fecha_radicacion":"Fecha_Radicacion",
    "fecha_aceptacion":"Fecha_Aceptacion", "fecha_pago":"Fecha_Pago", "periodo_cierre":"Periodo_Cierre",
    "codigo_entidad":"Codigo_Entidad", "entidad_pagadora":"Entidad_Pagadora", "pagador":"Entidad_Pagadora",
    "regimen":"Regimen", "sede":"Sede", "codigo_servicio":"Codigo_Servicio", "servicio":"Servicio",
    "linea_servicio":"Linea_Servicio", "cantidad":"Cantidad", "canal_radicacion":"Canal_Radicacion",
    "estado_factura":"Estado_Factura", "estado":"Estado_Factura", "dias_emision_radicacion":"Dias_Emision_Radicacion",
    "soporte_completo":"Soporte_Completo", "valor_bruto":"Valor_Bruto", "descuento":"Descuento",
    "copago":"Copago_Cuota", "copago_cuota":"Copago_Cuota", "cuota_moderadora":"Copago_Cuota",
    "valor_neto":"Valor_Neto", "glosa":"Glosa_Inicial", "glosa_inicial":"Glosa_Inicial",
    "valor_pagado":"Valor_Pagado", "pago":"Valor_Pagado", "saldo_cartera":"Saldo_Cartera", "cartera":"Saldo_Cartera"
}


def css():
    st.markdown("""<style>
    .main .block-container{padding-top:1.2rem;max-width:1500px}.hero{padding:1.2rem 1.4rem;border-radius:16px;
    background:linear-gradient(115deg,#0B3C5D,#1D70A2);color:white;margin-bottom:1rem}.hero h1{margin:0;color:white}
    .note{padding:.8rem 1rem;border-left:5px solid #F4A261;background:#FFF8EF;border-radius:8px}
    div[data-testid="stMetric"]{background:#F7FAFC;border:1px solid #DDE6ED;padding:12px;border-radius:12px}
    .small{color:#52616B;font-size:.9rem}.ok{color:#147D64}.warn{color:#A65A00}.bad{color:#B42318}
    </style>""", unsafe_allow_html=True)


def header():
    st.markdown("<div class='hero'><h1>ANALITICA DE FACTURACION EN SALUD</h1><p>Facturacion, radicacion, glosas, recaudo y cartera</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='note'>Los resultados dependen de la calidad y estructura del archivo cargado. Esta herramienta facilita el analisis exploratorio y no reemplaza una auditoria financiera, contable, medica o contractual.</div>", unsafe_allow_html=True)


def strip_accents(text):
    return "".join(c for c in unicodedata.normalize("NFKD", str(text)) if not unicodedata.combining(c))


def key_name(name):
    x = strip_accents(name).strip().lower()
    x = re.sub(r"[\s\-]+", "_", x)
    x = re.sub(r"_+", "_", x)
    return x.strip("_")


def detect_renames(columns):
    changes, used = {}, set()
    for col in columns:
        candidate = ALIASES.get(key_name(col))
        if candidate and candidate not in used and candidate not in columns:
            changes[col] = candidate
            used.add(candidate)
    return changes


def unique_columns(cols):
    seen, out = {}, []
    for c in cols:
        if c not in seen:
            seen[c] = 0; out.append(c)
        else:
            seen[c] += 1; out.append(f"{c}_{seen[c]}")
    return out


def parse_money_value(value):
    if pd.isna(value): return np.nan
    if isinstance(value, (int, float, np.number)): return float(value)
    s = re.sub(r"[^0-9,\.\-()]", "", str(value).strip())
    if not s: return np.nan
    negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        thousands = "." if dec == "," else ","
        s = s.replace(thousands, "").replace(dec, ".")
    elif "," in s:
        parts = s.split(",")
        s = "".join(parts) if len(parts[-1]) == 3 and len(parts) > 1 else s.replace(".", "").replace(",", ".")
    elif s.count(".") > 1:
        parts = s.split("."); s = "".join(parts) if len(parts[-1]) == 3 else "".join(parts[:-1]) + "." + parts[-1]
    elif "." in s and len(s.split(".")[-1]) == 3:
        s = s.replace(".", "")
    try:
        number = float(s)
        return -number if negative else number
    except ValueError:
        return np.nan


@st.cache_data(show_spinner=False)
def read_csv_bytes(data, sep_option="automatico"):
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
    seps = [None] if sep_option == "automatico" else [{"coma":",", "punto y coma":";", "tabulacion":"\t"}[sep_option]]
    errors = []
    for enc in encodings:
        for sep in seps:
            try:
                return pd.read_csv(io.BytesIO(data), encoding=enc, sep=sep, engine="python"), enc, sep
            except Exception as exc: errors.append(str(exc))
    raise ValueError("No fue posible interpretar el CSV. Pruebe otro separador.")


@st.cache_data(show_spinner=False)
def excel_sheets(data):
    return pd.ExcelFile(io.BytesIO(data)).sheet_names


@st.cache_data(show_spinner=False)
def read_excel_bytes(data, sheet):
    return pd.read_excel(io.BytesIO(data), sheet_name=sheet)


def convert_types(df):
    out, log = df.copy(), []
    for col in DATES:
        if col in out:
            before = out[col].notna().sum(); out[col] = pd.to_datetime(out[col], errors="coerce", dayfirst=True)
            failed = max(0, before - out[col].notna().sum()); log.append((col, "fecha", failed, int(out[col].isna().sum())))
    for col in MONEY:
        if col in out:
            before = out[col].notna().sum(); out[col] = out[col].map(parse_money_value)
            failed = max(0, before - out[col].notna().sum()); log.append((col, "moneda", failed, int(out[col].isna().sum())))
    for col in ["Cantidad", "Dias_Emision_Radicacion"]:
        if col in out:
            before = out[col].notna().sum(); out[col] = pd.to_numeric(out[col], errors="coerce")
            failed = max(0, before - out[col].notna().sum()); log.append((col, "numero", failed, int(out[col].isna().sum())))
    return out, pd.DataFrame(log, columns=["Columna","Conversion","No convertidos","Nulos resultantes"])


def derive(df):
    d = df.copy()
    if "Fecha_Radicacion" in d:
        f = d["Fecha_Radicacion"]
        d["Ano_Radicacion"] = f.dt.year; d["Numero_Mes"] = f.dt.month
        d["Mes_Radicacion"] = f.dt.month.map(MONTHS); d["Trimestre_Radicacion"] = "T" + f.dt.quarter.astype("Int64").astype(str)
        d["Ano_Mes"] = f.dt.to_period("M").astype(str); d["Dia_Semana"] = f.dt.dayofweek.map({0:"Lunes",1:"Martes",2:"Miercoles",3:"Jueves",4:"Viernes",5:"Sabado",6:"Domingo"})
        if "Periodo_Cierre" not in d: d["Periodo_Cierre"] = d["Ano_Mes"]
    if "Periodo_Cierre" in d:
        d["Periodo_Cierre"] = d["Periodo_Cierre"].astype(str).str.strip().replace({"NaT":np.nan,"nan":np.nan})
    if "Fecha_Emision" in d and "Fecha_Radicacion" in d:
        d["Dias_Emision_Radicacion"] = (d["Fecha_Radicacion"] - d["Fecha_Emision"]).dt.days
    if "Fecha_Pago" in d and "Fecha_Radicacion" in d:
        d["Dias_Radicacion_Pago"] = (d["Fecha_Pago"] - d["Fecha_Radicacion"]).dt.days
    formulas = [("Porcentaje_Descuento","Descuento","Valor_Bruto"),("Porcentaje_Copago","Copago_Cuota","Valor_Bruto"),("Porcentaje_Glosa","Glosa_Inicial","Valor_Neto"),("Porcentaje_Recaudo","Valor_Pagado","Valor_Neto"),("Porcentaje_Cartera","Saldo_Cartera","Valor_Neto")]
    for new, num, den in formulas:
        if num in d and den in d: d[new] = np.where(d[den].ne(0), d[num]/d[den]*100, np.nan)
    if "Glosa_Inicial" in d: d["Tiene_Glosa"] = d["Glosa_Inicial"].fillna(0).gt(0)
    if "Saldo_Cartera" in d: d["Tiene_Saldo"] = d["Saldo_Cartera"].fillna(0).gt(0)
    if "Estado_Factura" in d: d["Es_Pagada"] = d["Estado_Factura"].astype(str).str.casefold().eq("pagada")
    if "Dias_Emision_Radicacion" in d:
        d["Rango_Tiempo_Radicacion"] = pd.cut(d["Dias_Emision_Radicacion"], [-np.inf,3,7,15,np.inf], labels=["0 a 3 dias","4 a 7 dias","8 a 15 dias","Mas de 15 dias"])
    return d.replace([np.inf,-np.inf], np.nan)


def financial_identity_flags(df, tolerance):
    d = df.copy(); d["Inconsistencia_Financiera"] = False
    if all(c in d for c in ["Valor_Neto","Valor_Bruto","Descuento","Copago_Cuota"]):
        expected = d["Valor_Bruto"].fillna(0)-d["Descuento"].fillna(0)-d["Copago_Cuota"].fillna(0)
        d["Inconsistencia_Financiera"] |= (d["Valor_Neto"]-expected).abs().gt(tolerance)
    if all(c in d for c in ["Saldo_Cartera","Valor_Neto","Glosa_Inicial","Valor_Pagado"]):
        expected = d["Valor_Neto"].fillna(0)-d["Glosa_Inicial"].fillna(0)-d["Valor_Pagado"].fillna(0)
        d["Inconsistencia_Financiera"] |= (d["Saldo_Cartera"]-expected).abs().gt(tolerance)
    return d


def quality_report(df, tolerance):
    rows = []
    def add(item, value): rows.append({"Validacion":item,"Resultado":value})
    add("Filas", len(df)); add("Columnas", len(df.columns)); add("Duplicados exactos", int(df.duplicated().sum()))
    if "ID_Factura" in df: add("ID de factura duplicados", int(df["ID_Factura"].duplicated(keep=False).sum()))
    if "Numero_Radicado" in df: add("Radicados duplicados", int(df["Numero_Radicado"].duplicated(keep=False).sum()))
    add("Valores nulos", int(df.isna().sum().sum()))
    for c in MONEY:
        if c in df: add(f"Valores negativos: {c}", int(df[c].lt(0).sum()))
    if "Valor_Neto" in df: add("Valores netos en cero", int(df["Valor_Neto"].eq(0).sum()))
    checks = [("Radicacion anterior a emision","Fecha_Radicacion","Fecha_Emision"),("Pago anterior a radicacion","Fecha_Pago","Fecha_Radicacion")]
    for label,a,b in checks:
        if a in df and b in df: add(label, int(df[a].lt(df[b]).sum()))
    for label,a,b in [("Saldo superior al neto","Saldo_Cartera","Valor_Neto"),("Pago superior al neto","Valor_Pagado","Valor_Neto"),("Glosa superior al neto","Glosa_Inicial","Valor_Neto")]:
        if a in df and b in df: add(label, int(df[a].gt(df[b]+tolerance).sum()))
    flagged = financial_identity_flags(df,tolerance)
    add("Inconsistencias financieras", int(flagged["Inconsistencia_Financiera"].sum()))
    completeness = 100*(1-df.isna().sum().sum()/max(1,df.size))
    uniqueness = 100*(1-df.duplicated().sum()/max(1,len(df)))
    validity_penalty = sum(v["Resultado"] for v in rows if isinstance(v["Resultado"],int) and ("anterior" in v["Validacion"].lower() or "superior" in v["Validacion"].lower()))
    validity = 100*(1-min(validity_penalty/max(1,len(df)),1))
    consistency = 100*(1-flagged["Inconsistencia_Financiera"].mean())
    score = round(np.mean([completeness,uniqueness,validity,consistency]),1)
    nulls = pd.DataFrame({"Columna":df.columns,"Nulos":df.isna().sum().values,"Porcentaje":(df.isna().mean()*100).round(2).values})
    return pd.DataFrame(rows), nulls, score, flagged


def fmt_money(v, label="COP"):
    if pd.isna(v): return "No disponible"
    sign = "-" if v < 0 else ""; text = f"{abs(v):,.0f}".replace(",",".")
    prefix = {"COP":"$ ","USD":"US$ ","EUR":"EUR ","Sin simbolo":""}.get(label, label+" ")
    return sign+prefix+text


def pct(num, den): return np.nan if not den else num/den*100

def plot(fig):
    fig.update_layout(template="plotly_white", colorway=PALETTE, margin=dict(l=20,r=20,t=55,b=20), legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)


def aggregate(df, group):
    agg = {}
    if "ID_Factura" in df: agg["ID_Factura"]="nunique"
    if "Cantidad" in df: agg["Cantidad"]="sum"
    for c in MONEY:
        if c in df: agg[c]="sum"
    if "Dias_Emision_Radicacion" in df: agg["Dias_Emision_Radicacion"]="mean"
    out = df.groupby(group, dropna=False).agg(agg).reset_index()
    if "ID_Factura" in out: out=out.rename(columns={"ID_Factura":"Facturas"})
    if "Valor_Neto" in out:
        out["Ticket_Promedio"] = out["Valor_Neto"]/out.get("Facturas",1)
        if out["Valor_Neto"].sum(): out["Participacion"] = out["Valor_Neto"]/out["Valor_Neto"].sum()*100
    for new,num in [("Porcentaje_Recaudo","Valor_Pagado"),("Porcentaje_Cartera","Saldo_Cartera"),("Porcentaje_Glosa","Glosa_Inicial")]:
        if num in out and "Valor_Neto" in out: out[new]=np.where(out["Valor_Neto"].ne(0),out[num]/out["Valor_Neto"]*100,np.nan)
    return out


def monthly(df):
    period = "Periodo_Cierre" if "Periodo_Cierre" in df else "Ano_Mes" if "Ano_Mes" in df else None
    if not period: return pd.DataFrame()
    m=aggregate(df,period).rename(columns={period:"Periodo"}).sort_values("Periodo")
    if "Valor_Neto" in m:
        m["Crecimiento_Mensual"] = m["Valor_Neto"].pct_change()*100
        m["Acumulado_Anual"] = m["Valor_Neto"].cumsum(); m["Promedio_Movil_3"] = m["Valor_Neto"].rolling(3,min_periods=1).mean()
    return m


def sidebar_filters(df):
    st.sidebar.subheader("Filtros globales")
    if st.sidebar.button("Limpiar filtros", use_container_width=True):
        for k in list(st.session_state):
            if k.startswith("f_"): del st.session_state[k]
        st.rerun()
    mask = pd.Series(True,index=df.index)
    if "Fecha_Radicacion" in df and df["Fecha_Radicacion"].notna().any():
        lo,hi=df["Fecha_Radicacion"].min().date(),df["Fecha_Radicacion"].max().date()
        chosen=st.sidebar.date_input("Rango de radicacion",(lo,hi),key="f_dates")
        if len(chosen)==2: mask &= df["Fecha_Radicacion"].dt.date.between(chosen[0],chosen[1])
    for c in ["Ano_Radicacion","Mes_Radicacion","Entidad_Pagadora","Regimen","Sede","Servicio","Linea_Servicio","Estado_Factura","Canal_Radicacion","Soporte_Completo"]:
        if c in df and df[c].notna().any():
            opts=sorted(df[c].dropna().astype(str).unique().tolist())
            selected=st.sidebar.multiselect(c.replace("_"," "),opts,default=opts,key="f_"+c)
            mask &= df[c].astype(str).isin(selected)
    if "Tiene_Glosa" in df:
        g=st.sidebar.selectbox("Facturas con glosa",["Todas","Si","No"],key="f_glosa")
        if g!="Todas": mask &= df["Tiene_Glosa"].eq(g=="Si")
    if "Tiene_Saldo" in df:
        s=st.sidebar.selectbox("Facturas con saldo",["Todas","Si","No"],key="f_saldo")
        if s!="Todas": mask &= df["Tiene_Saldo"].eq(s=="Si")
    if "Valor_Neto" in df and df["Valor_Neto"].notna().any():
        lo,hi=float(df["Valor_Neto"].min()),float(df["Valor_Neto"].max())
        if lo < hi:
            rng=st.sidebar.slider("Rango de valor neto",lo,hi,(lo,hi),key="f_valor")
            mask &= df["Valor_Neto"].between(*rng)
    filtered=df[mask]
    st.sidebar.metric("Registros visibles",f"{len(filtered):,}",f"{len(filtered)/max(1,len(df))*100:.1f}%")
    return filtered


def show_start(df=None, meta=None):
    st.subheader("Inicio y carga de datos")
    st.write("Cargue un archivo Excel o CSV para validar su estructura, explorar la facturacion y generar analisis descargables.")
    st.info("Columnas minimas: ID_Factura, Valor_Neto y al menos Fecha_Radicacion o Periodo_Cierre. Recomendadas: Entidad_Pagadora, Estado_Factura, Valor_Pagado, Saldo_Cartera y Glosa_Inicial.")
    st.warning("Evite cargar archivos que contengan nombres de pacientes, documentos de identidad, historias clinicas, diagnosticos u otra informacion personal o sensible. Utilice archivos anonimizados y siga las politicas de tratamiento de datos de su organizacion.")
    if df is not None:
        cols=st.columns(5)
        vals=[("Archivo",meta.get("name","")),("Filas",len(df)),("Columnas",len(df.columns)),("Entidades",df["Entidad_Pagadora"].nunique() if "Entidad_Pagadora" in df else "N/D"),("Servicios",df["Servicio"].nunique() if "Servicio" in df else "N/D")]
        for c,(a,b) in zip(cols,vals): c.metric(a,b)
        st.dataframe(df.head(50),use_container_width=True)
        if st.checkbox("Mostrar muestra aleatoria"):
            st.dataframe(df.sample(min(20,len(df)),random_state=42),use_container_width=True)


def show_quality(df,tolerance,log):
    st.subheader("Diagnostico de calidad de datos")
    report,nulls,score,flagged=quality_report(df,tolerance)
    st.metric("Puntaje exploratorio de calidad",f"{score}/100")
    st.caption("El puntaje es un indicador exploratorio de calidad y no reemplaza una auditoria de datos.")
    a,b=st.columns(2); a.dataframe(report,use_container_width=True,hide_index=True); b.dataframe(nulls,use_container_width=True,hide_index=True)
    with st.expander("Conversiones de tipos"): st.dataframe(log,use_container_width=True,hide_index=True)
    with st.expander("Posibles inconsistencias financieras"):
        st.dataframe(flagged[flagged["Inconsistencia_Financiera"]],use_container_width=True)


def show_summary(df,currency):
    st.subheader("Resumen ejecutivo")
    if df.empty: st.warning("Los filtros actuales no tienen registros."); return
    invoices=df["ID_Factura"].nunique() if "ID_Factura" in df else len(df)
    net=df.get("Valor_Neto",pd.Series(dtype=float)).sum(); paid=df.get("Valor_Pagado",pd.Series(dtype=float)).sum(); bal=df.get("Saldo_Cartera",pd.Series(dtype=float)).sum(); glosa=df.get("Glosa_Inicial",pd.Series(dtype=float)).sum()
    metrics=[("Facturacion bruta",fmt_money(df.get("Valor_Bruto",pd.Series(dtype=float)).sum(),currency)),("Facturacion neta",fmt_money(net,currency)),("Facturas",f"{invoices:,}"),("Valor pagado",fmt_money(paid,currency)),("Saldo de cartera",fmt_money(bal,currency)),("Valor glosado",fmt_money(glosa,currency)),("Recaudo",f"{pct(paid,net):.1f}%" if net else "N/D"),("Glosa",f"{pct(glosa,net):.1f}%" if net else "N/D"),("Ticket promedio",fmt_money(net/max(1,invoices),currency))]
    for i in range(0,len(metrics),3):
        cols=st.columns(3)
        for c,(label,value) in zip(cols,metrics[i:i+3]): c.metric(label,value)
    m=monthly(df)
    if not m.empty and "Valor_Neto" in m:
        plot(px.line(m,x="Periodo",y="Valor_Neto",markers=True,title="Facturacion neta por periodo"))
        vals=[c for c in ["Valor_Neto","Valor_Pagado","Saldo_Cartera"] if c in m]
        plot(px.bar(m,x="Periodo",y=vals,barmode="group",title="Facturacion, pagos y cartera"))
    c1,c2=st.columns(2)
    if "Estado_Factura" in df:
        with c1: plot(px.pie(df,names="Estado_Factura",values="Valor_Neto" if "Valor_Neto" in df else None,title="Distribucion por estado"))
    if "Entidad_Pagadora" in df and "Valor_Neto" in df:
        top=aggregate(df,"Entidad_Pagadora").nlargest(10,"Valor_Neto")
        with c2: plot(px.bar(top,x="Valor_Neto",y="Entidad_Pagadora",orientation="h",title="Top entidades pagadoras"))


def show_monthly(df):
    st.subheader("Cierre mensual")
    m=monthly(df)
    if m.empty: st.info("Se necesita Periodo_Cierre o Fecha_Radicacion."); return
    st.dataframe(m,use_container_width=True,hide_index=True)
    if "Valor_Neto" in m:
        plot(px.line(m,x="Periodo",y=[c for c in ["Valor_Neto","Valor_Pagado","Saldo_Cartera","Promedio_Movil_3"] if c in m],markers=True,title="Evolucion del cierre"))
        hi=m.loc[m["Valor_Neto"].idxmax()]; lo=m.loc[m["Valor_Neto"].idxmin()]
        st.success(f"Mayor facturacion: {hi['Periodo']}. Menor facturacion: {lo['Periodo']}.")


def show_group(df, group, title):
    st.subheader(title)
    if group not in df: st.info(f"No se encontro la columna {group}."); return
    table=aggregate(df,group)
    sort="Valor_Neto" if "Valor_Neto" in table else table.columns[1]
    table=table.sort_values(sort,ascending=False)
    st.dataframe(table,use_container_width=True,hide_index=True)
    if "Valor_Neto" in table: plot(px.bar(table.head(15),x="Valor_Neto",y=group,orientation="h",title=f"Facturacion por {group.replace('_',' ').lower()}"))
    if all(c in table for c in ["Valor_Neto","Porcentaje_Recaudo","Saldo_Cartera"]):
        plot(px.scatter(table,x="Valor_Neto",y="Porcentaje_Recaudo",size="Saldo_Cartera",color="Porcentaje_Glosa" if "Porcentaje_Glosa" in table else None,hover_name=group,title="Volumen, recaudo y cartera"))
    if "Valor_Neto" in table:
        p=table[[group,"Valor_Neto"]].copy(); p["Participacion"]=p["Valor_Neto"]/p["Valor_Neto"].sum()*100; p["Acumulado"]=p["Participacion"].cumsum()
        fig=make_subplots(specs=[[{"secondary_y":True}]])
        fig.add_bar(x=p[group],y=p["Valor_Neto"],name="Valor")
        fig.add_scatter(x=p[group],y=p["Acumulado"],name="Acumulado %",secondary_y=True)
        fig.add_hline(y=80,line_dash="dash",line_color="#F4A261",secondary_y=True); fig.update_layout(title="Analisis de Pareto")
        plot(fig)


def show_states(df):
    st.subheader("Estados de facturacion")
    if "Estado_Factura" not in df: st.info("No se encontro Estado_Factura."); return
    t=aggregate(df,"Estado_Factura"); st.dataframe(t,use_container_width=True,hide_index=True)
    y="Valor_Neto" if "Valor_Neto" in t else "Facturas"; plot(px.bar(t,x="Estado_Factura",y=y,color="Estado_Factura",title="Distribucion por estado"))
    if "Periodo_Cierre" in df and "Valor_Neto" in df:
        p=df.groupby(["Periodo_Cierre","Estado_Factura"],dropna=False)["Valor_Neto"].sum().reset_index(); plot(px.bar(p,x="Periodo_Cierre",y="Valor_Neto",color="Estado_Factura",title="Estados por periodo"))


def show_glosas(df):
    st.subheader("Glosas")
    if "Glosa_Inicial" not in df: st.info("No se encontro Glosa_Inicial."); return
    positive=df[df["Glosa_Inicial"].fillna(0)>0]; net=df.get("Valor_Neto",pd.Series(dtype=float)).sum()
    a,b,c,d=st.columns(4); a.metric("Valor glosado",fmt_money(positive["Glosa_Inicial"].sum())); b.metric("Facturas con glosa",len(positive)); c.metric("Frecuencia",f"{len(positive)/max(1,len(df))*100:.1f}%"); d.metric("Severidad",f"{positive['Glosa_Inicial'].sum()/net*100:.1f}%" if net else "N/D")
    plot(px.histogram(positive,x="Glosa_Inicial",nbins=30,title="Distribucion de glosas"))
    if "Entidad_Pagadora" in df: show_group(positive,"Entidad_Pagadora","Ranking de glosa por entidad")


def show_cartera(df):
    st.subheader("Recaudo y cartera")
    if not all(c in df for c in ["Valor_Neto","Valor_Pagado","Saldo_Cartera"]): st.info("Se requieren Valor_Neto, Valor_Pagado y Saldo_Cartera."); return
    totals=df[["Valor_Neto","Valor_Pagado","Saldo_Cartera"]].sum(); plot(px.bar(x=totals.index,y=totals.values,labels={"x":"Concepto","y":"Valor"},title="Facturacion, pago y saldo"))
    if "Entidad_Pagadora" in df: show_group(df,"Entidad_Pagadora","Cartera por entidad")
    if "Fecha_Radicacion" in df:
        cutoff=st.date_input("Fecha de corte",date.today()); days=(pd.Timestamp(cutoff)-df["Fecha_Radicacion"]).dt.days
        temp=df.assign(Antiguedad=pd.cut(days,[-np.inf,30,60,90,180,np.inf],labels=["0 a 30","31 a 60","61 a 90","91 a 180","Mas de 180"]))
        plot(px.bar(temp.groupby("Antiguedad",observed=False)["Saldo_Cartera"].sum().reset_index(),x="Antiguedad",y="Saldo_Cartera",title="Antiguedad aproximada de cartera"))
        st.caption("Rangos analiticos configurables; no constituyen una politica contable o contractual universal.")


def show_times(df):
    st.subheader("Tiempos de radicacion")
    c="Dias_Emision_Radicacion"
    if c not in df or df[c].dropna().empty: st.info("No hay tiempos de radicacion calculables."); return
    s=df[c].dropna(); vals=[("Promedio",s.mean()),("Mediana",s.median()),("Desv. estandar",s.std()),("P90",s.quantile(.9)),("P95",s.quantile(.95))]
    cols=st.columns(5)
    for col,(label,val) in zip(cols,vals): col.metric(label,f"{val:.1f} dias")
    plot(px.histogram(df,x=c,nbins=40,title="Distribucion de tiempos")); plot(px.box(df,y=c,title="Casos extremos"))


def show_statistics(df):
    st.subheader("Analisis estadistico")
    nums=[c for c in df.select_dtypes(include=np.number).columns if df[c].notna().sum()>1]
    if not nums: st.info("No hay variables numericas suficientes."); return
    var=st.selectbox("Variable numerica",nums); s=df[var].dropna()
    desc={"Conteo":s.count(),"Media":s.mean(),"Mediana":s.median(),"Moda":s.mode().iloc[0] if not s.mode().empty else np.nan,"Desviacion":s.std(),"Varianza":s.var(),"Minimo":s.min(),"Maximo":s.max(),"Rango":s.max()-s.min(),"Q1":s.quantile(.25),"Q3":s.quantile(.75),"IQR":s.quantile(.75)-s.quantile(.25),"P90":s.quantile(.9),"P95":s.quantile(.95),"Coef. variacion":s.std()/abs(s.mean()) if s.mean()!=0 else np.nan,"Asimetria":s.skew(),"Curtosis":s.kurt()}
    st.dataframe(pd.DataFrame(desc.items(),columns=["Estadistico","Valor"]),use_container_width=True,hide_index=True)
    a,b=st.columns(2)
    with a: plot(px.histogram(df,x=var,nbins=40,marginal="rug",title=f"Distribucion de {var}"))
    with b: plot(px.box(df,y=var,title=f"Boxplot de {var}"))
    st.write(f"La media es {s.mean():,.2f}, la mediana {s.median():,.2f} y la asimetria {s.skew():.2f}. La interpretacion describe los valores calculados y no presupone normalidad.")
    st.markdown("#### Correlaciones")
    method=st.radio("Metodo",["pearson","spearman"],horizontal=True); corr=df[nums].corr(method=method)
    plot(px.imshow(corr,text_auto=".2f",aspect="auto",color_continuous_scale="RdBu_r",zmin=-1,zmax=1,title=f"Correlacion {method.title()}"))
    st.warning("La correlacion no implica causalidad. Algunas relaciones pueden surgir directamente de las formulas contables entre las variables.")
    with st.expander("Pruebas estadisticas"):
        group_cols=[c for c in df.select_dtypes(exclude=np.number).columns if 2<=df[c].nunique()<=20]
        if group_cols:
            group=st.selectbox("Agrupacion",group_cols); alpha=st.number_input("Significancia",.001,.20,.05,.01)
            samples=[g[var].dropna().values for _,g in df.groupby(group) if g[var].notna().sum()>=2]
            if len(samples)==2:
                statv,p=stats.mannwhitneyu(*samples,alternative="two-sided"); name="Mann-Whitney U"
            elif len(samples)>2:
                statv,p=stats.kruskal(*samples); name="Kruskal-Wallis"
            else: st.info("No existen suficientes grupos."); return
            st.write({"Prueba":name,"Hipotesis nula":"Las distribuciones de los grupos son equivalentes.","Estadistico":statv,"p-valor":p,"Significancia":alpha,"Decision":"Rechazar H0" if p<alpha else "No rechazar H0"})


def show_outliers(df):
    st.subheader("Valores atipicos")
    nums=[c for c in df.select_dtypes(include=np.number).columns if df[c].notna().sum()>3]
    if not nums: st.info("No hay variables numericas suficientes."); return
    var=st.selectbox("Variable",nums); method=st.radio("Metodo",["IQR","Z-score","Percentiles"],horizontal=True); s=df[var]
    if method=="IQR":
        mult=st.number_input("Multiplicador IQR",.5,5.0,1.5,.1); q1,q3=s.quantile([.25,.75]); iqr=q3-q1; lo,hi=q1-mult*iqr,q3+mult*iqr
    elif method=="Z-score":
        z=st.number_input("Umbral Z",1.0,6.0,3.0,.1); mean,std=s.mean(),s.std(); lo,hi=mean-z*std,mean+z*std
    else:
        p=st.slider("Percentiles",.1,10.0,1.0,.1)/100; lo,hi=s.quantile(p),s.quantile(1-p)
    mask=s.lt(lo)|s.gt(hi); out=df[mask]
    st.metric("Valores atipicos",len(out),f"{len(out)/max(1,s.notna().sum())*100:.1f}%"); st.write(f"Limites: {lo:,.2f} a {hi:,.2f}")
    st.dataframe(out,use_container_width=True); plot(px.box(df,y=var,points="outliers",title=f"Atipicos de {var}"))
    st.caption("Un valor atipico no es necesariamente un error; puede corresponder a una factura legitima de mayor complejidad o valor.")


def generate_insights(df):
    items=[]
    m=monthly(df)
    if not m.empty and "Valor_Neto" in m:
        r=m.loc[m["Valor_Neto"].idxmax()]; items.append(("Mayor facturacion",f"{r['Periodo']}: {fmt_money(r['Valor_Neto'])}","Revisar los componentes del periodo y su sostenibilidad."))
        if len(m)>1:
            last=m.iloc[-1]; prev=m.iloc[-2]; ch=pct(last["Valor_Neto"]-prev["Valor_Neto"],prev["Valor_Neto"])
            items.append(("Variacion reciente",f"{ch:.1f}% frente al periodo anterior","Revisar entidades y servicios que explican la variacion."))
    if "Entidad_Pagadora" in df and "Valor_Neto" in df:
        t=aggregate(df,"Entidad_Pagadora").sort_values("Valor_Neto",ascending=False); r=t.iloc[0]
        items.append(("Entidad con mayor facturacion",f"{r['Entidad_Pagadora']}: {fmt_money(r['Valor_Neto'])}","Evaluar concentracion y exposicion financiera."))
    if "Saldo_Cartera" in df and "Entidad_Pagadora" in df:
        t=aggregate(df,"Entidad_Pagadora").sort_values("Saldo_Cartera",ascending=False); r=t.iloc[0]
        items.append(("Mayor cartera",f"{r['Entidad_Pagadora']}: {fmt_money(r['Saldo_Cartera'])}","Priorizar conciliacion y seguimiento documental."))
    if "Soporte_Completo" in df:
        incomplete=~df["Soporte_Completo"].astype(str).str.strip().str.casefold().isin(["si","sí","true","1","completo"])
        items.append(("Soportes potencialmente incompletos",f"{incomplete.mean()*100:.1f}%","Validar definicion y revisar registros marcados."))
    return items


def show_insights(df):
    st.subheader("Insights y alertas")
    items=generate_insights(df)
    if not items: st.info("No hay datos suficientes para generar insights."); return
    for title,value,action in items:
        st.markdown(f"**Hallazgo calculado: {title}.** Los datos muestran **{value}**. Interpretacion: se observa un punto relevante para seguimiento. Recomendacion para investigar: {action} La informacion disponible no permite establecer la causa.")
    st.markdown("#### Semaforos configurables")
    cols=st.columns(3); thresholds={"Glosa roja %":cols[0].number_input("Glosa roja %",0.,100.,10.),"Cartera roja %":cols[1].number_input("Cartera roja %",0.,100.,30.),"Recaudo verde %":cols[2].number_input("Recaudo verde %",0.,100.,90.)}
    st.caption("Parametros demostrativos y editables; no representan estandares oficiales.")


def to_excel_bytes(sheets):
    output=io.BytesIO()
    with pd.ExcelWriter(output,engine="openpyxl") as writer:
        for name,frame in sheets.items(): frame.to_excel(writer,index=False,sheet_name=name[:31])
    return output.getvalue()


def show_explorer(df):
    st.subheader("Explorador de datos")
    text=st.text_input("Buscar texto"); cols=st.multiselect("Columnas",df.columns.tolist(),default=df.columns.tolist()[:min(15,len(df.columns))])
    view=df
    if text:
        mask=df.astype(str).apply(lambda c:c.str.contains(text,case=False,na=False)).any(axis=1); view=df[mask]
    mode=st.selectbox("Mostrar",["Todos","Con saldo","Con glosa","Soporte incompleto","Inconsistencias"])
    if mode=="Con saldo" and "Tiene_Saldo" in view: view=view[view["Tiene_Saldo"]]
    elif mode=="Con glosa" and "Tiene_Glosa" in view: view=view[view["Tiene_Glosa"]]
    elif mode=="Inconsistencias" and "Inconsistencia_Financiera" in view: view=view[view["Inconsistencia_Financiera"]]
    elif mode=="Soporte incompleto" and "Soporte_Completo" in view: view=view[~view["Soporte_Completo"].astype(str).str.casefold().isin(["si","sí","true","1","completo"])]
    n=st.slider("Filas",10,1000,min(100,max(10,len(view))))
    st.dataframe(view[cols].head(n) if cols else view.head(n),use_container_width=True,height=520)


def show_downloads(df):
    st.subheader("Descargas")
    m=monthly(df); entities=aggregate(df,"Entidad_Pagadora") if "Entidad_Pagadora" in df else pd.DataFrame(); services=aggregate(df,"Servicio") if "Servicio" in df else pd.DataFrame(); insights=pd.DataFrame(generate_insights(df),columns=["Hallazgo","Valor","Accion"])
    q,n,s,_=quality_report(df,st.session_state.get("tolerance",1.0))
    files={"facturacion_filtrada.xlsx":{"Datos":df},"cierre_mensual.xlsx":{"Cierre":m},"analisis_entidades.xlsx":{"Entidades":entities},"analisis_servicios.xlsx":{"Servicios":services},"informe_calidad.xlsx":{"Resumen":q,"Nulos":n}}
    for name,sheets in files.items():
        if all(not x.empty for x in sheets.values()): st.download_button(f"Descargar {name}",to_excel_bytes(sheets),name,mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
    st.download_button("Descargar datos filtrados CSV",df.to_csv(index=False).encode("utf-8-sig"),"facturacion_filtrada.csv","text/csv",use_container_width=True)
    st.download_button("Descargar insights",insights.to_csv(index=False).encode("utf-8-sig"),"insights_facturacion.csv","text/csv",use_container_width=True)


def show_methodology():
    st.subheader("Metodologia y transparencia")
    st.markdown("""
- **Facturacion neta:** valor reportado en `Valor_Neto`; cuando se valida la identidad, se contrasta con `Valor_Bruto - Descuento - Copago_Cuota`.
- **Porcentaje de glosa:** `Glosa_Inicial / Valor_Neto x 100`.
- **Porcentaje de recaudo:** `Valor_Pagado / Valor_Neto x 100`.
- **Porcentaje de cartera:** `Saldo_Cartera / Valor_Neto x 100`.
- **Ticket promedio:** `Valor_Neto / numero de facturas unicas`.
- **Correlacion:** intensidad y direccion de una asociacion, sin demostrar causalidad.
- **Valor atipico:** observacion alejada del patron; no implica por si sola un error.
- **IQR:** limites `Q1 - k x IQR` y `Q3 + k x IQR`.
- **p-valor:** compatibilidad de los datos con la hipotesis nula bajo los supuestos de la prueba. No rechazar H0 no demuestra que sea verdadera.

Los resultados dependen del mapeo, las conversiones, la completitud y la consistencia del archivo. La aplicacion no sustituye auditorias ni decisiones contractuales, contables o clinicas.
    """)


def mapping_ui(df):
    auto=detect_renames(df.columns); st.session_state["renames_auto"]=auto
    with st.expander("Configurar correspondencia de columnas",expanded=False):
        if auto: st.dataframe(pd.DataFrame(auto.items(),columns=["Columna original","Equivalencia detectada"]),hide_index=True,use_container_width=True)
        options=["Columna no disponible"]+df.columns.tolist(); mapping={}
        for target in EXPECTED:
            default=target if target in df.columns else next((k for k,v in auto.items() if v==target),"Columna no disponible")
            mapping[target]=st.selectbox(target.replace("_"," "),options,index=options.index(default) if default in options else 0,key="map_"+target)
        return mapping


def main():
    css(); header()
    if st.sidebar.button("Reiniciar aplicacion",use_container_width=True):
        st.session_state.clear(); st.rerun()
    currency=st.sidebar.selectbox("Etiqueta de moneda",["COP","USD","EUR","Sin simbolo"])
    tolerance=st.sidebar.number_input("Tolerancia de identidades",0.0,1000000.0,1.0,1.0); st.session_state["tolerance"]=tolerance
    uploaded=st.sidebar.file_uploader("Cargue el archivo de facturacion que desea analizar",type=["xlsx","xls","csv"])
    if uploaded is None:
        show_start(); return
    raw=uploaded.getvalue(); signature=(uploaded.name,len(raw))
    if st.session_state.get("signature")!=signature:
        for k in list(st.session_state):
            if k not in ["signature"]: del st.session_state[k]
        st.session_state["signature"]=signature
    try:
        if uploaded.name.lower().endswith(".csv"):
            sep=st.sidebar.selectbox("Separador CSV",["automatico","coma","punto y coma","tabulacion"])
            df,enc,used=read_csv_bytes(raw,sep); sheet=f"CSV ({enc})"
        else:
            sheets=excel_sheets(raw); default=sheets.index("Facturacion") if "Facturacion" in sheets else 0
            sheet=st.sidebar.selectbox("Hoja",sheets,index=default); df=read_excel_bytes(raw,sheet)
    except Exception as exc:
        st.error(f"No fue posible leer el archivo. {exc}"); return
    if df.empty: st.error("La hoja seleccionada no contiene datos."); return
    df.columns=unique_columns([str(c).strip() for c in df.columns])
    mapping=mapping_ui(df); rename={source:target for target,source in mapping.items() if source!="Columna no disponible" and source in df.columns}
    if len(rename.values())!=len(set(rename.values())): st.error("El mapeo contiene destinos duplicados."); return
    working=df.rename(columns=rename)
    with st.sidebar.expander("Limpieza controlada",expanded=False):
        remove_empty=st.checkbox("Eliminar filas completamente vacias",True); remove_dupes=st.checkbox("Eliminar duplicados exactos",False); fill_cat=st.checkbox("Completar categorias vacias",False); exclude_net=st.checkbox("Excluir Valor_Neto invalido",False); exclude_dates=st.checkbox("Excluir fechas invalidas",False); apply_clean=st.checkbox("Aplicar transformaciones",True)
    converted,log=convert_types(working)
    if apply_clean:
        clean=converted.copy(); before=len(clean)
        if remove_empty: clean=clean.dropna(how="all")
        if remove_dupes: clean=clean.drop_duplicates()
        if fill_cat:
            cats=[c for c in clean.select_dtypes(include="object").columns if c not in ["ID_Factura","Numero_Radicado"]]; clean[cats]=clean[cats].fillna("Sin informacion")
        if exclude_net and "Valor_Neto" in clean: clean=clean[clean["Valor_Neto"].notna()]
        if exclude_dates:
            datecols=[c for c in DATES if c in clean]
            if datecols: clean=clean[clean[datecols].notna().all(axis=1)]
        st.sidebar.caption(f"Registros iniciales: {before}; posteriores: {len(clean)}; excluidos: {before-len(clean)}")
    else: clean=working.copy(); log=pd.DataFrame()
    clean=derive(clean); clean=financial_identity_flags(clean,tolerance)
    missing_min=[c for c in MINIMUM if c not in clean] + ([] if ("Fecha_Radicacion" in clean or "Periodo_Cierre" in clean) else ["Fecha_Radicacion o Periodo_Cierre"])
    missing_rec=[c for c in RECOMMENDED if c not in clean]
    if missing_min:
        st.error("Faltan columnas minimas: "+", ".join(missing_min)+". Use el asistente de mapeo o ajuste los encabezados.")
        st.write("Columnas encontradas:",list(clean.columns)); show_start(clean,{"name":uploaded.name}); return
    if missing_rec: st.warning("Columnas recomendadas ausentes: "+", ".join(missing_rec)+". Los modulos dependientes se desactivaran.")
    filtered=sidebar_filters(clean)
    menu=st.sidebar.radio("Navegacion",["Inicio y carga de datos","Calidad de datos","Resumen ejecutivo","Cierre mensual","Entidades pagadoras","Servicios y lineas","Sedes y regimenes","Estados de facturacion","Glosas","Recaudo y cartera","Tiempos de radicacion","Analisis estadistico","Valores atipicos","Insights y alertas","Explorador de datos","Descargas","Metodologia"])
    if filtered.empty and menu not in ["Inicio y carga de datos","Calidad de datos","Metodologia"]: st.warning("Los filtros actuales no tienen registros."); return
    actions={
        "Inicio y carga de datos":lambda:show_start(clean,{"name":uploaded.name,"sheet":sheet}),
        "Calidad de datos":lambda:show_quality(clean,tolerance,log),
        "Resumen ejecutivo":lambda:show_summary(filtered,currency),
        "Cierre mensual":lambda:show_monthly(filtered),
        "Entidades pagadoras":lambda:show_group(filtered,"Entidad_Pagadora","Entidades pagadoras"),
        "Servicios y lineas":lambda:show_group(filtered,"Servicio","Servicios y lineas de servicio"),
        "Sedes y regimenes":lambda:show_group(filtered,"Sede","Sedes y regimenes"),
        "Estados de facturacion":lambda:show_states(filtered),
        "Glosas":lambda:show_glosas(filtered),
        "Recaudo y cartera":lambda:show_cartera(filtered),
        "Tiempos de radicacion":lambda:show_times(filtered),
        "Analisis estadistico":lambda:show_statistics(filtered),
        "Valores atipicos":lambda:show_outliers(filtered),
        "Insights y alertas":lambda:show_insights(filtered),
        "Explorador de datos":lambda:show_explorer(filtered),
        "Descargas":lambda:show_downloads(filtered),
        "Metodologia":show_methodology}
    try: actions[menu]()
    except Exception as exc: st.error(f"No fue posible completar este modulo. Revise la calidad y el mapeo de los datos. Detalle: {exc}")

if __name__ == "__main__":
    main()
