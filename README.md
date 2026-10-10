# Analítica de Facturación en Salud

Aplicación web desarrollada con **Streamlit** para cargar, validar y analizar archivos de facturación en salud. Incluye indicadores de facturación, radicación, glosas, recaudo, cartera, calidad de datos y análisis estadístico.

> **Importante:** la herramienta facilita el análisis exploratorio. No reemplaza una auditoría financiera, contable, médica, contractual ni de protección de datos.

## Funcionalidades

- Carga de archivos `CSV`, `XLSX` y `XLS`.
- Selección de hoja para libros de Excel.
- Detección de separador y codificación en archivos CSV.
- Asistente para mapear encabezados del archivo a las columnas esperadas.
- Conversión controlada de fechas, valores monetarios y variables numéricas.
- Validación de duplicados, nulos, fechas inconsistentes y valores financieros atípicos.
- Cálculo de variables derivadas, porcentajes y tiempos de radicación.
- Filtros globales por fecha, entidad, régimen, sede, servicio, estado y otros campos.
- Resumen ejecutivo con indicadores y gráficos interactivos.
- Análisis por periodo, entidad pagadora, servicio, sede, régimen y estado.
- Módulos de glosas, recaudo, cartera y antigüedad aproximada.
- Estadística descriptiva, correlaciones y pruebas no paramétricas.
- Detección configurable de valores atípicos mediante IQR, Z-score o percentiles.
- Generación de hallazgos calculados y alertas exploratorias.
- Explorador de registros con búsqueda y filtros.
- Descarga de resultados en Excel y CSV.

## Requisitos

- Python 3.10 o superior recomendado.
- Las dependencias enumeradas en `requirements.txt`.

## Instalación local

### 1. Clonar o descargar el proyecto

```bash
git clone <URL_DEL_REPOSITORIO>
cd <NOMBRE_DEL_REPOSITORIO>
```

También puedes descargar los archivos `app.py` y `requirements.txt` y guardarlos en una misma carpeta.

### 2. Crear un entorno virtual

En Linux o macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

En Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Ejecutar la aplicación

```bash
streamlit run app.py
```

Streamlit mostrará la dirección local de la aplicación, normalmente:

```text
http://localhost:8501
```

## Uso

1. Abre la aplicación en el navegador.
2. Carga un archivo de facturación en formato CSV, XLSX o XLS.
3. Si es un libro de Excel, selecciona la hoja correspondiente.
4. Revisa el mapeo de columnas y ajusta las equivalencias cuando sea necesario.
5. Configura las opciones de limpieza y la tolerancia de las identidades financieras.
6. Aplica los filtros globales desde la barra lateral.
7. Navega por los módulos de análisis.
8. Descarga los resultados desde la sección **Descargas**.

## Estructura mínima de los datos

La aplicación requiere las siguientes columnas lógicas, aunque los encabezados originales pueden mapearse desde la interfaz:

- `ID_Factura`
- `Valor_Neto`
- Al menos una de estas columnas:
  - `Fecha_Radicacion`
  - `Periodo_Cierre`

### Columnas recomendadas

Para habilitar una mayor cantidad de módulos se recomienda incluir:

- `Entidad_Pagadora`
- `Estado_Factura`
- `Valor_Pagado`
- `Saldo_Cartera`
- `Glosa_Inicial`

### Estructura ampliada compatible

```text
ID_Factura
Numero_Radicado
Fecha_Servicio
Fecha_Emision
Fecha_Radicacion
Fecha_Aceptacion
Fecha_Pago
Periodo_Cierre
Codigo_Entidad
Entidad_Pagadora
Regimen
Sede
Codigo_Servicio
Servicio
Linea_Servicio
Cantidad
Canal_Radicacion
Estado_Factura
Dias_Emision_Radicacion
Soporte_Completo
Valor_Bruto
Descuento
Copago_Cuota
Valor_Neto
Glosa_Inicial
Valor_Pagado
Saldo_Cartera
```

## Formatos y consideraciones

### Fechas

La aplicación intenta convertir las columnas de fecha utilizando interpretación de día primero. Se recomienda usar formatos consistentes, por ejemplo:

```text
31/12/2026
2026-12-31
```

### Valores monetarios

El cargador admite valores numéricos y representaciones habituales con coma o punto como separador decimal o de miles. Para reducir ambigüedades, utiliza un único formato en todo el archivo.

