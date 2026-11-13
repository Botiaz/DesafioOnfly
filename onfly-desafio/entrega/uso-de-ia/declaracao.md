# Declaração de uso de IA

## Ferramenta e modelo

- **Ferramenta:** Claude Code (extensão do VS Code)
- **Modelo:** Claude Opus 5.5 (`claude-opus-5-5`)

## O que a IA fez

**Ambiente e diagnóstico**

- Conferiu a versão do Python (3.14 na `.venv`, compatível com `>=3.11`), rodou o CLI e os testes e
  confirmou que as falhas iniciais eram defeitos de lógica, não de ambiente.
- Adaptou os comandos do README (bash) para PowerShell.
- Leu o `output/report.json` gerado com defeitos e apontou os sintomas visíveis (noites negativas,
  média `0.00`, ranking crescente, `by_month` sem fechar com as confirmadas).

**Revisão das minhas correções**

- Câmbio: confirmou a correção, verificou que não restava `float` no caminho do dinheiro e sugeriu
  remover o `Decimal(str(...))` redundante.
- Noites: explicou por que `.day` falhava (`timedelta` só tem `.days`; `date.day` é o dia do mês, o
  que gerava o `-28` na virada de mês).
- Ranking: explicou que `item[2]` não existe (as tuplas de `dict.items()` têm 2 posições) e que o
  defeito era a direção da ordenação; sugeriu negar o valor em vez de `reverse=True`, para não
  inverter o desempate por `hotel_id`.

**Defeitos não cobertos pelos testes fornecidos**

- Encontrou o limite fixo de 200 linhas na leitura do CSV (o arquivo real tem 300 reservas).
- Apontou que `is_billable` excluía `CANCELLED` e `NO_SHOW` em vez de aceitar só `CONFIRMED`.

**Testes e validação**

- A meu pedido, escreveu 54 testes adicionais em `tests/test_unit_services.py`,
  `tests/test_report_rules.py` e `tests/test_cli_contract.py` (noites em viradas de mês/ano e ano
  bissexto, câmbio exato, arredondamento half-up só na serialização, regras de status, ordenação,
  `--top`, schema do relatório, códigos de saída e conferência do dataset real). Os testes dos dois
  defeitos acima foram escritos para falhar até a correção.
- Rodou a suíte e o CLI em um ambiente isolado com Python 3.11.18 e comparou o relatório com o
  gerado no 3.14 (idênticos).
- Gerou os logs de sessão e redigiu este arquivo.

## O que eu fiz

- Configurei o ambiente (venv, dependências, interpretador no VS Code) e rodei o CLI.
- Fiz todas as alterações no código de `src/`:
  - `currency_converter.py`: troquei a divisão pela multiplicação pela taxa e removi o uso de `float`.
  - `stay_calculator.py`: passei a usar a diferença entre as datas, `(checkout - checkin).days`.
  - `status_policy.py`: identifiquei sozinho que `NO_SHOW` entrava nos totais; depois da revisão,
    passei a aceitar apenas `CONFIRMED`.
  - `report_builder.py`: localizei o `sorted` do `top_hotels` e inverti a ordenação para `total_brl`
    decrescente, mantendo o desempate por `hotel_id` ascendente.
  - `csv_reservation_repository.py`: removi o limite de leitura, para o arquivo ser lido até o fim.
- Decidi a ordem de investigação dos defeitos e validei as explicações e sugestões da IA antes de
  aplicá-las.
- Pedi os testes adicionais e a verificação no Python 3.11.
- Revisei os logs de sessão e esta declaração antes da entrega.
