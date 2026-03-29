const textoBruto = document.getElementById('texto-bruto');
const textoIA = document.getElementById('texto-ia');
const temaEnsino = document.getElementById('tema-ensino');
const btnSalvar = document.getElementById('btnSalvar');

window.onload = () => {
    textoBruto.value = localStorage.getItem("textoBruto") || "";
    textoIA.value = localStorage.getItem("textoIA") || "";
};

btnSalvar.addEventListener('click', async () => {
    const tema = temaEnsino.value.trim();
    
    if (!tema) {
        alert("Por favor, digite um tema para o ensino antes de salvar!");
        return;
    }

    btnSalvar.disabled = true;
    btnSalvar.innerText = "⏳ Salvando...";

    const dados = {
        tema: tema,
        texto_bruto: textoBruto.value,
        texto_corrigido: textoIA.value
    };

    try {
        const response = await fetch("http://127.0.0.1:8000/salvar-ensino", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(dados)
        });

        const result = await response.json();
        
        if (result.status === "sucesso") {
            alert("✅ " + result.mensagem);
            localStorage.clear();
            window.location.href = "index.html";
        }
    } catch (error) {
        console.error("Erro ao salvar:", error);
        alert("Erro ao conectar com o servidor.");
        btnSalvar.disabled = false;
        btnSalvar.innerText = "💾 Salvar e Finalizar Ensino";
    }
});