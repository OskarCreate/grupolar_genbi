# Grupo Lar — Build Your Own Generative BI

Adaptación del laboratorio **NEXA Retail — Build Your Own Generative BI** al Data Mart de **Grupo Lar** (transferencias internas de recursos entre almacenes y obras).

El código base es el del docente. Lo que cambia es todo lo que depende del negocio: la GenBI View, el contexto, la Semantic Layer, las Golden Queries y la app.

```text
grupolar_master (fact_resource_trans + 5 dimensiones)   ← ya lo tienes en Athena
        ↓
vw_grupolar_genbi_transferencias (GenBI View)            ← Paso 1
        ↓
dataset_profile.json → semantic_layer_draft.json         ← Pasos 6 y 7 (Bedrock)
        ↓
Validación humana → semantic_layer.json (aprobada)       ← Paso 8
        ↓
NL-to-SQL → SQL Guard → Athena → Insight + Visualización ← Pasos 9 a 13
```

> **Bedrock interpreta. La Semantic Layer gobierna. Athena calcula.**

---

## Qué ya tienes en AWS (no se repite)

| Recurso | Estado |
|---|---|
| S3 `sql-event-s3` con `raw/`, `master/` y `athena-results/` | Hecho |
| Athena `grupolar_raw` (tablas externas y vistas) | Hecho |
| Athena `grupolar_master`: `fact_resource_trans`, `dim_cuenta_contable`, `dim_recursos`, `dim_sede`, `dim_fecha`, `dim_usuario` | Hecho |
| Región `us-east-1` | Hecho |

Lo nuevo es: la **GenBI View**, **Amazon Bedrock** y la **aplicación Python/Streamlit** en tu PC.

---

## Paso 1 — Crear la GenBI View en Athena

En el editor de Athena ejecuta el contenido de `sql/01_create_genbi_view.sql`.

Crea `grupolar_master.vw_grupolar_genbi_transferencias`: une la fact con sus 5 dimensiones y expone solo lo que GenBI necesita, con nombres de negocio. `monto_total` se calcula en la vista (Debe − Haber), no se guarda en la fact.

Después ejecuta **una por una** las consultas de `sql/02_validar_genbi_view.sql`. Resultados esperados:

| Consulta | Esperado |
|---|---|
| V1 filas fact / vista / transferencias / comprobantes | 874 / 874 / 874 / 332 |
| V2 valor transferido / haber / monto total | 2,348,538.23 / 217,972.76 / 2,130,565.47 |
| V5 líneas por comprobante | 1→67, 2→81, 3→91, 4→93 |
| V6 unidades de medida | 11 distintas |

V5 y V6 son la evidencia de dos reglas de negocio que la Semantic Layer tiene que gobernar (ver Paso 8).

---

## Paso 2 — Verificar Amazon Bedrock

1. En la consola, región **us-east-1**, abre **Amazon Bedrock**.
2. En el catálogo de modelos busca **Amazon Nova Micro** y pruébalo en el *Playground* con cualquier pregunta.
3. Si te pide habilitar el acceso al modelo, habilítalo. En una cuenta de organización (tu cuenta es `POC-CLOUD-OPE-01`) puede que un administrador tenga que permitirlo.

El modelo configurado es `us.amazon.nova-micro-v1:0` (perfil de inferencia de EE. UU.). Si da `ValidationException` por el ID, prueba con `amazon.nova-micro-v1:0`.

---

## Paso 3 — Credenciales de AWS en tu PC

La aplicación corre en tu computadora y llama a Athena y Bedrock con tus credenciales.

1. Instala **AWS CLI v2**.
2. Configura tus credenciales:
   - Con access keys de IAM: `aws configure` (región `us-east-1`, formato `json`).
   - Si tu organización usa IAM Identity Center (SSO): `aws configure sso`.
3. Comprueba:

```bash
aws sts get-caller-identity
```

Tu usuario o rol necesita permisos para:

- **Athena:** `StartQueryExecution`, `GetQueryExecution`, `GetQueryResults`.
- **Glue Data Catalog:** leer la base `grupolar_master` y sus tablas y vistas.
- **S3:** leer `sql-event-s3/master/` y escribir `sql-event-s3/athena-results/`.
- **Bedrock:** `InvokeModel` (la app usa la API `Converse`).

---

## Paso 4 — Entorno Python

Necesitas Python 3.10 o superior (recomendado 3.11). Desde la carpeta del proyecto:

```bash
python -m venv .venv
```

Activar en **Windows PowerShell**:

```powershell
.\.venv\Scripts\Activate.ps1
```

Activar en macOS/Linux:

```bash
source .venv/bin/activate
```

