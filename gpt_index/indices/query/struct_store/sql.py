"""Default query for GPTFaissIndex."""
from typing import Any, Optional

from gpt_index.data_structs.table import SQLStructTable
from gpt_index.indices.query.base import BaseGPTIndexQuery
from gpt_index.indices.response.schema import Response
from gpt_index.langchain_helpers.sql_wrapper import SQLDatabase
from gpt_index.prompts.default_prompts import DEFAULT_TEXT_TO_SQL_PROMPT
from gpt_index.prompts.prompts import TextToSQLPrompt
from gpt_index.utils import llm_token_counter


class GPTSQLStructStoreIndexQuery(BaseGPTIndexQuery[SQLStructTable]):
    """GPT SQL query over a structured database.

    Runs raw SQL over a GPTSQLStructStoreIndex. No LLM calls are made here.
    NOTE: this query cannot work with composed indices - if the index
    contains subindices, those subindices will not be queried.

    .. code-block:: python

        response = index.query("<query_str>", mode="sql")

    """

    def __init__(
        self,
        index_struct: SQLStructTable,
        sql_database: Optional[SQLDatabase] = None,
        table_name: Optional[str] = None,
        ref_doc_id_column: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize params."""
        super().__init__(index_struct=index_struct, **kwargs)
        if sql_database is None:
            raise ValueError("sql_database must be provided.")
        self._sql_database = sql_database
        if table_name is None:
            raise ValueError("table_name must be provided.")
        self._table_name = table_name
        self._ref_doc_id_column = ref_doc_id_column

    @llm_token_counter("query")
    def query(self, query_str: str, verbose: bool = False) -> Response:
        """Answer a query."""
        # NOTE: override query method in order to fetch the right results.
        # NOTE: since the query_str is a SQL query, it doesn't make sense
        # to use ResponseBuilder anywhere.
        response_str, extra_info = self._sql_database.run_sql(query_str)
        response = Response(response=response_str, extra_info=extra_info)
        return response


class GPTNLStructStoreIndexQuery(BaseGPTIndexQuery[SQLStructTable]):
    """GPT natural language query over a structured database.

    Given a natural language query, we will extract the query to SQL.
    Runs raw SQL over a GPTSQLStructStoreIndex. No LLM calls are made here.
    NOTE: this query cannot work with composed indices - if the index
    contains subindices, those subindices will not be queried.

    .. code-block:: python

        response = index.query("<query_str>", mode="sql")

    """

    def __init__(
        self,
        index_struct: SQLStructTable,
        sql_database: Optional[SQLDatabase] = None,
        table_name: Optional[str] = None,
        ref_doc_id_column: Optional[str] = None,
        text_to_sql_prompt: Optional[TextToSQLPrompt] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize params."""
        super().__init__(index_struct=index_struct, **kwargs)
        if sql_database is None:
            raise ValueError("sql_database must be provided.")
        self._sql_database = sql_database
        if table_name is None:
            raise ValueError("table_name must be provided.")
        self._table_name = table_name
        self._ref_doc_id_column = ref_doc_id_column
        self._text_to_sql_prompt = text_to_sql_prompt or DEFAULT_TEXT_TO_SQL_PROMPT

    def _parse_response_to_sql(self, response: str) -> str:
        """Parse response to SQL."""
        result_response = response.strip()
        return result_response

    def _query(self, query_str: str, verbose: bool = False) -> Response:
        """Answer a query."""
        table_info = self._sql_database.get_single_table_info(self._table_name)
        response_str, _ = self._llm_predictor.predict(
            self._text_to_sql_prompt, query_str=query_str, schema=table_info
        )

        sql_query_str = self._parse_response_to_sql(response_str)
        # assume that it's a valid SQL query
        if verbose:
            print(f"> Predicted SQL query: {sql_query_str}")

        response_str, extra_info = self._sql_database.run_sql(sql_query_str)
        response = Response(response=response_str, extra_info=extra_info)
        return response
