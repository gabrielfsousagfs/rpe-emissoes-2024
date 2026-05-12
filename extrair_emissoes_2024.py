import argparse
import csv
import json
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any


BASE_URL = "https://registropublicodeemissoesapi.fgv.br"
DEFAULT_YEAR = 2024

HEADERS = {
    "Accept": "text/plain",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Content-Type": "application/json-patch+json",
    "Expires": "Sat, 01 Jan 2000 00:00:00 GMT",
    "Origin": "https://registropublicodeemissoes.fgv.br",
    "Pragma": "no-cache",
    "Referer": "https://registropublicodeemissoes.fgv.br/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
}


def carregar_ids(caminho: str) -> list[str]:
    """Carrega IDs de empresas, um por linha, ignorando linhas vazias."""
    with open(caminho, "r", encoding="utf-8") as arquivo:
        return [linha.strip() for linha in arquivo if linha.strip()]


def criar_contexto_ssl() -> ssl.SSLContext:
    """Cria contexto TLS compatível com servidores legados.

    O endpoint da FGV pode falhar em ambientes com OpenSSL 3, como o GitHub
    Actions, por rejeitar configurações TLS modernas durante o handshake.
    Reduzimos o nível de segurança apenas para esta conexão pública de leitura.
    """
    contexto = ssl.create_default_context()
    contexto.minimum_version = ssl.TLSVersion.TLSv1_2

    try:
        contexto.set_ciphers("DEFAULT:@SECLEVEL=1")
    except ssl.SSLError:
        pass

    legacy_server_connect = getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0)
    if legacy_server_connect:
        contexto.options |= legacy_server_connect

    return contexto


def fazer_requisicao_urllib(
    url: str,
    method: str,
    payload: dict[str, Any] | None,
    timeout: int,
) -> tuple[int, str]:
    """Faz uma requisição HTTP usando urllib e contexto TLS ajustado."""
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url=url,
        data=data,
        headers=HEADERS,
        method=method,
    )

    try:
        with urllib.request.urlopen(
            request, timeout=timeout, context=criar_contexto_ssl()
        ) as response:
            body = response.read().decode("utf-8")
            return response.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body


def fazer_requisicao_curl(
    url: str,
    method: str,
    payload: dict[str, Any] | None,
    timeout: int,
) -> tuple[int, str]:
    """Faz fallback via curl quando o handshake TLS do urllib falha."""
    comando = [
        "curl",
        "--silent",
        "--show-error",
        "--location",
        "--http1.1",
        "--tlsv1.2",
        "--ciphers",
        "DEFAULT:@SECLEVEL=1",
        "--connect-timeout",
        "30",
        "--max-time",
        str(timeout),
        "--request",
        method,
    ]

    for chave, valor in HEADERS.items():
        comando.extend(["--header", f"{chave}: {valor}"])

    if payload is not None:
        comando.extend(["--data", json.dumps(payload)])

    comando.extend(["--write-out", "\n%{http_code}", url])

    resultado = subprocess.run(
        comando,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout + 10,
    )
    saida = resultado.stdout

    if not saida:
        raise RuntimeError(f"curl falhou: {resultado.stderr.strip()}")

    body, _, status_text = saida.rpartition("\n")
    try:
        status = int(status_text)
    except ValueError as exc:
        raise RuntimeError(
            f"curl retornou status inválido: {status_text}; stderr={resultado.stderr}"
        ) from exc

    if resultado.returncode != 0 and status == 0:
        raise RuntimeError(f"curl falhou: {resultado.stderr.strip()}")

    return status, body


