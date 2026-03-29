window.onload = async () => {
    const listaDoc = document.getElementById('lista-historico');
    const campoBusca = document.getElementById('busca-ensino'); // Pega a barra de pesquisa

    try {
        const response = await fetch("http://127.0.0.1:8000/listar-ensinos");
        const ensinos = await response.json();
        
        listaDoc.innerHTML = ""; 

        if (ensinos.length === 0) {
            listaDoc.innerHTML = "<p style='color: #888; text-align: center;'>Nenhum ensino registrado ainda.</p>";
            return;
        }

        ensinos.forEach(ensino => {
            const item = document.createElement('div');
            item.className = 'card-ensino'; // Classe para ajudar na busca
            item.style = `
                background: #1e1e1e; 
                padding: 15px; 
                border-radius: 10px; 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
                border-left: 5px solid #ffc107;
            `;

            // Arruma a barra do Windows (\) para a barra da Web (/)
            const caminhoCorrigido = ensino.pdf.replace(/\\/g, '/');

            item.innerHTML = `
                <div>
                    <strong style="color: white; font-size: 1.1rem; display: block;">${ensino.tema}</strong>
                    <small style="color: #aaa;">📅 ${ensino.data}</small>
                </div>
                <div style="display: flex; gap: 10px;">
                    <a href="http://127.0.0.1:8000/${caminhoCorrigido}" target="_blank" class="btn btn-success">
                       📄 Ver PDF
                    </a>
                    <button onclick="deletarEnsino(${ensino.id})" class="btn btn-danger">
                       🗑️ Excluir
                    </button>
                </div>
            `;
            listaDoc.appendChild(item);
        });

       // ==========================================
        // ESTATÍSTICAS DINÂMICAS (Resumo do Mês)
        // ==========================================
        const statsUltimo = document.getElementById('stats-ultimo');
        const statsTotal = document.getElementById('stats-total');
        const statsIA = document.getElementById('stats-ia');

        // Atualiza a quantidade e a data do último
        if (ensinos.length > 0) {
            statsTotal.innerHTML = `<strong>Cultos gravados:</strong> ${ensinos.length}`;
            // Como ordenamos por ID DESC no Python, o ensinos[0] é sempre o mais recente!
            statsUltimo.innerHTML = `<strong>Último ensino:</strong> ${ensinos[0].data}`; 
        } else {
            statsTotal.innerHTML = `<strong>Cultos gravados:</strong> 0`;
            statsUltimo.innerHTML = `<strong>Último ensino:</strong> Nenhum`;
        }

        // Verifica se a IA (Servidor Python) está online
        try {
            const res = await fetch("http://127.0.0.1:8000/");
            if (res.ok) {
                statsIA.innerHTML = `<strong>Status da IA:</strong> Online 🟢`;
            } else {
                statsIA.innerHTML = `<strong>Status da IA:</strong> Instável 🟠`;
            }
        } catch {
            statsIA.innerHTML = `<strong>Status da IA:</strong> Offline 🔴`;
        }

        // SISTEMA DE BUSCA EM TEMPO REAL
        if (campoBusca) {
            campoBusca.addEventListener('input', (evento) => {
                const termoBuscado = evento.target.value.toLowerCase();
                const cards = document.querySelectorAll('.card-ensino');

                cards.forEach(card => {
                    const titulo = card.querySelector('strong').innerText.toLowerCase();
                    if (titulo.includes(termoBuscado)) {
                        card.style.display = 'flex';
                    } else {
                        card.style.display = 'none';
                    }
                });
            });
        }

    } catch (error) {
        console.error("Erro ao carregar histórico:", error);
        listaDoc.innerHTML = "<p style='color: #ff4444; text-align: center;'>Erro ao conectar com o banco de dados.</p>";
    }
}; // <-- FIM DO WINDOW.ONLOAD (Isso é crucial!)


// ==========================================
// FUNÇÃO GLOBAL DE EXCLUSÃO (Tem que ficar fora do window.onload)
// ==========================================
async function deletarEnsino(id) {
    if (!confirm("Tem certeza que deseja excluir este ensino permanentemente?")) {
        return;
    }

    try {
        const response = await fetch(`http://127.0.0.1:8000/deletar-ensino/${id}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (response.ok) {
            alert("🗑️ " + result.mensagem);
            window.location.reload(); // Recarrega a página para sumir com o card
        } else {
            alert("Erro ao excluir: " + result.detail);
        }
    } catch (error) {
        console.error("Erro na requisição de exclusão:", error);
        alert("Erro de conexão com o servidor. Verifique se o Python está rodando.");
    }
}

// Função para enviar texto para o Telão
async function projetarTexto() {
    const texto = document.getElementById('texto-teste-telao').value;
    
    await fetch("http://127.0.0.1:8000/projetar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto: texto })
    });
}

// Função para apagar o telão (manda um texto vazio ou um ponto)
async function limparTelao() {
    await fetch("http://127.0.0.1:8000/projetar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto: " " })
    });
}