Ejemplos:

```text
1250000
1.250.000
1,250,000
1250000,50
```

La etiqueta de moneda que aparece en los indicadores es configurable. La aplicación no realiza conversión entre monedas.

### Periodo de cierre

Se recomienda representar `Periodo_Cierre` con el formato:

```text
AAAA-MM
```

Ejemplo:

```text
2026-10
```

## Cálculos principales

La aplicación utiliza, cuando están disponibles, las siguientes relaciones:

```text
Valor_Neto = Valor_Bruto - Descuento - Copago_Cuota
Saldo_Cartera = Valor_Neto - Glosa_Inicial - Valor_Pagado
Porcentaje_Glosa = Glosa_Inicial / Valor_Neto * 100
Porcentaje_Recaudo = Valor_Pagado / Valor_Neto * 100
Porcentaje_Cartera = Saldo_Cartera / Valor_Neto * 100
Ticket_Promedio = Valor_Neto / Facturas_Unicas
```

La tolerancia para identificar diferencias en las identidades financieras puede configurarse desde la barra lateral.

## Módulos disponibles

- Inicio y carga de datos
- Calidad de datos
- Resumen ejecutivo
- Cierre mensual
- Entidades pagadoras
- Servicios y líneas
- Sedes y regímenes
- Estados de facturación
- Glosas
- Recaudo y cartera
- Tiempos de radicación
- Análisis estadístico
- Valores atípicos
- Insights y alertas
- Explorador de datos
- Descargas
- Metodología

## Despliegue en Streamlit Community Cloud

1. Crea un repositorio en GitHub.
2. Agrega en la raíz del repositorio:

```text
app.py
requirements.txt
README.md
```

3. Publica los cambios en la rama que usarás para el despliegue.
4. En Streamlit Community Cloud, crea una aplicación nueva.
5. Selecciona el repositorio, la rama y `app.py` como archivo principal.
6. Inicia el despliegue.

No es necesario incluir archivos de facturación en el repositorio. Cada usuario puede cargar su archivo durante la sesión.

## Estructura del proyecto

```text
.
├── app.py
├── requirements.txt
└── README.md
```

## Dependencias principales

- Streamlit
- pandas
- NumPy
- Plotly
- SciPy
- openpyxl
- xlrd

Consulta `requirements.txt` para ver la lista utilizada por el proyecto.

## Privacidad y seguridad de la información

Esta aplicación procesa los archivos cargados durante la sesión. Antes de utilizarla:

- Elimina nombres de pacientes, documentos de identidad e información clínica innecesaria.
- Usa datos anonimizados o seudonimizados.
- No publiques archivos reales de facturación en repositorios de código.
- Revisa las políticas de seguridad, privacidad, retención y tratamiento de datos de tu organización.
- Controla el acceso al despliegue si se utilizarán datos internos o confidenciales.

## Solución de problemas

### El archivo no se puede leer

- Comprueba que sea CSV, XLSX o XLS.
- En CSV, prueba otro separador desde la barra lateral.
- Verifica que la primera fila contenga los encabezados.
- En Excel, selecciona la hoja correcta.

### Faltan columnas mínimas

Abre **Configurar correspondencia de columnas** y asigna las columnas originales a `ID_Factura`, `Valor_Neto` y `Fecha_Radicacion` o `Periodo_Cierre`.

### Los valores monetarios se interpretan incorrectamente

Uniforma los separadores decimales y de miles en el archivo original. Evita mezclar formatos monetarios dentro de una misma columna.

### Algunos módulos no aparecen completos

Los módulos se adaptan a las columnas disponibles. Revisa la advertencia sobre columnas recomendadas y el diagnóstico de calidad.

### El despliegue falla por una dependencia

Vuelve a instalar localmente las dependencias y revisa los registros del despliegue:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Limitaciones

- La calidad de los resultados depende de la estructura, completitud y consistencia del archivo cargado.
- Los rangos de cartera, semáforos y umbrales estadísticos son configurables y no representan estándares oficiales.
- Las correlaciones no implican causalidad.
- Un valor atípico no es necesariamente un error.
- La aplicación no sustituye validaciones contables, contractuales, clínicas, legales o regulatorias.

## Licencia

No se ha definido una licencia para este proyecto. Antes de distribuirlo o permitir modificaciones, agrega un archivo `LICENSE` con las condiciones aplicables.
