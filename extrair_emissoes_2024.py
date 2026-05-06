import pandas as pd
import requests
import time

INPUT_FILE = "ids.xlsx"
OUTPUT_FILE = "emissoes_2024.csv"

URL = "https://registropublicodeemissoesapi.fgv.br/api/services/app/EmissionsChart/ChartDataParticipant"

HEADERS = {
    "Accept": "text/plain",
    "Content-Type": "application/json-patch+json",
    "Origin": "https://registropublicodeemissoes.fgv.br",
    "Referer": "https://registropublicodeemissoes.fgv.br/",
    "User-Agent": "Mozilla/5.0"
}


def extrair_emissoes(data_json):
    try:
        items = data_json["result"]["items"]

        escopo1 = 0
        escopo2 = 0
        escopo3 = 0

        for item in items:
            nome = item["context"]["name"].strip()

            for d in item["data"]:
                if d["year"] == 2024:
                    if "1" in nome:
                        escopo1 = d["value"]
                    elif "2" in nome:
                        escopo2 = d["value"]
                    elif "3" in nome:
                        escopo3 = d["value"]

        total = escopo1 + escopo2 + escopo3

        return escopo1, escopo2, escopo3, total

    except:
        return None, None, None, None


def main():
    print("LENDO IDs DO EXCEL...\n")

    df = pd.read_excel(INPUT_FILE)

    # 🔥 AJUSTE AQUI
    if "ID" in df.columns:
        id_col = "ID"
    else:
        id_col = df.columns[0]  # fallback automático

    print(f"Usando coluna: {id_col}\n")

    resultados = []
    total_ids = len(df)

    for i, row in df.iterrows():
        org_id = str(row[id_col]).split(".")[0].zfill(4)

        print(f"→ {org_id} ({i+1}/{total_ids})")

        try:
            payload = {
                "organizationId": int(org_id)
            }

            response = requests.post(URL, json=payload, headers=HEADERS, timeout=30)

            if response.status_code != 200:
                print(f"✖ erro HTTP {response.status_code}")
                continue

            data = response.json()

            if not data.get("success"):
                print("✖ resposta sem sucesso")
                continue

            e1, e2, e3, total = extrair_emissoes(data)

            if total == 0 or total is None:
                print("– sem dados 2024")
            else:
                print(f"✔ total: {total:,.2f}")

            resultados.append({
                "ID": org_id,
                "Escopo 1": e1,
                "Escopo 2": e2,
                "Escopo 3": e3,
                "Total 2024": total
            })

            time.sleep(0.5)

        except Exception as e:
            print(f"Erro {org_id}: {e}")

    print("\nSALVANDO RESULTADO...")

    df_out = pd.DataFrame(resultados)
    df_out.to_csv(OUTPUT_FILE, index=False)

    print("FINALIZADO 🚀")


if __name__ == "__main__":
    main()
