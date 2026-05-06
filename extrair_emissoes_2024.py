import asyncio
import pandas as pd
from playwright.async_api import async_playwright

INPUT_FILE = "IDs para puxar emissões totais.xlsx"
OUTPUT_FILE = "emissoes_2024.csv"

MAX_RETRIES = 3


def parse_numero(valor):
    if not valor:
        return 0.0
    valor = valor.replace(".", "").replace(",", ".").strip()
    try:
        return float(valor)
    except:
        return 0.0


async def extrair_dados(page, id_participante):
    url = f"https://registropublicodeemissoes.fgv.br/estatistica/estatistica-participantes/{id_participante}"

    for tentativa in range(MAX_RETRIES):
        try:
            await page.goto(url, timeout=60000)
            await page.wait_for_selector("table", timeout=15000)

            anos = await page.locator("table thead tr:nth-child(1) td b").all_text_contents()

            if "2024" not in anos:
                print(f"⚠️ {id_participante} sem 2024")
                return None

            idx_2024 = anos.index("2024")

            escopo1 = await page.locator("tr.escopo1-color td").all_text_contents()
            escopo2 = await page.locator("tr.escopo2-color td").all_text_contents()
            escopo3 = await page.locator("tr.escopo3-color td").all_text_contents()

            e1 = parse_numero(escopo1[idx_2024]) if idx_2024 < len(escopo1) else 0
            e3 = parse_numero(escopo3[idx_2024]) if idx_2024 < len(escopo3) else 0

            # escopo 2 → pegar maior valor possível (segurança futura)
            e2 = 0
            if idx_2024 < len(escopo2):
                e2 = parse_numero(escopo2[idx_2024])

            total = e1 + e2 + e3

            return {
                "id": id_participante,
                "escopo1_2024": e1,
                "escopo2_2024": e2,
                "escopo3_2024": e3,
                "total_2024": total
            }

        except Exception as e:
            print(f"❌ Erro {id_participante} (tentativa {tentativa+1}): {e}")
            await asyncio.sleep(2)

    return None


async def main():
    df_ids = pd.read_excel(INPUT_FILE)

    ids = df_ids.iloc[:, 0].astype(str).str.zfill(4).tolist()

    resultados = []

    async with async_playwright() as p:
        print("🚀 Iniciando navegador...")

        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for i, id_ in enumerate(ids):
            print(f"➡️ {i+1}/{len(ids)} | ID {id_}")

            dados = await extrair_dados(page, id_)

            if dados:
                resultados.append(dados)

            # pequena pausa para evitar bloqueio
            await asyncio.sleep(0.5)

        await browser.close()

    df_final = pd.DataFrame(resultados)
    df_final.to_csv(OUTPUT_FILE, index=False)

    print("\n✅ FINALIZADO")
    print(f"📄 Arquivo: {OUTPUT_FILE}")
    print(f"📊 Total coletado: {len(df_final)} registros")


if __name__ == "__main__":
    asyncio.run(main())
