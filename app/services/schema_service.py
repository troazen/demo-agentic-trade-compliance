"""
Schema service for providing database schema information.
"""

from typing import Dict, Any, List
import logging
from sqlalchemy import inspect

from app.models import db

logger = logging.getLogger(__name__)


class SchemaService:
    """Service class for database schema operations."""
    
    @staticmethod
    def get_database_schema() -> Dict[str, Any]:
        """
        Get database schema information including all tables and columns.
        
        Returns:
            Dictionary with schema information including tables and columns
        """
        logger.debug("Retrieving database schema information")
        
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        schema_info = {
            'tables': []
        }
        
        for table_name in sorted(tables):
            columns = inspector.get_columns(table_name)
            pk_constraint = inspector.get_pk_constraint(table_name)
            primary_keys = pk_constraint.get('constrained_columns', []) if pk_constraint else []
            foreign_keys = inspector.get_foreign_keys(table_name)
            
            # Build column information
            column_info = []
            for col in columns:
                col_data = {
                    'name': col['name'],
                    'type': str(col['type']),
                    'nullable': col.get('nullable', True),
                    'primary_key': col['name'] in primary_keys,
                    'default': str(col.get('default', '')) if col.get('default') is not None else None
                }
                
                # Find foreign key information for this column
                fk_info = None
                for fk in foreign_keys:
                    if col['name'] in fk.get('constrained_columns', []):
                        fk_info = {
                            'referenced_table': fk.get('referred_table', ''),
                            'referenced_column': fk.get('referred_columns', [None])[0] if fk.get('referred_columns') else None
                        }
                        break
                
                if fk_info:
                    col_data['foreign_key'] = fk_info
                
                column_info.append(col_data)
            
            table_info = {
                'table_name': table_name,
                'columns': column_info
            }
            
            schema_info['tables'].append(table_info)
        
        logger.debug(f"Retrieved schema information for {len(schema_info['tables'])} tables")
        return schema_info
    
    @staticmethod
    def get_schema_dataframe() -> List[Dict[str, Any]]:
        """
        Get database schema as a flat list suitable for dataframe display.
        
        Returns:
            List of dictionaries with table and column information
        """
        schema = SchemaService.get_database_schema()
        
        result = []
        for table in schema['tables']:
            table_name = table['table_name']
            for col in table['columns']:
                fk_str = ''
                if col.get('foreign_key'):
                    fk = col['foreign_key']
                    fk_str = f"{fk['referenced_table']}.{fk['referenced_column']}" if fk.get('referenced_column') else fk.get('referenced_table', '')
                
                col_info = {
                    'Table': table_name,
                    'Column': col['name'],
                    'Type': col['type'],
                    'Nullable': 'Yes' if col['nullable'] else 'No',
                    'Primary Key': 'Yes' if col['primary_key'] else 'No',
                    'Foreign Key': fk_str
                }
                result.append(col_info)
        
        return result

