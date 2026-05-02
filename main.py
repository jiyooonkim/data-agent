from service.qa_service import ask

while True:
    q = input("질문: ")

    res = ask(q)

    print("SQL:", res["sql"])
    print("결과:", res["result"])