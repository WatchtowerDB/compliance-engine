from abc import ABC, abstractmethod


"""
Base and Framework Builders
"""
class BaseAssertionBuilder(ABC):
    def __init__(self, framework):
        self.framework = framework

    @abstractmethod
    def build(self, schema_json):
        """
        Return list of tuples: (sql_query: str, description: str)
        """
        pass


class PCIDSSAssertionBuilder(BaseAssertionBuilder):
    def build(self, schema_json):
        sql_list = []
        tables = schema_json.get("tables", [])

        for table in tables:
            table_name = table.get("name")
            columns = {col['name']: col for col in table.get("columns", [])}

            # Sensitive columns
            sensitive_keywords = ["card", "cvv", "expiry", "ssn", "dob", "password", "email"]
            sensitive_cols = [
                col for col_name, col in columns.items()
                if any(keyword in col_name.lower() for keyword in sensitive_keywords)
            ]
            for col in sensitive_cols:
                sql = f"SELECT COUNT({col['name']}) FROM {table_name} WHERE {col['name']} IS NOT NULL;"
                description = f"Check for sensitive data in '{col['name']}' for PCI-DSS in table '{table_name}'."
                sql_list.append((sql, description))

            # Audit log check
            if "created_at" in columns and "updated_at" in columns:
                sql = f"SELECT COUNT(*) FROM {table_name} WHERE created_at IS NOT NULL AND updated_at IS NOT NULL;"
                description = f"Audit columns present in '{table_name}' for PCI-DSS."
                sql_list.append((sql, description))
            else:
                sql_list.append((
                    f"SELECT COUNT(*) FROM {table_name};",
                    f"Generic PCI-DSS assertion for '{table_name}'."
                ))
        return sql_list





class DefaultAssertionBuilder(BaseAssertionBuilder):
    """Fallback for unknown frameworks"""
    def build(self, schema_json):
        sql_list = []
        for table in schema_json.get("tables", []):
            table_name = table.get("name")
            sql_list.append((
                f"SELECT COUNT(*) FROM {table_name};",
                f"Generic assertion for '{self.framework.name}' in table '{table_name}'."
            ))
        return sql_list



BUILDERS = {
    "PCI-DSS": PCIDSSAssertionBuilder,
    
}
