import pandas as pd
import time
from curl_cffi import requests  # 🔥 IMPORTANTE

INPUT_FILE = "ids.xlsx"
OUTPUT_FILE = "emissoes_2024.xlsx"

URL = "https://registropublicodeemissoesapi.fgv.br/api/services/app/EmissionsChart/ChartDataParticipant"

def extrair_dados(org_id):
    try:
        response = requests.post(
            URL,
            impersonate="chrome",  # 🔥 resolve handshake
            headers={
                "Accept": "text/plain",
                "Content-Type": "application/json-patch+json",
                "Origin": "https://registropublicodeemissoes.fgv.br",
                "Referer": "https://registropublicodeemissoes.fgv.br/"
            },
            json={"organizationId": int(org_id)},
            timeout=30
        )

        if response.status_code != 200:
            print(f"✖ {org_id} status {response.status_code}")
            return None

        data = response.json()
        charts = data.get("result", {}).get("charts", [])

        if not charts:
            return None

        escopo1 = None
        escopo2 = None
        escopo3 = None

        for chart in charts:
            name = chart.get("name", "").lower()

            for serie in chart.get("series", []):
                for point in serie.get("data", []):

                    if str(point.get("year")) == "2024":
                        valor = point.get("value")

                        if "escopo 1" in name:
                            escopo1 = valor

                        elif "escopo 2" in name:
                            if escopo2 is None or valor > escopo2:
                                escopo2 = valor

                        elif "escopo 3" in name:
                            escopo3 = valor

        if escopo1 is None and escopo2 is None and escopo3 is None:
            return None

        total = (escopo1 or 0) + (escopo2 or 0) + (escopo3 or 0)

        return {
            "Escopo 1": escopo1,
            "Escopo 2": escopo2,
            "Escopo 3": escopo3,
            "Total 2024": total
        }

    except Exception as e:
        print(f"Erro {org_id}: {e}")
        return None


def main():
    print("📥 LENDO IDs...\n")

    df = pd.read_excel(INPUT_FILE)
    ids = df.iloc[:, 0].astype(str).str.zfill(4).tolist()

    resultados = []
    total_ids = len(ids)

    for i, org_id in enumerate(ids, 1):
        print(f"🔎 {org_id} ({i}/{total_ids})")

        dados = extrair_dados(org_id)

        if dados:
            print(f"✔ {org_id} OK")
            resultados.append({
                "ID": org_id,
                **dados
            })
        else:
            print(f"– {org_id} sem dados")

        time.sleep(0.4)

    df_final = pd.DataFrame(resultados)
    df_final.to_excel(OUTPUT_FILE, index=False)

    print("\n✅ FINALIZADO!")


if __name__ == "__main__":
    main()