Instalar dependencias y verificar Bedrock:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
python -c "import boto3; print(boto3.__version__); print('bedrock-runtime' in boto3.Session().get_available_services())"
```

El último valor debe ser `True`.

---

## Paso 5 — Configurar el proyecto

Copia `config/settings.example.json` como `config/settings.json`. Ya viene con tus valores:

```json
{
  "aws_region": "us-east-1",
  "athena_database": "grupolar_master",
  "allowed_view": "vw_grupolar_genbi_transferencias",
  "athena_output_s3": "s3://sql-event-s3/athena-results/",
  "athena_workgroup": "primary",
  "bedrock_model_id": "us.amazon.nova-micro-v1:0"
}
```

`settings.json` no se sube a Git (está en `.gitignore`).

### Cómo ejecutar los scripts

Siempre desde la **raíz del proyecto**, nunca desde `scripts/`.

macOS/Linux:

```bash
PYTHONPATH=. python scripts/01_profile.py
```

Windows PowerShell (una vez por terminal, y luego cada script):

```powershell
$env:PYTHONPATH = "."
python scripts/01_profile.py
```

---

## Paso 6 — Fase 1: Technical Profiling

```bash
python scripts/01_profile.py
```

Crea `config/dataset_profile.json`: columnas, tipos, grano y filas de ejemplo de la GenBI View. Es evidencia técnica, todavía no define métricas de negocio.

---

## Paso 7 — Fase 2: Semantic Discovery con Bedrock

```bash
python scripts/02_build_semantic_draft.py
```

Crea `config/semantic_layer_draft.json`: lo que **Bedrock propone** (dimensiones, medidas, sinónimos, ambigüedades y preguntas a validar).

**Guarda este archivo tal como sale.** Es un entregable y la base de la validación humana.

---

## Paso 8 — Fase 3: Validación humana

El borrador de Bedrock **no se usa directamente**. La Semantic Layer aprobada ya está en `config/semantic_layer.json`. Tu trabajo es:

1. Abrir `config/semantic_layer_draft.json` junto a `config/semantic_layer.json`.
2. Completar `docs/validacion_humana.md`: para cada propuesta de Bedrock, si fue **aceptada**, **corregida** o **rechazada**, y por qué.
3. Si Bedrock propuso algo útil que no está en la capa aprobada (un sinónimo, una dimensión), agrégalo a `semantic_layer.json`.

Decisiones clave de Grupo Lar, con su evidencia:

| Concepto | Error típico de una IA | Definición aprobada | Evidencia |
|---|---|---|---|
| N.º de comprobantes | `COUNT(num_comprobante)` | `COUNT(DISTINCT num_comprobante)` | 874 líneas, pero 332 comprobantes |
| Cantidad transferida | Sumarla entre todos los recursos | Solo dentro de un recurso o unidad de medida | 11 unidades distintas (bolsas, m³, kg…) |
| Costo unitario promedio | `AVG(precio)` | `SUM(monto_debe) / SUM(cantidad_recursos)` | Cemento: 27.76 con AVG vs. 28.27 ponderado |
| Monto Total | Columna física o Debe + Haber | `SUM(monto_total)` = Debe − Haber | 2,130,565.47 |
| Monto Haber | Gasto o salida | Reversiones (devoluciones/anulaciones) | 9.28 % del Debe |
| Sede | Una sola sede | Dos roles: origen (envía) y destino (recibe) | Dimensión de rol |

Contenido de la capa aprobada frente al mínimo pedido:

| Requisito mínimo | Grupo Lar |
|---|---|
| 5 dimensiones | 15 |
| 4 métricas | 10 |
| 5 sinónimos | 81 (49 de métricas y 32 de dimensiones) |
| 5 reglas de negocio | 10 |
| 3 ambigüedades | 7 |

---

## Paso 9 — Fase 4: Probar NL-to-SQL

```bash
python scripts/03_test_nl2sql.py
```

Prueba, por ejemplo:

```text
¿Qué cuentas contables concentran los mayores montos de transferencia?
```

Esperado:

```text
Interpretation: "monto" → Monto Total neto
SQL Guard: PASSED
```

---

## Paso 10 — Fase 5: Ejecutar contra Athena

```bash
python scripts/04_execute_genbi_query.py
```

Prueba: `¿Cuál fue el porcentaje revertido?` → `9.28` aproximadamente.

---

## Paso 11 — Fase 6: Golden Queries

```bash
python scripts/05_validate_reference.py
```

`config/reference_queries.json` tiene **13 golden queries** con SQL de referencia validado manualmente y su `expected_value`. El script compara el **resultado** del SQL generado contra el de referencia (no compara el texto del SQL).

| ID | Pregunta | Esperado |
|---|---|---|
| GQ01 | ¿cuántas transferencias se registraron? | 874 |
| GQ02 | ¿cuántos comprobantes de transferencia se emitieron? | 332 |
| GQ03 | ¿cuál fue el valor transferido total? | 2,348,538.23 |
| GQ04 | ¿cuál fue el monto total neto? | 2,130,565.47 |
| GQ05 | ¿cuál fue el monto haber total? | 217,972.76 |
| GQ06 | ¿cuál fue el porcentaje revertido? | 9.2812 |
| GQ07 | ¿cuál fue el valor promedio por comprobante? | 7,073.91 |
| GQ08 | ¿cuántas transferencias se registraron en agosto de 2025? | 99 |
| GQ09 | ¿cuál fue el valor transferido hacia la Obra 02 - Surquillo? | 449,970.58 |
| GQ10 | ¿cuántas transferencias registró el usuario LCASTRO? | 160 |
| GQ11 | ¿cuál fue el monto total neto de la cuenta 24111? | 879,179.42 |
| GQ12 | ¿cuál fue el costo unitario promedio del Cemento Portland…? | 28.2723 |
| GQ13 | ¿cuántos comprobantes registró HUERT en diciembre de 2025? | 5 |

Si alguna falla, **no cambies el SQL de referencia**. Revisa el SQL generado y corrige la Semantic Layer: un sinónimo que falta, una regla poco clara o un valor exacto de dimensión. Luego vuelve a ejecutar. Guarda la salida final como evidencia.

> 100 % en esta batería significa que estas 13 preguntas responden bien, no que cualquier pregunta posible lo haga.

---

## Paso 12 — Fase 7: Insight + Visualización

```bash
python scripts/06_genbi_result.py
```

Pruebas sugeridas:

| Pregunta | Gráfico esperado |
|---|---|
| ¿Cómo evolucionó el valor transferido por mes? | Línea |
| ¿Qué cuentas contables concentran el mayor monto total? | Barras |
| ¿Cuál fue el porcentaje revertido? | KPI |

---

## Paso 13 — Fase 8: Aplicación Streamlit

```bash
streamlit run app.py
```

Abre `http://localhost:8501`. La app muestra **Pregunta, Interpretación, Insight, Visualización y Resultado**. Con "Mostrar detalles técnicos" muestra la regla semántica aplicada, el SQL generado, el SQL Guard y los metadatos de Athena.

