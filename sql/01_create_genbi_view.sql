-- =====================================================================
-- GRUPO LAR - GenBI View
-- Contrato entre el Data Mart (grupolar_master) y la aplicación GenBI.
-- El LLM solo puede consultar esta vista, nunca las tablas físicas.
-- Ejecutar en Athena (una sola sentencia).
-- =====================================================================
CREATE OR REPLACE VIEW grupolar_master.vw_grupolar_genbi_transferencias AS
SELECT
    f.transaccion_id,
    f.num_comprobante,
    d.fecha                                                    AS fecha_transferencia,
    d.dia,
    d.mes,
    d.nombre_mes,
    d.trimestre,
    d.anio,
    CAST(d.anio AS VARCHAR) || '-' || LPAD(CAST(d.mes AS VARCHAR), 2, '0') AS periodo_mes,
    c.codigo_cuenta,
    c.descripcion_homologada                                   AS descripcion_cuenta,
    c.nombre_clase                                             AS clase_contable,
    c.cuenta_mayor,
    r.cod_recurso,
    r.descripcion_recurso,
    r.familia                                                  AS familia_recurso,
    r.unidad_medida,
    so.cod_sede                                                AS cod_sede_origen,
    so.nombre_sede                                             AS sede_origen,
    so.tipo_sede                                               AS tipo_sede_origen,
    sd.cod_sede                                                AS cod_sede_destino,
    sd.nombre_sede                                             AS sede_destino,
    sd.tipo_sede                                               AS tipo_sede_destino,
    COALESCE(u.cod_usuario, 'SIN USUARIO')                     AS usuario,
    f.cantidad_recursos,
    f.monto_debe,
    f.monto_haber,
    ROUND(f.monto_debe - f.monto_haber, 2)                     AS monto_total
FROM grupolar_master.fact_resource_trans f
JOIN grupolar_master.dim_fecha d           ON f.fecha_key        = d.fecha_key
JOIN grupolar_master.dim_cuenta_contable c ON f.cuenta_key       = c.cuenta_key
JOIN grupolar_master.dim_recursos r        ON f.recurso_key      = r.recurso_key
JOIN grupolar_master.dim_sede so           ON f.origen_sede_key  = so.sede_key
JOIN grupolar_master.dim_sede sd           ON f.destino_sede_key = sd.sede_key
LEFT JOIN grupolar_master.dim_usuario u    ON f.usuario_key      = u.usuario_key
