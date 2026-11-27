from app.rag import chunk


def test_chunk_respeita_tamanho_e_nao_perde_texto():
    texto = "\n\n".join(f"paragrafo {i} " * 20 for i in range(10))
    partes = chunk(texto, size=500)
    assert all(len(p) <= 500 for p in partes)
    assert "".join(partes).replace("\n", "") == texto.replace("\n", "")


def test_chunk_texto_vazio():
    assert chunk("") == []
