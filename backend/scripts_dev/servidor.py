"""Sobe a API local apontando para o ``lavconta_dev``.

Uso (na pasta backend):
    .\\.venv\\Scripts\\python.exe -m scripts_dev.servidor

Só a variável ``DATABASE_URL`` é sobrescrita no processo; o ``.env`` não é
editado. Autenticação continua no Supabase do ``.env`` (login real), mas os
dados de negócio ficam no banco local.
"""

import os

import uvicorn

from scripts_dev.banco_dev import url_banco_dev


def main() -> None:
    # definida antes de a aplicação ler a configuração; o processo de reload
    # do uvicorn herda o ambiente
    os.environ["DATABASE_URL"] = url_banco_dev()
    print("API local usando o banco lavconta_dev em http://localhost:8000")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
