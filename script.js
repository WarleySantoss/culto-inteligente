// Mapeando os elementos da tela
const btnRecord = document.getElementById('btnRecord');
const btnPause = document.getElementById('btnPause');
const btnFinish = document.getElementById('btnFinish');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const transcriptionBox = document.getElementById('transcription-box');
const placeholder = document.getElementById('placeholder');

let isRecording = false;
let mediaRecorder;
let audioChunks = [];

// Ação do Botão Gravar
btnRecord.addEventListener('click', async (event) => {
    event.preventDefault(); // Impede recarregamento acidental da página

    if (!isRecording) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = []; 

            mediaRecorder.ondataavailable = event => {
                if (event.data.size > 0) audioChunks.push(event.data);
            };

            // O que fazer assim que o áudio parar de gravar
            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                const formData = new FormData();
                formData.append("arquivo", audioBlob, "gravacao.webm");

                console.log("1. Áudio empacotado. Enviando para o Python...");

                try {
                    const response = await fetch("/processar-audio", {
                        method: "POST",
                        body: formData
                    });
                    
                    const data = await response.json();
                    console.log("2. Resposta recebida da IA com sucesso!", data);
                    
                    // Salva na memória do navegador
                    localStorage.setItem("textoBruto", data.texto_bruto);
                    localStorage.setItem("textoIA", data.texto_ia);
                    
                    console.log("3. Dados salvos. Mudando de tela em 2 segundos...");
                    
                    // Aguarda 2 segundos para podermos ler o console, e então redireciona
                    setTimeout(() => {
                        window.location.assign("revisao.html");
                    }, 2000);
                    
                } catch (error) {
                    console.error("ERRO FATAL: Falha ao comunicar com o Python:", error);
                    statusText.innerText = "Erro ao processar áudio. Veja o console.";
                    statusText.style.color = "#dc3545";
                }
            };

            mediaRecorder.start();
            isRecording = true;

            statusDot.classList.add('recording');
            statusText.innerText = "Gravando áudio real do microfone...";
            statusText.style.color = "#dc3545";
            if (placeholder) placeholder.style.display = 'none';
            transcriptionBox.innerHTML = "<p style='color:#aaa; text-align:center; margin-top:20%;'>Captação de áudio em andamento. Fale no microfone...</p>";
            btnRecord.disabled = true;

        } catch (err) {
            alert("Erro ao acessar o microfone.");
            console.error(err);
        }
    }
});

// Ação do Botão Pausar
btnPause.addEventListener('click', (event) => {
    event.preventDefault();
    alert("A função de pausa será implementada na versão final.");
});

// Ação do Botão Finalizar
btnFinish.addEventListener('click', (event) => {
    event.preventDefault(); // Impede o "refresh" automático do botão

    if (isRecording && mediaRecorder.state !== "inactive") {
        isRecording = false;
        
        statusDot.classList.remove('recording');
        statusDot.style.backgroundColor = "#28a745";
        statusText.innerText = "Processando áudio. Aguarde a IA...";
        statusText.style.color = "#28a745";
        transcriptionBox.innerHTML = "<p style='color:#aaa; text-align:center; margin-top:20%;'>Aguarde, processando e enviando para o servidor...</p>";
        btnFinish.disabled = true;

        mediaRecorder.stop(); 
    }
});