import sqlite3

print("=== 🧹 Faxina Geral no Acervo de Louvores ===")

# Conecta no seu banco de dados
conn = sqlite3.connect('estudos.db')
cursor = conn.cursor()

try:
    # 1. Apaga todas as músicas da tabela
    cursor.execute("DELETE FROM louvores")
    
    # 2. Zera o contador de IDs (para voltar do 1)
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='louvores'")
    
    conn.commit()
    print("✅ SUCESSO! Banco de dados limpo.")
    print("Todas as músicas foram apagadas e o seu acervo está 100% zerado!")

except Exception as e:
    print(f"❌ Ocorreu um erro: {e}")

finally:
    conn.close()


    # comando para rodar python limpar-musicas.py