Validación humana de la Semantic Layer — Grupo Lar

Entrada: config/semantic_layer_draft.json (propuesta de Amazon Bedrock). Salida: config/semantic_layer.json (capa aprobada).

AI can discover structure. Business governs meaning.

Este documento tiene dos partes:

Parte A: las decisiones de negocio que gobiernan la capa aprobada, cada una con su evidencia en Athena. Ya está completa.
Parte B: la comparación con lo que propuso tu borrador real. Se completa después de ejecutar scripts/02_build_semantic_draft.py, porque cada ejecución de Bedrock puede proponer cosas distintas.
Parte A — Decisiones de negocio con evidencia

Las cifras salen de sql/02_validar_genbi_view.sql y de las golden queries.

A1. El grano: una fila no es un comprobante
Evidencia: la vista tiene 874 líneas pero 332 comprobantes; un comprobante tiene de 1 a 4 líneas (consulta V5).
Consecuencia: COUNT(num_comprobante) devuelve 874 y está mal.
Definición aprobada: N.º de comprobantes = COUNT(DISTINCT num_comprobante) → 332. N.º de transferencias = COUNT(DISTINCT transaccion_id) → 874.
A2. La cantidad mezcla unidades de medida
Evidencia: cantidad_recursos está en 11 unidades distintas: UND, KG, GL, M3, BOL, ROL, VAR, M2, BAL, MIL y PAR (consulta V6).
Consecuencia: sumar bolsas de cemento con metros cúbicos de arena da un número sin significado de negocio.
Definición aprobada: Cantidad transferida = SUM(cantidad_recursos), pero solo se compara dentro de un mismo recurso o unidad de medida (regla de negocio 4). Cuando una pregunta dice "más recursos" sin métrica, se mide por valor transferido (ambigüedad recursos).
A3. Precio promedio: una agregación válida no es una métrica válida
Evidencia: para el Cemento Portland, AVG(monto_debe / cantidad_recursos) da 27.76; el costo ponderado SUM(monto_debe) / SUM(cantidad_recursos) da 28.27 (GQ12).
Definición aprobada: Costo unitario promedio = SUM(monto_debe) / NULLIF(SUM(cantidad_recursos), 0), siempre por recurso.
A4. Monto Total, Debe y Haber
Evidencia: Debe 2,348,538.23; Haber 217,972.76; Total 2,130,565.47 (consulta V2).
Definiciones aprobadas:
Valor transferido = SUM(monto_debe).
Monto Haber = SUM(monto_haber): representa reversiones (devoluciones o anulaciones), no gastos ni transferencias nuevas.
Monto Total neto = SUM(monto_total), donde monto_total = monto_debe − monto_haber se calcula en la vista y no se almacena en la fact.
% revertido = SUM(monto_haber) * 100 / NULLIF(SUM(monto_debe), 0) → 9.28 %.
A5. La sede tiene dos roles
Evidencia: la fact se une dos veces con dim_sede (origen y destino).
Definición aprobada: "envía / transfiere / sale de" → sede_origen; "recibe / llega a / hacia" → sede_destino. Si la pregunta no indica el rol, se usa sede_destino.
A6. Ambigüedades del lenguaje del negocio
Término	Puede significar	Regla aprobada
transacción	línea o comprobante	N.º de transferencias
movimiento	transferencias, valor o cantidad	N.º de transferencias
monto	Debe, Haber o neto	Monto Total neto
mejor / principal	cualquier métrica	Valor transferido
recursos ("más recursos")	cantidad, valor o transferencias	Valor transferido (la cantidad mezcla unidades)
sede	origen o destino	Sede de destino
A7. Contexto de negocio
Moneda PEN (S/), configuración regional es-PE; no se convierte a otra moneda.
Periodo cubierto: enero a diciembre de 2025.
Plan de cuentas real (CONCAR); transferencias, recursos y sedes simulados. El insight no debe presentarlos como datos reales de operación.
Parte B — Comparación con el borrador de Bedrock

Borrador generado con scripts/02_build_semantic_draft.py (modelo Amazon Nova, us-east-1). Cada propuesta se clasifica como Aceptado (pasa igual), Corregido (pasa con otra definición) o Rechazado (no pasa).

