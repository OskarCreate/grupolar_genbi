# Validación humana de la Semantic Layer — Grupo Lar

**Entrada:** `config/semantic_layer_draft.json` (propuesta de Amazon Bedrock).
**Salida:** `config/semantic_layer.json` (capa aprobada).

> AI can discover structure. Business governs meaning.

Este documento tiene dos partes:

- **Parte A:** las decisiones de negocio que gobiernan la capa aprobada, cada una con su evidencia en Athena. Ya está completa.
- **Parte B:** la comparación con **lo que propuso tu borrador real**. Se completa después de ejecutar `scripts/02_build_semantic_draft.py`, porque cada ejecución de Bedrock puede proponer cosas distintas.

---

## Parte A — Decisiones de negocio con evidencia

Las cifras salen de `sql/02_validar_genbi_view.sql` y de las golden queries.

### A1. El grano: una fila no es un comprobante

- **Evidencia:** la vista tiene 874 líneas pero 332 comprobantes; un comprobante tiene de 1 a 4 líneas (consulta V5).
- **Consecuencia:** `COUNT(num_comprobante)` devuelve 874 y está **mal**.
- **Definición aprobada:** N.º de comprobantes = `COUNT(DISTINCT num_comprobante)` → 332. N.º de transferencias = `COUNT(DISTINCT transaccion_id)` → 874.

### A2. La cantidad mezcla unidades de medida

- **Evidencia:** `cantidad_recursos` está en 11 unidades distintas: UND, KG, GL, M3, BOL, ROL, VAR, M2, BAL, MIL y PAR (consulta V6).
- **Consecuencia:** sumar bolsas de cemento con metros cúbicos de arena da un número sin significado de negocio.
- **Definición aprobada:** Cantidad transferida = `SUM(cantidad_recursos)`, pero solo se compara dentro de un mismo recurso o unidad de medida (regla de negocio 4). Cuando una pregunta dice "más recursos" sin métrica, se mide por **valor transferido** (ambigüedad `recursos`).

### A3. Precio promedio: una agregación válida no es una métrica válida

- **Evidencia:** para el Cemento Portland, `AVG(monto_debe / cantidad_recursos)` da **27.76**; el costo ponderado `SUM(monto_debe) / SUM(cantidad_recursos)` da **28.27** (GQ12).
- **Definición aprobada:** Costo unitario promedio = `SUM(monto_debe) / NULLIF(SUM(cantidad_recursos), 0)`, siempre por recurso.

### A4. Monto Total, Debe y Haber

- **Evidencia:** Debe 2,348,538.23; Haber 217,972.76; Total 2,130,565.47 (consulta V2).
- **Definiciones aprobadas:**
  - Valor transferido = `SUM(monto_debe)`.
  - Monto Haber = `SUM(monto_haber)`: representa **reversiones** (devoluciones o anulaciones), no gastos ni transferencias nuevas.
  - Monto Total neto = `SUM(monto_total)`, donde `monto_total = monto_debe − monto_haber` se calcula en la vista y no se almacena en la fact.
  - % revertido = `SUM(monto_haber) * 100 / NULLIF(SUM(monto_debe), 0)` → 9.28 %.

### A5. La sede tiene dos roles

- **Evidencia:** la fact se une dos veces con `dim_sede` (origen y destino).
- **Definición aprobada:** "envía / transfiere / sale de" → `sede_origen`; "recibe / llega a / hacia" → `sede_destino`. Si la pregunta no indica el rol, se usa `sede_destino`.

### A6. Ambigüedades del lenguaje del negocio

| Término | Puede significar | Regla aprobada |
|---|---|---|
| transacción | línea o comprobante | N.º de transferencias |
| movimiento | transferencias, valor o cantidad | N.º de transferencias |
| monto | Debe, Haber o neto | Monto Total neto |
| mejor / principal | cualquier métrica | Valor transferido |
| recursos ("más recursos") | cantidad, valor o transferencias | Valor transferido (la cantidad mezcla unidades) |
| sede | origen o destino | Sede de destino |

### A7. Contexto de negocio

- Moneda **PEN (S/)**, configuración regional `es-PE`; no se convierte a otra moneda.
- Periodo cubierto: enero a diciembre de 2025.
- Plan de cuentas real (CONCAR); transferencias, recursos y sedes simulados. El insight no debe presentarlos como datos reales de operación.

---

## Parte B — Comparación con el borrador de Bedrock

**Instrucciones:**

1. Abre `config/semantic_layer_draft.json`.
2. Por cada dimensión, medida, sinónimo y ambigüedad que propuso Bedrock, agrega una fila.
3. Decide: **Aceptado** (pasa igual), **Corregido** (pasa con otra definición) o **Rechazado** (no pasa).
4. Escribe el porqué con evidencia de la Parte A cuando aplique.
5. Borra las filas de ejemplo que no correspondan a tu borrador.

### Qué revisar en el borrador

- [ ] ¿Propone sumar `cantidad_recursos` entre todos los recursos? → **Corregido** (A2).
- [ ] ¿Cuenta comprobantes con `COUNT(num_comprobante)` o `COUNT(*)`? → **Corregido** (A1).
- [ ] ¿Propone `AVG` de un precio o costo por fila? → **Rechazado o corregido** (A3).
- [ ] ¿Trata `monto_haber` como gasto, salida o negativo? → **Corregido** (A4).
- [ ] ¿Propone sumar `anio`, `mes`, `dia`, `trimestre` o `codigo_cuenta`? → **Rechazado**: son dimensiones, no medidas.
- [ ] ¿Distingue `sede_origen` de `sede_destino`? Si las trata como una sola → **Corregido** (A5).
- [ ] ¿Usa dólares o cambia de moneda? → **Rechazado** (A7).
- [ ] ¿Detectó el grano y los campos no aditivos (`non_additive_fields`)? → **Aceptado** si coincide con A1.
- [ ] ¿Qué `validation_questions` dejó abiertas? Respóndelas en la tabla.

### Tabla de decisiones

Las filas son ejemplos del formato; reemplázalas con lo que propuso tu borrador.

| # | Propuesta de Bedrock (copiar del borrador) | Decisión | Versión aprobada | Por qué |
|---|---|---|---|---|
| 1 | Medida "Total Debit" = `SUM(monto_debe)` | Aceptado | `valor_transferido` = `SUM(monto_debe)` | Coincide con la definición de negocio; solo se renombra |
| 2 | Medida "Vouchers" = `COUNT(num_comprobante)` | Corregido | `COUNT(DISTINCT num_comprobante)` | Grano: 874 líneas vs. 332 comprobantes (A1) |
| 3 | Medida "Total Quantity" = `SUM(cantidad_recursos)` | Corregido | Igual, pero solo por recurso o unidad | Mezcla 11 unidades de medida (A2) |
| 4 | Medida "Average Unit Cost" = `AVG(...)` | Corregido | `SUM(monto_debe) / SUM(cantidad_recursos)` | AVG da 27.76 vs. 28.27 ponderado (A3) |
| 5 | Medida "Sum of Month" = `SUM(mes)` | Rechazado | — | `mes` es una dimensión de tiempo, no una medida |
| 6 | | | | |
| 7 | | | | |
| 8 | | | | |

### Resumen

| Decisión | Cantidad |
|---|---|
| Aceptado | |
| Corregido | |
| Rechazado | |

**Conclusión del grupo:** *(redactar: qué hizo bien Bedrock, qué tuvo que corregir el negocio y por qué el borrador no podía usarse directamente).*
