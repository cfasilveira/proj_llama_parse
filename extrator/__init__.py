"""
Pacote `extrator` — todo o código da extração de tabelas vive aqui.

Como os módulos se relacionam (fluxo de dados):

    main.py
      └── extrator/config.py          carrega .env e valida (chave, PDF, pasta)
      └── extrator/logging_config.py  configura o logger (console + arquivo)
      └── extrator/pipeline.py        orquestra tudo
             ├── extrator/parser_llama.py  fala com a API do LlamaParse (único com rede)
             └── extrator/tabelas.py       funções puras: filtrar, nomear e salvar tabelas

A regra de ouro do projeto: `tabelas.py` e `config.py` NÃO fazem chamadas de rede,
por isso são fáceis de testar com o pytest (testes offline, sem gastar créditos).
"""
