import asyncio
from playwright.async_api import async_playwright

INPUT_FILE = "ids.txt"
OUTPUT_FILE = "emissoes_2024.csv"

URL = "https://registropublicodeemissoesapi.fgv.br/api/services/app/EmissionsChart/ChartDataParticipant"


def extrair_emissoes(data):
    try:
        items = data["result"]["items"]

        e1 = e2 = e3 = 0

        for item in items:
            nome = item["context"]["name"]

            for d in item["data"]:
                if d["year"] == 2024:
                    if "1" in nome:
                        e1 = d["value"]
                    elif "2" in nome:
                        e2 = d["value"]
                    elif "3" in nome:
                        e3 = d["value"]

        return e1, e2, e3, e1 + e2 + e3

    except:
        return None, None, None, None


async def main():
    print("LENDO IDS...\n")

    with open(INPUT_FILE) as f:
        ids = [i.strip() for i in f if i.strip()]

    resultados = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )

        request = context.request

        for i, org_id in enumerate(ids):
            org_id = org_id.zfill(4)

            print(f"→ {org_id} ({i+1}/{len(ids)})")

            try:
                response = await request.post(
                    URL,
                    data={
                        "organizationId": int(org_id)
                    }
                )

                if response.status != 200:
                    print("✖ erro HTTP")
                    continue

                data = await response.json()

                if not data.get("success"):
                    print("✖ sem sucesso")
                    continue

                e1, e2, e3, total = extrair_emissoes(data)

                if total:
                    print(f"✔ total: {total:,.2f}")
                else:
                    print("– sem dados")

                resultados.append(f"{org_id},{e1},{e2},{e3},{total}")

                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"Erro {org_id}: {e}")

        await browser.close()

    print("\nSALVANDO...")

    with open(OUTPUT_FILE, "w") as f:
        f.write("ID,Escopo1,Escopo2,Escopo3,Total2024\n")
        f.write("\n".join(resultados))

    print("FINALIZADO 🚀")


asyncio.run(main())
