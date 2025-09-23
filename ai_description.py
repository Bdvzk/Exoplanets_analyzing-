import requests


def describe_exoplanet(row, language="pl"):
    prompt = (
        f"Opisz egzoplanetę na podstawie danych:\n"
        f"- ID: {row.get('kepid', 'brak')}\n"
        f"- Promień: {row.get('koi_prad', 'brak')} R⊕\n"
        f"- Okres orbitalny: {row.get('koi_period', 'brak')} dni\n"
        f"- Głębokość tranzytu: {row.get('koi_depth', 'brak')} ppm\n"
        f"- Czas trwania tranzytu: {row.get('koi_duration', 'brak')} godz.\n"
        f"- Predykcja modelu: {'egzoplaneta' if row.get('prediction') == 1 else 'fałszywy pozytyw'}\n"
        f"- Możliwość życia: {row.get('habitable', 'nieznana')}\n\n"
        f"Stwórz krótki, naukowy opis tej planety w języku {'polskim' if language == 'pl' else 'angielskim'}."
    )

    headers = {
        "Authorization": "Bearer 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",
        "Content-Type": "application/json"
    }

    data = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        return clean_description(raw)
    except Exception as e:
        return f"Błąd podczas generowania opisu: {str(e)}"
def clean_description(text):
    for tag in ["<s>", "</s>", "[OUT]", "[/OUT]"]:
        text = text.replace(tag, "")
    return text.strip()
