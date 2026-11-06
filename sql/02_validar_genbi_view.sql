-- =====================================================================
-- GRUPO LAR - Validación de la GenBI View
-- Ejecutar UNA consulta a la vez en Athena.
-- =====================================================================

-- V1. La vista no pierde ni duplica filas de la fact.
-- Esperado: 874 | 874 | 874 | 332
SELECT
    (SELECT COUNT(*) FROM grupolar_master.fact_resource_trans)            AS filas_fact,
    COUNT(*)                                                              AS filas_vista,
    COUNT(DISTINCT transaccion_id)                                        AS transferencias,
    COUNT(DISTINCT num_comprobante)                                       AS comprobantes
FROM grupolar_master.vw_grupolar_genbi_transferencias;


-- V2. Las medidas cuadran con la fact.
-- Esperado: 2348538.23 | 217972.76 | 2130565.47
SELECT
    ROUND(SUM(monto_debe), 2)   AS valor_transferido,
    ROUND(SUM(monto_haber), 2)  AS monto_haber,
    ROUND(SUM(monto_total), 2)  AS monto_total_neto
FROM grupolar_master.vw_grupolar_genbi_transferencias;


-- V3. Estructura de la vista (lo que verá el profiler).
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'grupolar_master'
  AND table_name   = 'vw_grupolar_genbi_transferencias'
ORDER BY ordinal_position;


-- V4. Muestra de filas.
SELECT transaccion_id, num_comprobante, fecha_transferencia, periodo_mes,
       codigo_cuenta, descripcion_recurso, sede_origen, sede_destino,
       usuario, cantidad_recursos, monto_debe, monto_haber, monto_total
FROM grupolar_master.vw_grupolar_genbi_transferencias
LIMIT 10;


-- V5. Evidencia del grano: un comprobante tiene varias líneas.
-- Esperado: 1 línea -> 67 | 2 -> 81 | 3 -> 91 | 4 -> 93 comprobantes
SELECT lineas_por_comprobante, COUNT(*) AS comprobantes
FROM (
    SELECT num_comprobante, COUNT(*) AS lineas_por_comprobante
    FROM grupolar_master.vw_grupolar_genbi_transferencias
    GROUP BY num_comprobante
)
GROUP BY lineas_por_comprobante
ORDER BY lineas_por_comprobante;


-- V6. Evidencia de unidades mezcladas en cantidad_recursos.
-- Esperado: 11 unidades distintas (UND, KG, GL, M3, BOL, ...)
SELECT unidad_medida, COUNT(*) AS lineas, SUM(cantidad_recursos) AS cantidad
FROM grupolar_master.vw_grupolar_genbi_transferencias
GROUP BY unidad_medida
ORDER BY lineas DESC;
