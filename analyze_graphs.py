from datetime import datetime

def gerar_relatorio_kanban():
    # Simulação dos dados que viriam do Notion (substitua por integração real, se houver)
    status_counts = {
        "Em Planejamento": 2,
        "Ideias para Post": 2,
        "Relatório": 1,
        "Em Criação": 1,
        "Ideias Aprovadas": 1
    }

    tipo_post_counts = {
        "Sem Tipo de post": 5,
        "Vídeo": 1,
        "Reels": 1
    }

    alteracoes_detectadas = "Nenhuma mudança significativa detectada."

    insights = [
        "⚠️ Poucos cards em 'Em Criação'. Considere mover ideias aprovadas para esta etapa.",
        "📌 5 cards estão sem tipo de post definido.",
        "🎨 Nenhum carrossel ou foto planejado. Considere diversificar os formatos de conteúdo."
    ]

    hoje = datetime.now().strftime("%d/%m/%Y")

    # Construção do relatório em markdown
    relatorio = f"""📊 **Relatório de Análise de Kanban - {hoje}**

### 🔍 Distribuição por Status:"""

    for status, count in status_counts.items():
        relatorio += f"\n- {status}: {count} card(s)"

    relatorio += "\n\n### 🧩 Distribuição por Tipo de Post:"
    for tipo, count in tipo_post_counts.items():
        relatorio += f"\n- {tipo}: {count} card(s)"

    relatorio += f"\n\n### 🔁 Alterações detectadas desde a última análise:\n{alteracoes_detectadas}"

    relatorio += "\n\n### 🧠 Insights Automáticos:"
    for insight in insights:
        relatorio += f"\n{insight}"

    return relatorio

# Teste local (opcional)
if __name__ == "__main__":
    print(gerar_relatorio_kanban())
