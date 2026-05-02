from llm.llm_client import generate_sql
from db.postgres import run_query

def ask(question):
    sql = generate_sql(question)

    if "DELETE" in sql or "UPDATE" in sql:
        raise Exception("blocked query")

    result = run_query(sql)

    return {
        "sql": sql,
        "result": result
    }