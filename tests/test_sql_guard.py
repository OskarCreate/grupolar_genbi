import unittest

from src.sql_guard import SQLValidationError, validate_sql


class SQLGuardTests(unittest.TestCase):
    VIEW = "vw_grupolar_genbi_transferencias"

    def test_valid_select(self):
        sql = """
        SELECT sede_destino, SUM(monto_debe) AS valor_transferido
        FROM vw_grupolar_genbi_transferencias
        GROUP BY sede_destino
        """
        self.assertTrue(validate_sql(sql, self.VIEW))

    def test_valid_with_database_prefix(self):
        sql = (
            "SELECT COUNT(DISTINCT num_comprobante) AS comprobantes "
            "FROM grupolar_master.vw_grupolar_genbi_transferencias"
        )
        self.assertTrue(validate_sql(sql, self.VIEW))

    def test_allows_extract_from(self):
        sql = (
            "SELECT EXTRACT(month FROM fecha_transferencia) AS mes, "
            "SUM(monto_debe) AS valor FROM vw_grupolar_genbi_transferencias "
            "GROUP BY 1"
        )
        self.assertTrue(validate_sql(sql, self.VIEW))

    def test_allows_union_all_on_same_view(self):
        sql = (
            "SELECT sede_origen AS sede, 'ENVIADO' AS rol, "
            "SUM(monto_debe) AS valor FROM vw_grupolar_genbi_transferencias "
            "GROUP BY sede_origen "
            "UNION ALL "
            "SELECT sede_destino, 'RECIBIDO', SUM(monto_debe) "
            "FROM vw_grupolar_genbi_transferencias GROUP BY sede_destino"
        )
        self.assertTrue(validate_sql(sql, self.VIEW))

    def test_blocks_fact_table(self):
        with self.assertRaises(SQLValidationError):
            validate_sql(
                "SELECT transaccion_id FROM grupolar_master.fact_resource_trans",
                self.VIEW,
            )

    def test_blocks_dimension_join(self):
        with self.assertRaises(SQLValidationError):
            validate_sql(
                "SELECT v.usuario FROM vw_grupolar_genbi_transferencias v "
                "JOIN dim_usuario u ON v.usuario = u.cod_usuario",
                self.VIEW,
            )

    def test_blocks_select_star(self):
        with self.assertRaises(SQLValidationError):
            validate_sql(
                "SELECT * FROM vw_grupolar_genbi_transferencias",
                self.VIEW,
            )

    def test_blocks_delete(self):
        with self.assertRaises(SQLValidationError):
            validate_sql(
                "DELETE FROM vw_grupolar_genbi_transferencias",
                self.VIEW,
            )

    def test_blocks_drop(self):
        with self.assertRaises(SQLValidationError):
            validate_sql(
                "SELECT 1 FROM vw_grupolar_genbi_transferencias; "
                "DROP TABLE grupolar_master.fact_resource_trans",
                self.VIEW,
            )

    def test_blocks_comments(self):
        with self.assertRaises(SQLValidationError):
            validate_sql(
                "SELECT SUM(monto_debe) FROM vw_grupolar_genbi_transferencias -- x",
                self.VIEW,
            )

    def test_blocks_cte(self):
        with self.assertRaises(SQLValidationError):
            validate_sql(
                "WITH t AS (SELECT usuario FROM vw_grupolar_genbi_transferencias) "
                "SELECT usuario FROM t",
                self.VIEW,
            )


if __name__ == "__main__":
    unittest.main()
