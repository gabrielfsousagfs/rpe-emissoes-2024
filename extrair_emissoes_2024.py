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


# ✅ ENDPOINTS CORRETOS
async def inicializar_sessao(request, org_id):
    try:
        # 1️⃣ GetYearRange (CORRETO)
        await request.get(
            f"{BASE_URL}/api/services/app/EstatisticaPublica/GetYearRangeByOrganization?organizationId={int(org_id)}",
            headers=HEADERS
        )

        # 2️⃣ GetAllScopes (CORRETO)
        await request.get(
            f"{BASE_URL}/api/services/app/EstatisticaPublica/GetAllScopes",
            headers=HEADERS
        )

        return True

    except Exception as e:
        print(f"Erro init {org_id}: {e}")
        return False


async def buscar_dados(request, org_id):
    payload = {
        "organizationId": int(org_id)
    }

    try:
        response = await request.post(
            f"{BASE_URL}/api/services/app/EmissionsChart/ChartDataParticipant",
            headers=HEADERS,
            data=json.dumps(payload)
        )

        if response.status != 200:
            print(f"✖ {org_id} status {response.status}")
            return None

        return await response.json()

    except Exception as e:
        print(f"Erro {org_id}: {e}")
        return None


# ✅ EXTRAÇÃO ROBUSTA
def extrair_2024(data):
    try:
        items = data["result"]["items"]

        esc1 = esc2 = esc3 = None

        for item in items:
            scope_id = item["context"]["id"]

            for d in item["data"]:
                if d["year"] == 2024:
                    if scope_id == 1:
                        esc1 = d["value"]
                    elif scope_id == 2:
                        esc2 = d["value"]
                    elif scope_id == 3:
                        esc3 = d["value"]

        return esc1, esc2, esc3

    except Exception as e:
        print("Erro parsing:", e)
        return None, None, None


async def main():
    print("INICIANDO...")

    with open(INPUT_FILE, "r") as f:
        ids = [linha.strip().zfill(4) for linha in f if linha.strip()]

    resultados = []

    async with async_playwright() as p:
        context = await p.request.new_context()

        total = len(ids)

        for i, org_id in enumerate(ids):
            print(f"→ {org_id} ({i+1}/{total})")

            # 🔑 inicialização correta
            ok = await inicializar_sessao(context, org_id)
            if not ok:
                print("✖ erro inicialização")
                continue

            data = await buscar_dados(context, org_id)

            if not data or not data.get("result"):
                print("✖ sem dados")
                continue

            esc1, esc2, esc3 = extrair_2024(data)

            if esc1 is None and esc2 is None and esc3 is None:
                print("– sem dados 2024")
                continue

            resultados.append({
                "id": org_id,
                "escopo_1": esc1,
                "escopo_2": esc2,
                "escopo_3": esc3,
                "total": (esc1 or 0) + (esc2 or 0) + (esc3 or 0)
            })

            await asyncio.sleep(0.3)

    print("SALVANDO RESULTADO...")

    df = pd.DataFrame(resultados)
    df.to_csv(OUTPUT_FILE, index=False)

    print("FINALIZADO 🚀")


if __name__ == "__main__":
    asyncio.run(main())
