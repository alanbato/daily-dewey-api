# Helper functions for DDC API usage

import sqlite3


class DDCDatabase:
    """Helper class for querying DDC database"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_section(self, code: str) -> dict[str, str | int] | None:
        """Get section details by code"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM full_classification 
                WHERE section_code = ?
            """,
                (code,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "section_code": row[0],
                    "section_description": row[1],
                    "division_code": row[2],
                    "division_description": row[3],
                    "main_class_code": row[4],
                    "main_class_description": row[5],
                }
        return None

    def search(self, query: str, limit: int = 10) -> list[dict[str, str]]:
        """Search across all DDC levels"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT code, title, level, display 
                FROM searchable_ddc 
                WHERE search_text LIKE ?
                ORDER BY code
                LIMIT ?
            """,
                (f"%{query}%", limit),
            )
            return [
                {"code": row[0], "title": row[1], "level": row[2], "display": row[3]}
                for row in cursor.fetchall()
            ]

    def get_random_section(
        self, exclude_unassigned: bool = True
    ) -> dict[str, str | int] | None:
        """Get a random section"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if exclude_unassigned:
                cursor.execute("""
                    SELECT * FROM full_classification 
                    WHERE section_description NOT LIKE '%[Unassigned]%'
                    ORDER BY RANDOM() 
                    LIMIT 1
                """)
            else:
                cursor.execute("""
                    SELECT * FROM full_classification 
                    ORDER BY RANDOM() 
                    LIMIT 1
                """)
            row = cursor.fetchone()
            if row:
                return {
                    "section_code": row[0],
                    "section_description": row[1],
                    "division_code": row[2],
                    "division_description": row[3],
                    "main_class_code": row[4],
                    "main_class_description": row[5],
                }
        return None

    def get_sections_by_division(
        self, division_code: str
    ) -> list[dict[str, str | int]]:
        """Get all sections in a division"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT code, description 
                FROM sections 
                WHERE division = ?
                ORDER BY code
            """,
                (division_code,),
            )
            return [
                {"code": row[0], "description": row[1]} for row in cursor.fetchall()
            ]

    def get_divisions_by_main_class(
        self, main_class_code: str
    ) -> list[dict[str, str | int]]:
        """Get all divisions in a main class"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT code, description 
                FROM divisions 
                WHERE main_class = ?
                ORDER BY code
            """,
                (main_class_code,),
            )
            return [
                {"code": row[0], "description": row[1]} for row in cursor.fetchall()
            ]


# Example usage:
# ddc = DDCDatabase('ddc_database.db')
# result = ddc.search('computer')
# random_section = ddc.get_random_section()
