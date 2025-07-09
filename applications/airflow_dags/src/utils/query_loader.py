"""
GraphQL Query Loader Utility for Airflow DAGs.

This module provides utilities for loading GraphQL queries from .gql files
in the queries/ directory, enabling better query management and separation
of concerns between query definitions and application logic.
"""

import os
from pathlib import Path
from typing import Dict, Optional
import structlog

logger = structlog.get_logger(__name__)


class QueryLoader:
    """
    Utility class for loading GraphQL queries from .gql files.
    
    This class provides a centralized way to load and manage GraphQL queries
    from external files, improving maintainability and allowing for better
    query organization.
    """
    
    def __init__(self, queries_dir: Optional[str] = None):
        """
        Initialize the QueryLoader.
        
        Args:
            queries_dir: Path to the directory containing .gql files.
                        If None, uses the default queries/ directory.
        """
        if queries_dir is None:
            # Get the directory containing this file, then go up to src, then to queries
            current_dir = Path(__file__).parent
            src_dir = current_dir.parent
            queries_dir = src_dir / "queries"
        else:
            queries_dir = Path(queries_dir)
        
        self.queries_dir = queries_dir
        self._query_cache: Dict[str, str] = {}
        
        logger.info(f"Initialized QueryLoader with queries directory: {self.queries_dir}")
    
    def load_query(self, query_name: str) -> str:
        """
        Load a GraphQL query from a .gql file.
        
        Args:
            query_name: Name of the query file (without .gql extension)
            
        Returns:
            The GraphQL query string
            
        Raises:
            FileNotFoundError: If the query file doesn't exist
            IOError: If there's an error reading the file
        """
        # Check cache first
        if query_name in self._query_cache:
            return self._query_cache[query_name]
        
        query_file = self.queries_dir / f"{query_name}.gql"
        
        if not query_file.exists():
            raise FileNotFoundError(f"Query file not found: {query_file}")
        
        try:
            with open(query_file, 'r', encoding='utf-8') as f:
                query_content = f.read().strip()
            
            # Cache the query
            self._query_cache[query_name] = query_content
            
            logger.debug(f"Loaded query '{query_name}' from {query_file}")
            return query_content
            
        except IOError as e:
            logger.error(f"Error reading query file {query_file}: {e}")
            raise
    
    def load_all_queries(self) -> Dict[str, str]:
        """
        Load all .gql files from the queries directory.
        
        Returns:
            Dictionary mapping query names to their content
        """
        queries = {}
        
        if not self.queries_dir.exists():
            logger.warning(f"Queries directory does not exist: {self.queries_dir}")
            return queries
        
        for gql_file in self.queries_dir.glob("*.gql"):
            query_name = gql_file.stem
            try:
                queries[query_name] = self.load_query(query_name)
            except Exception as e:
                logger.error(f"Failed to load query {query_name}: {e}")
        
        logger.info(f"Loaded {len(queries)} queries from {self.queries_dir}")
        return queries
    
    def get_available_queries(self) -> list:
        """
        Get a list of available query names.
        
        Returns:
            List of query names (without .gql extension)
        """
        if not self.queries_dir.exists():
            return []
        
        return [f.stem for f in self.queries_dir.glob("*.gql")]
    
    def clear_cache(self):
        """Clear the query cache."""
        self._query_cache.clear()
        logger.debug("Query cache cleared")
    
    def reload_query(self, query_name: str) -> str:
        """
        Reload a query from disk, bypassing the cache.
        
        Args:
            query_name: Name of the query to reload
            
        Returns:
            The reloaded query string
        """
        if query_name in self._query_cache:
            del self._query_cache[query_name]
        
        return self.load_query(query_name)


# Global instance for convenience
_default_loader = None


def get_query_loader() -> QueryLoader:
    """
    Get the default QueryLoader instance.
    
    Returns:
        The default QueryLoader instance
    """
    global _default_loader
    if _default_loader is None:
        _default_loader = QueryLoader()
    return _default_loader


def load_query(query_name: str) -> str:
    """
    Convenience function to load a query using the default loader.
    
    Args:
        query_name: Name of the query file (without .gql extension)
        
    Returns:
        The GraphQL query string
    """
    return get_query_loader().load_query(query_name)


def get_available_queries() -> list:
    """
    Convenience function to get available queries using the default loader.
    
    Returns:
        List of available query names
    """
    return get_query_loader().get_available_queries()


# Example usage and testing
if __name__ == "__main__":
    # Test the query loader
    loader = QueryLoader()
    
    # List available queries
    available = loader.get_available_queries()
    print(f"Available queries: {available}")
    
    # Load all queries
    queries = loader.load_all_queries()
    for name, content in queries.items():
        print(f"\nQuery '{name}':")
        print(f"Length: {len(content)} characters")
        print(f"First 100 chars: {content[:100]}...")