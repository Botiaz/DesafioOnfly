# Entrega — Consolidador de reservas de hotel

## Defeitos corrigidos

| # | Arquivo | Sintoma | Causa raiz | Correção |
|-|-|-|-|-|
| 1 | `services/currency_converter.py` | Valores em moeda estrangeira muito menores que o esperado (ex.: 100 USD virava ~18 BRL em vez de 542). | A conversão dividia o valor pela taxa em vez de multiplicar. | `amount * rate` |
| 2 | `services/currency_converter.py` | Risco de centavos errados nos totais. | O cálculo convertia `Decimal` para `float` e voltava, perdendo precisão antes da soma. | Conta feita só em `Decimal` |
| 3 | `services/stay_calculator.py` | Noites negativas quando a estadia cruza mês/ano (check-in 30/01, check-out 02/02 dava `-28`). | O código subtraía o dia do mês (`checkout.day - checkin.day`) em vez da diferença entre as datas. | `(checkout - checkin).days * rooms` |
| 4 | `services/status_policy.py` | Reservas `NO_SHOW` entrando em noites, valores, `by_month` e `top_hotels`. | A regra de faturamento só excluía `CANCELLED`, em vez de aceitar apenas `CONFIRMED`. | `status == "CONFIRMED"` |
| 5 | `services/report_builder.py` | `top_hotels` trazia os hotéis de **menor** valor, em ordem crescente. | O `sorted` ordenava `total_brl` de forma ascendente. | Chave `(-amount, hotel_id)`: valor decrescente, desempate por `hotel_id` crescente |
| 6 | `repositories/csv_reservation_repository.py` | O relatório contava 200 reservas; o arquivo tem 300. | A leitura parava com um `break` fixo ao chegar a 200 linhas. | Leitura do arquivo até o fim |

Os defeitos 1, 3, 4 e 5 eram apontados pelos testes fornecidos. Os defeitos 2 e 6 não eram cobertos
por eles e foram encontrados na revisão do código; o 6 foi o que mais alterava o relatório final.

## Como investiguei

1. **Reproduzi o problema.** Rodei o CLI na amostra `data/exemplo-validacao.csv` e comparei com a
   tabela esperada do README. Também rodei `pytest -q` (5 falhas no início, como previsto).
2. **Fui do sintoma ao código.** Cada teste que falhava apontava uma regra (câmbio, noites, status,
   ranking). Segui o fluxo `ler → converter tipos → contar status → filtrar CONFIRMED → agregar`
   pelos módulos em `services/` e `repositories/` até achar a linha responsável.
3. **Corrigi um defeito por vez**, rodando o teste correspondente após cada mudança para isolar o
   efeito.
4. **Revisei o que os testes não cobriam.** Com os testes fornecidos passando, conferi o código contra
   as regras do README e os dados reais. Assim apareceram o `float` no dinheiro, a regra de status
   escrita por exclusão e o limite de 200 linhas (o relatório mostrava 200 reservas, mas o CSV tem 300).
5. **Ampliei os testes** para travar cada regra, incluindo os dois defeitos que os testes originais
   não pegavam.

Usei IA (Claude Code) como apoio; o detalhamento está em `entrega/uso-de-ia/`.

## Testes adicionais

Os testes fornecidos não foram alterados. Adicionei 54 testes em três arquivos:

- `tests/test_unit_services.py`: funções isoladas. Noites (virada de mês, de ano, ano bissexto,
  vários quartos), câmbio exato em `Decimal`, arredondamento half-up (`2.675 → "2.68"`; com `float`
  daria `2.67`) e regra de status (inclusive status desconhecidos).
- `tests/test_report_rules.py`: ponta a ponta via CLI. Schema do relatório, dinheiro como string com
  2 casas, `CANCELLED`/`NO_SHOW` fora de `by_month` e `top_hotels`, relatório sem confirmadas, mês do
  check-in, ordenação, arredondamento só na serialização, média sobre o total exato, desempate do
  ranking, limite do `--top` e arquivo com mais de 200 linhas.
- `tests/test_cli_contract.py`: contrato do CLI. Código de saída `0` (criando o diretório de saída),
  código `2` para `--top` inválido, argumento ausente, arquivo inexistente, coluna faltando e linha
  malformada, e conferência do dataset real contra as contagens do próprio CSV.

## Como validar

Requisitos: Python 3.11+.

```bash
python3.11 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

pytest -q

PYTHONPATH=src python -m onfly_report \
  --input data/exemplo-validacao.csv \
  --rates data/taxas_cambio.csv \
  --output output/exemplo.json
```

No Windows (PowerShell), defina a variável antes: `$env:PYTHONPATH = "src"`.

A saída da amostra deve bater com a tabela do README:

```
Reservas: 12 | Confirmadas: 9 | Noites: 28 | Total BRL: 7566.00
```

Relatório do dataset completo (`data/reservas_hoteis.csv`), antes e depois:

| Campo | Antes | Depois |
|-|-|-|
| `total_reservations` | 200 | 300 |
| `confirmed_reservations` | 153 | 235 |
| `total_room_nights` | -1393 | 1347 |
| `total_amount_brl` | 193218.53 | 396170.00 |
| `average_nightly_rate_brl` | 0.00 | 294.11 |
| 1º em `top_hotels` | H04 (9918.09) | H06 (45165.46) |

## Resultado do pytest

```
$ pytest -q
...........................................................              [100%]
59 passed
```

Validado com Python 3.14.7 e com Python 3.11.18; o relatório gerado é idêntico nas duas versões
(exceto `generated_at`). `ruff check .` sem apontamentos.
