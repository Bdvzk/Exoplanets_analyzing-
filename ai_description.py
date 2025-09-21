# ai_description.py

from openai import OpenAI

client = OpenAI(api_key="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")

def describe_exoplanet(row, language="pl"):
    prompt = (
        f"Opisz egzoplanetę na podstawie danych:\n"
        f"- ID: {row.get('kepid', 'brak')}\n"
        f"- Promień: {row['koi_prad']} R⊕\n"
        f"- Okres orbitalny: {row['koi_period']} dni\n"
        f"- Głębokość tranzytu: {row['koi_depth']} ppm\n"
        f"- Czas trwania tranzytu: {row['koi_duration']} godz.\n"
        f"- Predykcja modelu: {'egzoplaneta' if row['prediction'] == 1 else 'fałszywy pozytyw'}\n"
        f"- Możliwość życia: {row['habitable']}\n\n"
        f"Stwórz krótki, naukowy opis tej planety w języku {'polskim' if language == 'pl' else 'angielskim'}."
    )

    try:
        chat_completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Błąd podczas generowania opisu: {str(e)}"
