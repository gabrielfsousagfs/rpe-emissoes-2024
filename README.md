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
5. O workflow falha se alguma empresa ficar com `status=erro` ou `status=sem_dados_2024`, mas ainda publica o CSV para auditoria.


## Solução para erro de handshake TLS

Se o GitHub Actions mostrar erro de handshake na etapa **Rodar extração**, a versão atual tenta duas rotas automaticamente:

1. `urllib` com contexto TLS mais compatível com servidores legados.
2. fallback com `curl` usando HTTP/1.1, TLS 1.2 e nível de segurança reduzido para a conexão pública da API.

O workflow também imprime a versão do OpenSSL e do curl na etapa **Diagnosticar TLS**, o que ajuda a comparar o ambiente do GitHub Actions com uma execução local.

## Como enviar as requisições da API para depuração

A melhor forma é enviar o `Copy as cURL` das requisições principais, porque ele preserva método, URL, headers e payload:

1. Abra a página da empresa no Chrome.
2. Abra **DevTools > Network**.
3. Marque **Preserve log** e filtre por **Fetch/XHR**.
4. Recarregue a página.
5. Para cada requisição abaixo, clique com o botão direito e escolha **Copy > Copy as cURL (bash)**:
   - `GetYearRangeByOrganization?organizationId=...`
   - `GetAllScopes`
   - `ChartDataParticipant`
6. Envie também o status HTTP e um trecho pequeno da resposta, se possível.

Antes de enviar, remova cookies, tokens, `Authorization` ou qualquer header que pareça sensível. Se preferir, envie um HAR exportado do DevTools, mas o `Copy as cURL` das três chamadas acima costuma ser mais fácil de reutilizar.

## Regras de extração

- O script usa apenas a biblioteca padrão do Python; não há dependências externas.
- O script usa a API pública `EmissionsChart/ChartDataParticipant` para cada ID.
- O payload do `ChartDataParticipant` replica a chamada da página: envia `subFilter` com escopos `[1, 2, 3]` e `filter.years` com os anos retornados por `GetYearRangeByOrganization`. Isso evita respostas vazias/sem dados causadas por chamar o endpoint apenas com `organizationId`.
- O total é calculado como `Escopo 1 + Escopo 2 + Escopo 3`.
- Se a API retornar mais de uma opção de Escopo 2, o script usa o maior valor.
- Os valores são truncados para inteiros, sem arredondamento e sem casas decimais.
