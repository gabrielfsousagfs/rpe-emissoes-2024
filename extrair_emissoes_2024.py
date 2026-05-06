import pandas as pd
import requests
import time

INPUT_FILE = "ids.xlsx"
OUTPUT_FILE = "emissoes_2024.xlsx"

URL = "https://registropublicodeemissoesapi.fgv.br/api/services/app/EmissionsChart/ChartDataParticipant"

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

def extrair_dados(org_id):
    payload = {
        "organizationId": int(org_id)
    }

    try:
        response = requests.post(URL, json=payload, headers=HEADERS, timeout=30)

        if response.status_code != 200:
            print(f"✖ {org_id} status {response.status_code}")
            return None

        data = response.json()

        # Caminho esperado da resposta
        charts = data.get("result", {}).get("charts", [])

        if not charts:
            return None

        escopo1 = None
        escopo2 = None
        escopo3 = None

        for chart in charts:
            name = chart.get("name", "").lower()

            series = chart.get("series", [])

            for serie in series:
                for point in serie.get("data", []):
                    if str(point.get("year")) == "2024":
                        valor = point.get("value")

                        if "escopo 1" in name:
                            escopo1 = valor

                        elif "escopo 2" in name:
                            # pega o maior se tiver mais de um (market/location)
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
    print("📥 LENDO IDs DO EXCEL...\n")

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
            print(f"– {org_id} sem dados 2024")

        time.sleep(0.3)  # evita bloqueio

    print("\n💾 SALVANDO RESULTADO...")

    df_final = pd.DataFrame(resultados)
    df_final.to_excel(OUTPUT_FILE, index=False)

    print(f"\n✅ FINALIZADO! Arquivo gerado: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
