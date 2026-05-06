import asyncio
import json
import pandas as pd
from playwright.async_api import async_playwright

INPUT_FILE = "ids.txt"
OUTPUT_FILE = "emissoes_2024.csv"

BASE_URL = "https://registropublicodeemissoesapi.fgv.br"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json-patch+json",
    "Origin": "https://registropublicodeemissoes.fgv.br",
    "Referer": "https://registropublicodeemissoes.fgv.br/",
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest"
}


async def inicializar_sessao(request, org_id):
    try:
        print(f"  🔹 INIT sessão para {org_id}")

        # 1️⃣ GetYearRange
        url1 = f"{BASE_URL}/api/services/app/EstatisticaPublica/GetYearRangeByOrganization?organizationId={int(org_id)}"
        r1 = await request.get(url1, headers=HEADERS)
        print(f"    GetYearRange status: {r1.status}")

        txt1 = await r1.text()
        print(f"    GetYearRange resposta (resumo): {txt1[:200]}")

        # 2️⃣ GetAllScopes
        url2 = f"{BASE_URL}/api/services/app/EstatisticaPublica/GetAllScopes"
        r2 = await request.get(url2, headers=HEADERS)
        print(f"    GetAllScopes status: {r2.status}")

        txt2 = await r2.text()
        print(f"    GetAllScopes resposta (resumo): {txt2[:200]}")

        return True

    except Exception as e:
        print(f"❌ Erro init {org_id}: {e}")
        return False


async def buscar_dados(request, org_id):
    payload = {
        "organizationId": int(org_id)
    }

    print(f"  🔹 POST ChartData para {org_id}")
    print(f"    Payload: {payload}")

    try:
        response = await request.post(
            f"{BASE_URL}/api/services/app/EmissionsChart/ChartDataParticipant",
            headers=HEADERS,
            data=json.dumps(payload)
        )

        print(f"    Status: {response.status}")

        text = await response.text()
        print(f"    Resposta (primeiros 500 chars):\n{text[:500]}\n")

        if response.status != 200:
            print(f"❌ status inválido")
            return None

        data = await response.json()

        # DEBUG estrutura
        if "result" not in data:
            print("❌ 'result' não encontrado na resposta")
            return None

        if "items" not in data["result"]:
            print("❌ 'items' não encontrado dentro de result")
            print(data["result"])
            return None

        print(f"    ✔ items encontrados: {len(data['result']['items'])}")

        return data

    except Exception as e:
        print(f"❌ Erro POST {org_id}: {e}")
        return None


def extrair_2024(data):
    try:
        items = data["result"]["items"]

        esc1 = esc2 = esc3 = None

        print("  🔹 EXTRAÇÃO")

        for item in items:
            scope_id = item["context"]["id"]
            print(f"    Escopo encontrado: {scope_id}")

            for d in item["data"]:
                if d["year"] == 2024:
                    print(f"      ✔ 2024 encontrado no escopo {scope_id}: {d['value']}")

                    if scope_id == 1:
                        esc1 = d["value"]
                    elif scope_id == 2:
                        esc2 = d["value"]
                    elif scope_id == 3:
                        esc3 = d["value"]

        print(f"    Resultado extração: S1={esc1}, S2={esc2}, S3={esc3}")

        return esc1, esc2, esc3

    except Exception as e:
        print("❌ Erro parsing:", e)
        return None, None, None


async def main():
    print("🚀 INICIANDO DEBUG COMPLETO...\n")

    with open(INPUT_FILE, "r") as f:
        ids = [linha.strip().zfill(4) for linha in f if linha.strip()]

    resultados = []

    async with async_playwright() as p:
        context = await p.request.new_context()

        total = len(ids)

        for i, org_id in enumerate(ids):
            print("\n" + "="*60)
            print(f"→ PROCESSANDO {org_id} ({i+1}/{total})")
            print("="*60)

            ok = await inicializar_sessao(context, org_id)
            if not ok:
                print("❌ falha na inicialização")
                continue

            data = await buscar_dados(context, org_id)

            if not data:
                print("❌ sem resposta válida")
                continue

            esc1, esc2, esc3 = extrair_2024(data)

            if esc1 is None and esc2 is None and esc3 is None:
                print("⚠️ SEM DADOS 2024 DETECTADO")
                continue

            resultados.append({
                "id": org_id,
                "escopo_1": esc1,
                "escopo_2": esc2,
                "escopo_3": esc3,
                "total": (esc1 or 0) + (esc2 or 0) + (esc3 or 0)
            })

            await asyncio.sleep(0.5)

    print("\n💾 SALVANDO RESULTADO...")

    df = pd.DataFrame(resultados)
    df.to_csv(OUTPUT_FILE, index=False)

    print("✅ FINALIZADO")


if __name__ == "__main__":
    asyncio.run(main())
