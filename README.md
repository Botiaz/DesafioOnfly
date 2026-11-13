# Desafio Onfly — Consolidador de reservas

CLI em Python para consolidar reservas de hotel, aplicar regras de faturamento, converter valores para BRL e gerar um relatório JSON.

O projeto está em [`onfly-desafio/`](onfly-desafio/). A implementação corrige os defeitos originais do desafio e inclui testes automatizados para as regras de negócio e o contrato do CLI.

## Funcionalidades

- Leitura de reservas e taxas de câmbio em CSV.
- Conversão de valores para BRL usando `Decimal`.
- Cálculo de noites por quarto, inclusive em viradas de mês e ano.
- Contagem por status (`CONFIRMED`, `CANCELLED` e `NO_SHOW`).
- Totais financeiros e de noites somente para reservas confirmadas.
- Consolidação mensal pelo mês do check-in.
- Ranking dos hotéis por valor total, com desempate por `hotel_id`.
- Validação de entradas e códigos de saída previsíveis.
- Geração automática do diretório de saída.

## Requisitos

- Python 3.11 ou superior.
- `pytest` e `ruff` apenas para desenvolvimento e validação.
- O programa não possui dependências de runtime além da biblioteca padrão do Python.

## Instalação

```bash
cd onfly-desafio
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

No Windows PowerShell:

```powershell
cd onfly-desafio
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

## Uso

Execução com os dados completos:

```bash
PYTHONPATH=src python -m onfly_report \
  --input data/reservas_hoteis.csv \
  --rates data/taxas_cambio.csv \
  --output output/report.json
```

Execução com a amostra de validação:

```bash
PYTHONPATH=src python -m onfly_report \
  --input data/exemplo-validacao.csv \
  --rates data/taxas_cambio.csv \
  --output output/exemplo.json
```

O programa imprime um resumo no terminal e grava o JSON no caminho informado. O argumento `--output` é opcional e usa `output/report.json` por padrão.

### Argumentos

| Argumento | Obrigatório | Padrão | Descrição |
| --- | --- | --- | --- |
| `--input` | Sim | — | CSV de reservas. |
| `--rates` | Sim | — | CSV de taxas de câmbio para BRL. |
| `--output` | Não | `output/report.json` | Arquivo JSON de saída. |
| `--top` | Não | `5` | Quantidade de hotéis no ranking; deve ser inteiro maior ou igual a 1. |

### Códigos de saída

- `0`: relatório gerado com sucesso.
- `2`: argumento inválido ou erro nos arquivos de entrada.
- `1`: erro inesperado ou falha ao escrever a saída.

## Regras de negócio

### Status

- Apenas `CONFIRMED` é faturável.
- `CANCELLED` e `NO_SHOW` entram em `total_reservations` e nas contagens por status.
- Reservas não confirmadas não entram em noites, valores, `by_month` ou `top_hotels`.

### Noites

```text
room_nights = (checkout_date - checkin_date).days * rooms
```

A diferença é não inclusiva: uma reserva de 10/01 a 13/01 representa 3 noites.

### Câmbio e precisão

```text
amount_brl = amount * rate_to_brl
```

Os valores monetários são calculados com `Decimal`. O arredondamento half-up para duas casas ocorre somente na serialização do relatório.

A média é calculada como:

```text
average_nightly_rate_brl = total_amount_brl / total_room_nights
```

Quando não há noites confirmadas, a média é `"0.00"`.

### Ordenação

- `by_month`: mês ascendente, usando o mês do check-in.
- `top_hotels`: `total_brl` decrescente; em caso de empate, `hotel_id` ascendente.
- `top_hotels` retorna no máximo a quantidade indicada por `--top`.

## Formato do relatório

O arquivo JSON possui exatamente esta estrutura:

```json
{
  "report_version": "1.0",
  "generated_at": "2025-07-01T10:00:00-03:00",
  "summary": {
    "total_reservations": 0,
    "confirmed_reservations": 0,
    "cancelled_reservations": 0,
    "no_show_reservations": 0,
    "total_room_nights": 0,
    "total_amount_brl": "0.00",
    "average_nightly_rate_brl": "0.00"
  },
  "by_month": [
    {
      "month": "2025-01",
      "reservations": 0,
      "room_nights": 0,
      "total_brl": "0.00"
    }
  ],
  "top_hotels": [
    {
      "hotel_id": "H01",
      "hotel_name": "Hotel Exemplo",
      "room_nights": 0,
      "total_brl": "0.00"
    }
  ]
}
```

Valores monetários são strings com exatamente duas casas decimais e sem separador de milhar. `generated_at` usa o offset fixo `-03:00`.

## Resultado esperado da amostra

A amostra `data/exemplo-validacao.csv` deve produzir:

| Campo | Valor |
| --- | ---: |
| `total_reservations` | `12` |
| `confirmed_reservations` | `9` |
| `cancelled_reservations` | `2` |
| `no_show_reservations` | `1` |
| `total_room_nights` | `28` |
| `total_amount_brl` | `7566.00` |
| `average_nightly_rate_brl` | `270.21` |

Resumo impresso no terminal:

```text
Reservas: 12 | Confirmadas: 9 | Noites: 28 | Total BRL: 7566.00
```

## Testes e qualidade

Execute todos os testes:

```bash
cd onfly-desafio
pytest -q
```

Execute o lint:

```bash
ruff check .
```

A suíte cobre cálculo de noites, conversão cambial, arredondamento, regras de status, agregações, ranking, validação de arquivos, códigos de saída e o dataset completo.

## Estrutura do projeto

```text
.
├── README.md
└── onfly-desafio/
    ├── data/
    │   ├── exemplo-validacao.csv
    │   ├── reservas_hoteis.csv
    │   └── taxas_cambio.csv
    ├── entrega/
    │   ├── README-ENTREGA.md
    │   └── uso-de-ia/
    ├── output/
    ├── src/onfly_report/
    │   ├── repositories/       # leitura dos CSVs
    │   ├── services/            # regras e agregação
    │   ├── cli.py               # interface de linha de comando
    │   └── models.py            # modelos de domínio
    ├── tests/
    ├── pyproject.toml
    ├── requirements.txt
    └── requirements-dev.txt
```

## Entrega

A documentação da investigação, dos defeitos corrigidos e dos testes adicionais está em [`onfly-desafio/entrega/README-ENTREGA.md`](onfly-desafio/entrega/README-ENTREGA.md). O histórico de uso de IA, quando aplicável, está em [`onfly-desafio/entrega/uso-de-ia/`](onfly-desafio/entrega/uso-de-ia/).

## Licença

Este repositório foi criado para fins de avaliação técnica da Onfly.
