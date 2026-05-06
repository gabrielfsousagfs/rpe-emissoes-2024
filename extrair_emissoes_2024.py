import requests
import time
import csv
import pandas as pd
from bs4 import BeautifulSoup

# ========================
# CONFIG
# ========================
INPUT_FILE = "ids.xlsx"
OUTPUT_FILE = "emissoes_2024.csv"
SLEEP = 0.3

BASE_URL = "https://registropublicodeemissoes.fgv.br/estatistica/estatistica-participantes/{}"

# ========================
# FUNÇÕES
# ========================

def parse_numero_br(valor):
    try:
        return float(valor.replace(".", "").replace(",", ".").strip())
    except:
        return None


def extrair_emissoes(html):
    soup = BeautifulSoup(html, "html.parser")

    tabela = soup.find("div", class_="container-table")
    if not tabela:
        return None

    linhas = tabela.find_all("tr")

    anos = []
    escopo1 = []
    escopo2 = []
    escopo3 = []

    for linha in linhas:
        texto = linha.get_text(strip=True)

        if "Ano" in texto:
            anos = [td.get_text(strip=True) for td in linha.find_all("td")]

        elif "Escopo 1" in texto:
            escopo1 = [td.get_text(strip=True) for td in linha.find_all("td")]

        elif "Escopo 2" in texto:
            escopo2 = [td.get_text(strip=True) for td in linha.find_all("td")]

        elif "Escopo   3" in texto or "Escopo 3" in texto:
            escopo3 = [td.get_text(strip=True) for td in linha.find_all("td")]

    if "2024" not in anos:
        return None

    idx = anos.index("2024")

    try:
        s1 = parse_numero_br(escopo1[idx]) if idx < len(escopo1) else None
        s2 = parse_numero_br(escopo2[idx]) if idx < len(escopo2) else None
        s3 = parse_numero_br(escopo3[idx]) if idx < len(escopo3) else None

        total = sum(filter(None, [s1, s2, s3]))

        return s1, s2, s3, total

    except:
        return None


# ========================
# MAIN
# ========================

def main():
    print("\nLENDO IDs DO EXCEL...\n")

    df = pd.read_excel(INPUT_FILE)

    if "ID" not in df.columns:
        raise Exception("O Excel precisa ter uma coluna chamada 'ID'")

    ids = df["ID"].astype(str).str.zfill(4).tolist()

    print(f"Total de IDs: {len(ids)}\n")

    with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["ID", "Escopo1_2024", "Escopo2_2024", "Escopo3_2024", "Total_2024"])

        for idx, participant_id in enumerate(ids, start=1):
            url = BASE_URL.format(participant_id)

            try:
                response = requests.get(url, timeout=10)

                if response.status_code != 200:
                    print(f"✖ {participant_id} sem página")
                    continue

                resultado = extrair_emissoes(response.text)

                if resultado:
                    s1, s2, s3, total = resultado
                    writer.writerow([participant_id, s1, s2, s3, total])
                    print(f"✔ {participant_id} OK ({idx}/{len(ids)})")
                else:
                    print(f"– {participant_id} sem dados 2024 ({idx}/{len(ids)})")

            except Exception as e:
                print(f"Erro {participant_id}: {e}")

            time.sleep(SLEEP)

    print(f"\nFINALIZADO → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
