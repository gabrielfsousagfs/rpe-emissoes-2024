import requests
import time

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


def extrair_emissoes(data_json):
    try:
        items = data_json["result"]["items"]

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


def fazer_request(org_id, tentativas=3):
    for tentativa in range(tentativas):
        try:
            payload = {"organizationId": int(org_id)}

            response = requests.post(
                URL,
                json=payload,
                headers=HEADERS,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()

        except Exception as e:
            print(f"⚠️ erro tentativa {tentativa+1} para {org_id}")

        time.sleep(2)

    return None


def main():
    print("LENDO IDs...\n")

    with open(INPUT_FILE, "r") as f:
        ids = [linha.strip() for linha in f if linha.strip()]

    total_ids = len(ids)
    resultados = []

    for i, org_id in enumerate(ids):
        org_id = org_id.zfill(4)

        print(f"→ {org_id} ({i+1}/{total_ids})")

        data = fazer_request(org_id)

        if not data or not data.get("success"):
            print("✖ falha na API")
            continue

        e1, e2, e3, total = extrair_emissoes(data)

        if total:
            print(f"✔ total: {total:,.2f}")
        else:
            print("– sem dados 2024")

        resultados.append(f"{org_id},{e1},{e2},{e3},{total}")

        time.sleep(0.5)

    print("\nSALVANDO...")

    with open(OUTPUT_FILE, "w") as f:
        f.write("ID,Escopo1,Escopo2,Escopo3,Total2024\n")
        f.write("\n".join(resultados))

    print("FINALIZADO 🚀")


if __name__ == "__main__":
    main()
