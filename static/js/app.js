// Espera o DOM estar completamente carregado para executar o script
document.addEventListener('DOMContentLoaded', () => {

    // --- 1. Seletores de Elementos ---
    // Seleciona os elementos principais da interface
    const step1 = document.getElementById('step-1');
    const step2 = document.getElementById('step-2');
    const step3 = document.getElementById('step-3');

    const uploadForm = document.getElementById('upload-form');
    const convertBtn = document.getElementById('convert-btn');
    const fileInput = document.getElementById('file-input');
    const fileNamePreview = document.getElementById('file-name-preview');
    const uploadArea = document.getElementById('upload-area');
    const fileLabel = document.getElementById('file-label');

    // Elementos da Etapa 2 (Progresso)
    const statusMessage = document.getElementById('status-message');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const progressDetails = document.getElementById('progress-details');

    // Elementos da Etapa 3 (Resultado)
    const totalRecords = document.getElementById('total-records');
    const successRecords = document.getElementById('success-records');
    const errorRecords = document.getElementById('error-records');
    const errorsList = document.getElementById('errors-list');
    const errorsContent = document.getElementById('errors-content');
    const downloadBtn = document.getElementById('download-btn');
    const newConversionBtn = document.getElementById('new-conversion-btn');

    let currentTaskId = null; // Armazena o ID da tarefa de conversão

    // --- 2. Função de Controle de Etapas ---
    // (Conforme 'arquitetura_projeto.pdf')
    function showStep(stepNumber) {
        // Esconde todas as etapas
        [step1, step2, step3].forEach(step => {
            step.classList.add('hide');
            step.classList.remove('show');
        });

        // Mostra a etapa desejada
        const currentStep = document.getElementById(`step-${stepNumber}`);
        if (currentStep) {
            currentStep.classList.add('show');
            currentStep.classList.remove('hide');
        }
    }

    // --- 3. Validação de Formulário (Etapa 1) ---
    // Habilita/desabilita o botão "Converter"
    function validateForm() {
        const requiredInputs = uploadForm.querySelectorAll('input[required]');
        let allValid = true;

        // Verifica se todos os campos 'required' estão preenchidos
        requiredInputs.forEach(input => {
            if (!input.value.trim()) {
                allValid = false;
            }
        });

        // Verifica se o arquivo foi selecionado
        if (fileInput.files.length === 0) {
            allValid = false;
        }

        convertBtn.disabled = !allValid;
    }

    // Adiciona ouvintes de evento para validar em tempo real
    uploadForm.addEventListener('input', validateForm);
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            fileNamePreview.textContent = fileInput.files[0].name;
            fileLabel.textContent = "Arquivo Selecionado:";
        } else {
            fileNamePreview.textContent = "";
            fileLabel.textContent = "Clique ou arraste o arquivo (.csv ou .xlsx) aqui";
        }
        validateForm();
    });

    // --- 4. Drag and Drop de Arquivo (Opcional do 'workflow_conversao.pdf') ---
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        // Pega o arquivo do 'drop' e o define no input
        if (e.dataTransfer.files.length > 0) {
            // Valida a extensão (simples)
            const file = e.dataTransfer.files[0];
            const allowedTypes = ['text/csv', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];
            if (allowedTypes.includes(file.type) || file.name.endsWith('.csv') || file.name.endsWith('.xlsx')) {
                fileInput.files = e.dataTransfer.files;
                // Dispara o evento 'change' para atualizar a UI
                fileInput.dispatchEvent(new Event('change'));
            } else {
                alert('Tipo de arquivo não permitido. Use .csv ou .xlsx');
            }
        }
    });

    // --- 5. Envio do Formulário (AJAX) ---
    // (Conforme 'arquitetura_projeto.pdf')
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault(); // Impede o recarregamento da página

        // Vai para a etapa 2 (Processamento)
        showStep(2);
        resetProgress();

        // Coleta os dados do formulário
        const formData = new FormData(uploadForm);

        try {
            // Envia os dados para a rota /upload
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Falha no upload. O servidor respondeu com erro.');
            }

            const data = await response.json();
            
            if (data.task_id) {
                currentTaskId = data.task_id;
                // Inicia a verificação de status (Polling)
                checkStatus(currentTaskId);
            } else {
                throw new Error('Resposta inválida do servidor (sem task_id).');
            }

        } catch (error) {
            console.error('Erro no upload:', error);
            showError('Erro crítico ao iniciar a conversão. Tente novamente.');
            showStep(1); // Volta para a Etapa 1
        }
    });

    // --- 6. Verificação de Status (Polling) ---
    // (Conforme 'arquitetura_projeto.pdf')
    function checkStatus(taskId) {
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/status/${taskId}`);
                if (!response.ok) {
                    throw new Error('Servidor não respondeu ao status.');
                }
                
                const data = await response.json();

                // Atualiza a barra de progresso
                progressFill.style.width = data.progress + '%';
                progressText.textContent = data.progress + '%';
                statusMessage.textContent = data.message;
                progressDetails.textContent = data.details || '';

                // Verifica se a conversão foi concluída
                if (data.status === 'completed') {
                    clearInterval(interval); // Para o polling
                    showResults(data); // Exibe os resultados
                    showStep(3); // Vai para a etapa 3
                }

                // Verifica se houve erro
                if (data.status === 'error') {
                    clearInterval(interval);
                    showError(data.message);
                    showStep(3); // Vai para a etapa 3 para mostrar o erro
                }

            } catch (error) {
                console.error('Erro no polling:', error);
                clearInterval(interval); // Para o polling em caso de falha de rede
                showError('Erro de comunicação. Não foi possível obter o status.');
                showStep(1);
            }
        }, 1000); // Verifica a cada 1 segundo
    }

    // --- 7. Exibição de Resultados (Etapa 3) ---
    function showResults(data) {
        totalRecords.textContent = data.total_records || 0;
        successRecords.textContent = data.success_records || 0;
        errorRecords.textContent = data.error_records || 0;

        if (data.error_records > 0 && data.error_details) {
            errorsContent.textContent = data.error_details;
            errorsList.classList.remove('hide');
        } else {
            errorsList.classList.add('hide');
            errorsContent.textContent = '';
        }

        // Configura o botão de download
        if (data.filename) {
            downloadBtn.disabled = false;
            downloadBtn.onclick = () => {
                window.location.href = `/download/${data.filename}`;
            };
        } else {
            // Se não houver arquivo (erro total), desabilita o download
            downloadBtn.disabled = true;
        }
    }

    // Função para mostrar erro crítico na Etapa 3
    function showError(message) {
        totalRecords.textContent = '0';
        successRecords.textContent = '0';
        errorRecords.textContent = 'N/A';
        errorsContent.textContent = `Erro Crítico: ${message}`;
        errorsList.classList.remove('hide');
        downloadBtn.disabled = true;
    }

    // --- 8. Botão "Nova Conversão" ---
    // (Conforme 'arquitetura_projeto.pdf')
    newConversionBtn.addEventListener('click', () => {
        // Reseta o formulário e a UI
        uploadForm.reset();
        fileNamePreview.textContent = '';
        fileLabel.textContent = "Clique ou arraste o arquivo (.csv ou .xlsx) aqui";
        convertBtn.disabled = true;
        currentTaskId = null;
        resetProgress();
        
        // Volta para a Etapa 1
        showStep(1);
    });

    // Função para resetar a barra de progresso
    function resetProgress() {
        statusMessage.textContent = 'Iniciando conversão...';
        progressFill.style.width = '0%';
        progressText.textContent = '0%';
        progressDetails.textContent = '';
    }
});