def fazer_requisicao(
    url: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> tuple[int, str]:
    """Faz uma requisição HTTP e retorna status e corpo como texto."""
    try:
        return fazer_requisicao_urllib(url, method, payload, timeout)
    except (ssl.SSLError, urllib.error.URLError, TimeoutError) as exc:
        print(f"Aviso: urllib falhou para {url}: {exc}. Tentando fallback com curl.")
        return fazer_requisicao_curl(url, method, payload, timeout)


def converter_ano(valor: Any, ano_alvo: int) -> int | None:
    """Converte um valor para ano quando ele está no intervalo esperado."""
    if isinstance(valor, bool):
        return None

    if isinstance(valor, str) and valor.isdigit():
        valor = int(valor)

    if isinstance(valor, int) and 1990 <= valor <= ano_alvo:
        return valor

    return None


def coletar_anos(objeto: Any, ano_alvo: int) -> list[int]:
    """Coleta valores que parecem anos dentro de uma resposta JSON."""
    anos: list[int] = []

    ano = converter_ano(objeto, ano_alvo)
    if ano is not None:
        return [ano]

    if isinstance(objeto, list):
        for item in objeto:
            anos.extend(coletar_anos(item, ano_alvo))

    if isinstance(objeto, dict):
        for valor in objeto.values():
            anos.extend(coletar_anos(valor, ano_alvo))

    return sorted(set(anos))


def extrair_anos_do_year_range(body: str, ano_alvo: int) -> list[int]:
    """Extrai a lista de anos que deve ser enviada ao ChartDataParticipant."""
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return [ano_alvo]

    result = data.get("result", data)

    if isinstance(result, dict):
        for chave_anos in ("years", "anos", "availableYears", "yearRange"):
            if chave_anos in result:
                anos = coletar_anos(result[chave_anos], ano_alvo)
                if anos:
                    return anos

        pares_inicio_fim = (
            ("minYear", "maxYear"),
            ("startYear", "endYear"),
            ("initialYear", "finalYear"),
            ("firstYear", "lastYear"),
        )
        for chave_inicio, chave_fim in pares_inicio_fim:
            inicio = converter_ano(result.get(chave_inicio), ano_alvo)
            fim = converter_ano(result.get(chave_fim), ano_alvo)
            if inicio is not None and fim is not None:
                if inicio <= fim:
                    return list(range(inicio, fim + 1))

    anos = coletar_anos(result, ano_alvo)
    if len(anos) == 2 and anos[1] - anos[0] > 1:
        return list(range(anos[0], anos[1] + 1))

    return anos or [ano_alvo]


def inicializar_sessao(org_id: str, ano: int) -> list[int]:
    """Replica chamadas iniciais feitas pela página antes do gráfico de emissões."""
    url_year_range = (
        f"{BASE_URL}/api/services/app/EstatisticaPublica/"
        f"GetYearRangeByOrganization?organizationId={int(org_id)}"
    )
    status, body = fazer_requisicao(url_year_range)
    if status != 200:
        raise RuntimeError(f"GetYearRange retornou HTTP {status}: {body[:300]}")

    anos = extrair_anos_do_year_range(body, ano)

    url_scopes = f"{BASE_URL}/api/services/app/EstatisticaPublica/GetAllScopes"
    status, body = fazer_requisicao(url_scopes)
    if status != 200:
        raise RuntimeError(f"GetAllScopes retornou HTTP {status}: {body[:300]}")

    return anos


def montar_payload_chart_data(org_id: str, anos: list[int]) -> dict[str, Any]:
    """Monta o payload observado na chamada real da página."""
    return {
        "organizationId": int(org_id),
        "subFilter": {
            "scopes": [1, 2, 3],
            "categories": [],
            "gases": [],
            "emissionTypes": [],
            "sectors": [],
            "isSin": False,
        },
        "filter": {"years": anos},
    }


def buscar_chart_data(org_id: str, anos: list[int]) -> dict[str, Any]:
    """Busca os dados de emissões de uma empresa na API pública do RPE."""
    payload = montar_payload_chart_data(org_id, anos)
    status, body = fazer_requisicao(
        f"{BASE_URL}/api/services/app/EmissionsChart/ChartDataParticipant",
        method="POST",
        payload=payload,
    )

    if status != 200:
        raise RuntimeError(
            f"ChartDataParticipant retornou HTTP {status}: {body[:300]}"
        )

    data = json.loads(body)

    if not data.get("success"):
        raise RuntimeError(f"API retornou success=false: {data}")

    if "result" not in data:
        raise RuntimeError("Resposta sem campo result")

    if "items" not in data["result"]:
        raise RuntimeError("Resposta sem result.items")

    return data


def truncar_valor(valor: float | int | None) -> int | None:
    """Remove casas decimais sem arredondar."""
    if valor is None:
        return None

    return int(valor)


def escopo_por_id_ou_descricao(item: dict[str, Any]) -> int | None:
    """Identifica o escopo retornado pela API.

    A API normalmente retorna context.id 1, 2 e 3. Como o Escopo 2 pode aparecer
    em mais de uma variação, a descrição/nome também é usada como fallback.
    """
    context = item.get("context", {})
    scope_id = context.get("id")

    if scope_id in {1, 2, 3}:
        return scope_id

    texto_contexto = " ".join(
        str(context.get(campo, "")) for campo in ("name", "desc")
    ).lower()

    if "escopo" in texto_contexto and "1" in texto_contexto:
        return 1
    if "escopo" in texto_contexto and "2" in texto_contexto:
        return 2
    if "escopo" in texto_contexto and "3" in texto_contexto:
        return 3

    return None


def extrair_emissoes_ano(data: dict[str, Any], ano: int) -> dict[str, Any]:
    """Extrai emissões do ano informado e soma Escopos 1, 2 e 3.

    Quando houver mais de um valor para Escopo 2 no mesmo ano, mantém o maior.
    """
    resultado: dict[str, Any] = {
        "nome_empresa": data["result"].get("name"),
        "escopo_1": None,
        "escopo_2": None,
        "escopo_3": None,
    }

    for item in data["result"]["items"]:
        scope_id = escopo_por_id_ou_descricao(item)
        if scope_id not in {1, 2, 3}:
            continue

        for ponto in item.get("data", []):
            if ponto.get("year") != ano or ponto.get("shouldNullify"):
                continue

            valor = ponto.get("value")
            if valor is None:
                continue

            chave = f"escopo_{scope_id}"

            if scope_id == 2:
                valor_atual = resultado[chave]
                resultado[chave] = (
                    valor if valor_atual is None else max(valor_atual, valor)
                )
            else:
                resultado[chave] = valor

    valores = [resultado["escopo_1"], resultado["escopo_2"], resultado["escopo_3"]]

    if all(valor is None for valor in valores):
        resultado["total"] = None
        resultado["status"] = f"sem_dados_{ano}"
    else:
        resultado["status"] = "ok"

    resultado["escopo_1"] = truncar_valor(resultado["escopo_1"])
    resultado["escopo_2"] = truncar_valor(resultado["escopo_2"])
    resultado["escopo_3"] = truncar_valor(resultado["escopo_3"])

    escopos_truncados = [
        resultado["escopo_1"],
        resultado["escopo_2"],
        resultado["escopo_3"],
    ]
    if any(valor is not None for valor in escopos_truncados):
        resultado["total"] = sum(valor or 0 for valor in escopos_truncados)

    return resultado


def processar_empresa(org_id: str, ano: int) -> dict[str, Any]:
    """Processa uma empresa e sempre retorna uma linha para auditoria."""
    linha: dict[str, Any] = {
        "id": org_id,
        "nome_empresa": None,
        "ano": ano,
        "escopo_1": None,
        "escopo_2": None,
        "escopo_3": None,
        "total": None,
        "status": None,
        "erro": None,
    }

    try:
        anos = inicializar_sessao(org_id, ano)
        data = buscar_chart_data(org_id, anos)
        linha.update(extrair_emissoes_ano(data, ano))
    except Exception as exc:
        linha["status"] = "erro"
        linha["erro"] = str(exc)

    return linha


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extrai emissões totais de empresas no Registro Público de Emissões."
    )
    parser.add_argument(
        "--input", default="ids.txt", help="Arquivo TXT com um ID por linha."
    )
    parser.add_argument(
        "--output", default="emissoes_2024.csv", help="Arquivo CSV de saída."
    )
    parser.add_argument("--ano", type=int, default=DEFAULT_YEAR, help="Ano a extrair.")
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Pausa em segundos entre empresas para reduzir carga na API.",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Finaliza com erro se alguma empresa ficar com status erro.",
    )
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Finaliza com erro se alguma empresa ficar sem dados para o ano.",
    )
    args = parser.parse_args()

    ids = carregar_ids(args.input)
    resultados = []

    total = len(ids)
    for indice, org_id in enumerate(ids, start=1):
        print(f"Processando {org_id} ({indice}/{total})")
        resultado = processar_empresa(org_id, args.ano)
        resultados.append(resultado)
        time.sleep(args.delay)

    colunas = [
        "id",
        "nome_empresa",
        "ano",
        "escopo_1",
        "escopo_2",
        "escopo_3",
        "total",
        "status",
        "erro",
    ]
    with open(args.output, "w", encoding="utf-8", newline="") as arquivo:
        writer = csv.DictWriter(arquivo, fieldnames=colunas)
        writer.writeheader()
        writer.writerows(resultados)

    print(f"Arquivo salvo em: {args.output}")

    erros = sum(1 for linha in resultados if linha["status"] == "erro")
    sem_dados = sum(
        1 for linha in resultados if linha["status"] == f"sem_dados_{args.ano}"
    )
    print(f"Resumo: {len(resultados)} empresas, {erros} erros, {sem_dados} sem dados.")

    if args.fail_on_error and erros:
        raise SystemExit(f"Extração finalizada com {erros} erro(s).")

    if args.fail_on_missing and sem_dados:
        raise SystemExit(f"Extração finalizada com {sem_dados} empresa(s) sem dados.")


if __name__ == "__main__":
    main()
