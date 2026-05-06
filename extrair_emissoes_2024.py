import asyncio
import json
import pandas as pd
from playwright.async_api import async_playwright

INPUT_FILE = "ids.txt"
OUTPUT_FILE = "emissoes_2024.csv"

URL = "https://registropublicodeemissoesapi.fgv.br/api/services/app/EmissionsChart/ChartDataParticipant"

HEADERS = {
    "Accept": "text/plain",
    "Content-Type": "application/json-patch+json",
    "Origin": "https://registropublicodeemissoes.fgv.br",
    "Referer": "https://registropublicodeemissoes.fgv.br/",
    "User-Agent": "Mozilla/5.0"
}


async def buscar_dados(request, org_id):
    payload = {
        "organizationId": int(org_id)
    }

    try:
        response = await request.post(
            URL,
            headers=HEADERS,
            data=json.dumps(payload)  # 👈 CORREÇÃO AQUI
        )

        if response.status != 200:
            print(f"✖ {org_id} status {response.status}")
            return None

        data = await response.json()
        return data

    except Exception as e:
        print(f"Erro {org_id}: {e}")
        return None
    print(await response.text())

def extrair_2024(data):
    try:
        items = data["result"]["items"]

        escopo1 = None
        escopo2 = None
        escopo3 = None

        for item in items:
            nome = item["context"]["name"]

            for d in item["data"]:
                if d["year"] == 2024:
                    if "1" in nome:
                        escopo1 = d["value"]
                    elif "2" in nome:
                        escopo2 = d["value"]
                    elif "3" in nome:
                        escopo3 = d["value"]

        return escopo1, escopo2, escopo3

    except:
        return None, None, None


async def main():
    print("INICIANDO...")

    # Lê IDs
    with open(INPUT_FILE, "r") as f:
        ids = [linha.strip().zfill(4) for linha in f if linha.strip()]

    resultados = []

    async with async_playwright() as p:
        context = await p.request.new_context()

        total = len(ids)

        for i, org_id in enumerate(ids):
            print(f"→ {org_id} ({i+1}/{total})")

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