B1. Dimensiones propuestas
#	Propuesta de Bedrock	Decisión	Versión aprobada	Por qué
1	num_comprobante como dimensión "Transfer Voucher", "identificador único"	Corregido	Dimensión degenerada; se usa en la métrica numero_comprobantes = COUNT(DISTINCT num_comprobante)	No es único por fila: 874 líneas y 332 comprobantes (A1). No es un eje de análisis, sino algo que se cuenta
2	fecha_transferencia	Aceptado	fecha_transferencia	Correcta como dimensión de tiempo
3	cod_recurso	Corregido	descripcion_recurso, con la lista de valores exactos	El usuario pregunta por nombre ("cemento"), no por código interno
4	descripcion_recurso	Aceptado	Dimensión recurso	Correcta
5	unidad_medida	Aceptado	unidad_medida y regla de negocio 4	Correcta; además se convirtió en regla porque la cantidad mezcla 11 unidades (A2)
6	cod_sede_origen	Corregido	sede_origen (nombre) y tipo_sede_origen	El código no es legible; falta el tipo (almacén u obra) y el significado del rol "envía" (A5)
7	cod_sede_destino	Corregido	sede_destino (nombre) y tipo_sede_destino	Igual que el anterior, con el rol "recibe"; necesario para "rotación entre obras"
8	anio (lo llamó "Time")	Aceptado	anio	Correcta; solo se corrige la etiqueta a "Año"
9	mes	Aceptado	mes, con la regla de filtrar junto con anio	Correcta para filtros
10	trimestre	Aceptado	trimestre	Correcta
B2. Medidas propuestas
#	Propuesta de Bedrock	Decisión	Versión aprobada	Por qué
11	"Quantity of Resources" = cantidad_recursos, "cantidad total transferida"	Corregido	cantidad_transferida = SUM(cantidad_recursos), solo por recurso o unidad	Sumarla entre recursos mezcla bolsas, m³, kg y galones (A2)
12	"Value of Resources Transferred" = monto_debe	Aceptado	valor_transferido = SUM(monto_debe)	Correcta; Bedrock no dio la agregación y el negocio la fijó
13	"Reversed Value" = monto_haber, devoluciones o anulaciones	Aceptado	monto_haber = SUM(monto_haber)	Interpretó bien el significado de negocio (A4)
14	"Net Value" = monto_total (Debe − Haber)	Aceptado	monto_total_neto = SUM(monto_total)	Correcta (A4)

Observación: Bedrock propuso columnas, no métricas. No indicó ninguna agregación SQL; esa decisión la tomó el negocio.

B3. Campos no aditivos, sinónimos y ambigüedades
#	Propuesta de Bedrock	Decisión	Versión aprobada	Por qué
15	non_additive_fields: monto_haber y monto_total	Rechazado	Ambos son aditivos	Son importes por línea: se suman sin error. GQ04 (SUM(monto_total) = SUM(monto_debe − monto_haber) = 2,130,565.47) y GQ05 (217,972.76) lo prueban con 13/13. Los campos que de verdad no se suman son los identificadores (transaccion_id, num_comprobante, codigo_cuenta), el tiempo (anio, mes, dia), los ratios (% revertido, costo unitario) y la cantidad entre unidades distintas
16	Sinónimos solo en inglés ("Transfer Value", "Return Value", "Net Transfer Value")	Corregido	81 sinónimos en español	Los usuarios de Grupo Lar preguntan en español ("valor transferido", "devoluciones", "monto neto")
17	Ambigüedad: monto_total es derivado y no está en la fact	Aceptado	Regla de negocio 2	Es correcto, pero no es una ambigüedad del lenguaje del negocio
B4. Respuesta a las preguntas de validación de Bedrock
¿Se incluye monto_total como medida? ¿Es aditiva? Sí, como monto_total_neto = SUM(monto_total). Es aditiva: la suma de los netos por línea es igual a Debe − Haber total (GQ04).
¿Qué otros campos no deben sumarse? Los identificadores (transaccion_id, num_comprobante), los códigos (codigo_cuenta, cod_recurso), los campos de tiempo y los ratios. cantidad_recursos solo se suma dentro de una misma unidad de medida.
B5. Lo que Bedrock no detectó y agregó el negocio
Elemento agregado	Por qué era necesario
Dimensión cuenta contable (codigo_cuenta, descripcion_cuenta, clase_contable)	Es el centro de la problemática del proyecto y responde la pregunta 2; Bedrock la omitió
Dimensiones usuario, familia_recurso, periodo_mes, nombre_mes	Necesarias para las preguntas 3, 4 y 5 y para tendencias mensuales
Métricas numero_transferencias y numero_comprobantes con DISTINCT	Bedrock no propuso ningún conteo y no advirtió la duplicación por grano (A1)
Métricas porcentaje_revertido, valor_promedio_comprobante, costo_unitario_promedio y obras_destino	Indicadores del negocio que no existen como columna (A3, A4)
7 ambigüedades (transacción, movimiento, monto, mejor, principal, recursos, sede)	Bedrock solo registró una observación técnica, ninguna ambigüedad del lenguaje
Contexto de moneda (PEN, S/) y nota de datos simulados	Evita que el insight invente moneda o presente datos simulados como reales (A7)
Resumen
Decisión	Cantidad	Elementos
Aceptado	10	2, 4, 5, 8, 9, 10, 12, 13, 14, 17
Corregido	6	1, 3, 6, 7, 11, 16
Rechazado	1	15
Agregado por el negocio	6 grupos	Tabla B5

Conclusión del grupo: (redactar con sus palabras: qué hizo bien Bedrock, qué tuvo que corregir el negocio y por qué el borrador no podía usarse directamente).