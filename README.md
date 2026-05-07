# rpe-emissoes-2024

Extrai as emissões totais de empresas cadastradas no Registro Público de Emissões da FGV para o ano de 2024.

## Entrada

O arquivo `ids.txt` deve conter um ID de empresa por linha. Por enquanto, mantemos apenas 5 IDs para facilitar testes.

```txt
18
32
40
43
329
```

## Saída

O script gera `emissoes_2024.csv` com as colunas:

| Coluna | Descrição |
| --- | --- |
| `id` | ID da empresa no Registro Público de Emissões |
| `nome_empresa` | Nome da empresa retornado pela API |
| `ano` | Ano extraído |
| `escopo_1` | Emissões do Escopo 1 truncadas, sem casas decimais |
| `escopo_2` | Maior valor de Escopo 2 encontrado, truncado, sem casas decimais |
| `escopo_3` | Emissões do Escopo 3 truncadas, sem casas decimais |
| `total` | Soma truncada de Escopo 1 + maior Escopo 2 + Escopo 3 |
| `status` | `ok`, `sem_dados_2024` ou `erro` |
| `erro` | Mensagem de erro, quando houver |

## Rodar localmente

```bash
python extrair_emissoes_2024.py --input ids.txt --output emissoes_2024.csv --ano 2024
```

## Rodar no GitHub Actions

1. Acesse a aba **Actions** do repositório.
2. Selecione o workflow **Extrair emissões 2024**.
3. Clique em **Run workflow**.
4. Ao final da execução, baixe o artefato **emissoes-2024**, que contém `emissoes_2024.csv`.
5. O workflow falha se alguma empresa ficar com `status=erro`, mas ainda publica o CSV para auditoria.

## Regras de extração

- O script usa apenas a biblioteca padrão do Python; não há dependências externas.
- O script usa a API pública `EmissionsChart/ChartDataParticipant` para cada ID.
- O total é calculado como `Escopo 1 + Escopo 2 + Escopo 3`.
- Se a API retornar mais de uma opção de Escopo 2, o script usa o maior valor.
- Os valores são truncados para inteiros, sem arredondamento e sem casas decimais.