Preguntas de negocio del proyecto:

```text
¿Qué sedes reciben la mayor cantidad de recursos?
¿Qué cuentas contables concentran los mayores montos de transferencia?
¿Cuáles son los recursos de mayor rotación entre obras?
¿Quiénes son los usuarios que registran las transacciones?
¿En qué mes hay mayor transacción de recursos entre las sedes?
```

Preguntas de ambigüedad (para la demo):

```text
¿Cuál fue la principal obra?          → "principal" se mide por valor transferido
¿Qué recursos tuvieron más movimiento? → "movimiento" se mide por número de transferencias
¿Qué sede recibe más recursos?          → "recursos" se mide por valor (la cantidad mezcla unidades)
```

---

## Cambios respecto al código del docente

| Archivo | Cambio | Por qué |
|---|---|---|
| `sql/01_create_genbi_view.sql` | Vista de Grupo Lar | Contrato propio del Data Mart |
| `sql/02_validar_genbi_view.sql` | Nuevo | Evidencia de que la vista no pierde ni duplica datos |
| `config/*.json` | Contexto, Semantic Layer y 13 golden queries de Grupo Lar | No se copia la de NEXA |
| `src/visualization.py` | Detecta tiempo en español (`periodo_mes`, `anio`, `mes`, `trimestre`), no trata códigos como métricas, una línea por categoría | El original solo detectaba `date/month/year` |
| `src/sql_guard.py` | Permite `EXTRACT(... FROM columna)` | El original lo confundía con una tabla y bloqueaba SQL válido |
| `src/sql_generator.py` | Reglas de Athena, sin CTE, valores exactos | El SQL Guard solo acepta `SELECT` |
| `scripts/05_validate_reference.py` | Una golden query que falla no detiene las demás; resumen por ID | Para medir la batería completa |
| `app.py` | Marca Grupo Lar, interpretación siempre visible, KPI con formato S/ y % | Lo pide el entregable |
| `tests/test_sql_guard.py` | 11 pruebas con la vista de Grupo Lar | Gobierno del SQL |
| `.gitignore` | Ya no ignora el perfil, el borrador ni la capa aprobada | Son entregables |

Pruebas locales del SQL Guard:

```bash
python -m unittest tests.test_sql_guard -v
```

---

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `Missing config/settings.json` | Copia `settings.example.json` como `settings.json`. |
| `ModuleNotFoundError: No module named 'src'` | No definiste `PYTHONPATH` o ejecutaste desde `scripts/`. |
| `AccessDeniedException` en Bedrock | Falta acceso al modelo o el permiso `bedrock:InvokeModel`. |
| `ValidationException` con el model ID | Cambia a `amazon.nova-micro-v1:0` o revisa la región. |
| Athena: `Table ... does not exist` | No creaste la vista o está en otra base: debe estar en `grupolar_master`. |
| Athena: `output location` | Revisa `athena_output_s3` y el permiso de escritura en S3. |
| `SQL Guard bloqueó la consulta` | Es lo esperado si el LLM intenta otra tabla, `SELECT *` o `WITH`. Reformula la pregunta o agrega una regla. |
| Golden query falla | Mira el SQL generado; ajusta sinónimos, reglas o valores en `semantic_layer.json`. |

---

## Nota sobre los datos

El plan de cuentas es real (CONCAR). Las transferencias, recursos y sedes son simulados con fines académicos, porque las tablas de movimientos de RSFACCAR y RSFACINM estaban vacías. Esto está declarado en `business_context.json` y en la Semantic Layer, para que los insights no lo oculten.
