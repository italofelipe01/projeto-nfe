// Espera o DOM estar completamente carregado para executar o script
document.addEventListener('DOMContentLoaded', () => {

    // --- 1. Seletores de Elementos ---
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

    // --- NOVOS SELETORES DO RPA ---
    const rpaSection = document.getElementById('rpa-section');
    const btnRunRPA = document.getElementById('btnRunRPA');
    const rpaStatusText = document.getElementById('rpa-status-text');
    const rpaLogs = document.getElementById('rpa-logs');
    const devModeCheck = document.getElementById('devModeCheck');

    // Seletores dos campos do formulário
    const configSelector = document.getElementById('config-selector');
    const inscricaoInput = document.getElementById('inscricao_municipal');
    const mesInput = document.getElementById('mes');
    const anoInput = document.getElementById('ano');
    const razaoInput = document.getElementById('razao_social');
    const codigoServicoInput = document.getElementById('codigo_servico');

    let currentTaskId = null;

    // --- 2. Função de Controle de Etapas ---
    function showStep(stepNumber) {
        [step1, step2, step3].forEach(step => {
            step.classList.add('hide');
            step.classList.remove('show');
        });
        const currentStep = document.getElementById(`step-${stepNumber}`);
        if (currentStep) {
            currentStep.classList.add('show');
            currentStep.classList.remove('hide');
        }
    }

    // --- 3. Validação de Formulário (Etapa 1) ---
    function validateForm() {
        const requiredInputs = uploadForm.querySelectorAll('input[required]');
        let allValid = true;

        requiredInputs.forEach(input => {
            if (!input.value.trim()) {
                allValid = false;
            }
        });

        if (fileInput.files.length === 0) {
            allValid = false;
        }

        convertBtn.disabled = !allValid;
    }

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

    // --- 4. Drag and Drop de Arquivo ---
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

        if (e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            const allowedTypes = ['text/csv', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];
            if (allowedTypes.includes(file.type) || file.name.endsWith('.csv') || file.name.endsWith('.xlsx')) {
                fileInput.files = e.dataTransfer.files;
                fileInput.dispatchEvent(new Event('change'));
            } else {
                alert('Tipo de arquivo não permitido. Use .csv ou .xlsx');
            }
        }
    });

    // --- Lógica do Dropdown de Produção ---
    configSelector.addEventListener('change', () => {
        const selectedOption = configSelector.options[configSelector.selectedIndex];
        const razao = selectedOption.getAttribute('data-razao') || '';
        const inscricao = selectedOption.getAttribute('data-inscricao') || '';

        razaoInput.value = razao;
        inscricaoInput.value = inscricao;

        const now = new Date();
        now.setMonth(now.getMonth() - 1);
        const targetYear = now.getFullYear();
        const targetMonth = now.getMonth() + 1;

        mesInput.value = targetMonth;
        anoInput.value = targetYear;
        codigoServicoInput.value = '';

        validateForm();
    });

    // --- 5. Envio do Formulário (AJAX) ---
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        showStep(2);
        resetProgress();
        const formData = new FormData(uploadForm);

        try {
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
                checkStatus(currentTaskId);
            } else {
                throw new Error('Resposta inválida do servidor (sem task_id).');
            }

        } catch (error) {
            console.error('Erro no upload:', error);
            showError('Erro crítico ao iniciar a conversão. Tente novamente.');
            showStep(1);
        }
    });

    // --- 6. Verificação de Status (Polling) ---
    function checkStatus(taskId) {
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/status/${taskId}`);
                if (!response.ok) throw new Error('Servidor não respondeu ao status.');

                const data = await response.json();

                progressFill.style.width = data.progress + '%';
                progressText.textContent = data.progress + '%';
                statusMessage.textContent = data.message;
                progressDetails.textContent = data.details || '';

                if (data.status === 'completed') {
                    clearInterval(interval);
                    showResults(data);
                    
                    // --- GATILHO PARA RPA ---
                    // Se a conversão foi um sucesso, preparamos a área do robô
                    // usando os metadados salvos pelo backend (filename e inscricao)
                    if (data.success > 0) {
                        prepareRPA(data.filename, data.meta_inscricao);
                    }
                    
                    showStep(3);
                }

                if (data.status === 'error') {
                    clearInterval(interval);
                    showError(data.message);
                    showStep(3);
                }

            } catch (error) {
                console.error('Erro no polling:', error);
                clearInterval(interval);
                showError('Erro de comunicação. Não foi possível obter o status.');
                showStep(1);
            }
        }, 1000);
    }

    // --- 7. Exibição de Resultados ---
    function showResults(data) {
        totalRecords.textContent = data.total || 0;
        successRecords.textContent = data.success || 0;
        errorRecords.textContent = data.errors || 0;

        if (data.errors > 0 && data.error_details && Array.isArray(data.error_details)) {
            let errorString = "";
            data.error_details.forEach(item => {
                errorString += `Linha ${item.line}: ${item.errors.join(', ')}\n`;
            });
            errorsContent.textContent = errorString;
            errorsList.classList.remove('hide');
        } else {
            errorsList.classList.add('hide');
            errorsContent.textContent = '';
        }

        if (data.filename) {
            downloadBtn.disabled = false;
            downloadBtn.onclick = () => {
                window.location.href = `/download/${data.filename}`;
            };
        } else {
            downloadBtn.disabled = true;
        }
    }

    function showError(message) {
        totalRecords.textContent = '0';
        successRecords.textContent = '0';
        errorRecords.textContent = 'N/A';
        errorsContent.textContent = `Erro Crítico: ${message}`;
        errorsList.classList.remove('hide');
        downloadBtn.disabled = true;
        // Esconde RPA em caso de erro fatal
        rpaSection.style.display = 'none';
    }

    // --- 8. LÓGICA DO RPA (NOVO MÓDULO) ---
    function prepareRPA(filename, inscricao) {
        // Mostra a seção
        rpaSection.style.display = 'block';
        rpaLogs.style.display = 'none';
        btnRunRPA.disabled = false;
        
        // Remove listeners antigos clonando o botão (previne múltiplos cliques acumulados)
        const newBtn = btnRunRPA.cloneNode(true);
        btnRunRPA.parentNode.replaceChild(newBtn, btnRunRPA);
        
        // Adiciona o novo listener com os dados frescos (closure)
        newBtn.addEventListener('click', () => {
            executeRobot(filename, inscricao);
        });
    }

    async function executeRobot(filename, inscricao) {
        const isDev = devModeCheck.checked;
        const statusSpan = rpaStatusText;
        const logsDiv = rpaLogs;

        // UI Feedback inicial
        logsDiv.style.display = 'block';
        statusSpan.innerText = "⏳ Inicializando robô... Por favor, aguarde (não feche a janela).";
        statusSpan.className = "text-info";
        
        // Desabilita botão
        document.getElementById('btnRunRPA').disabled = true; // Re-seleciona o botão atualizado do DOM

        try {
            const response = await fetch('/rpa/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    filename: filename,
                    inscricao_municipal: inscricao, // O CAMPO CRÍTICO QUE FALTAVA
                    mode: isDev ? 'dev' : 'prod'
                }),
            });

            const data = await response.json();

            if (response.ok && data.success) {
                statusSpan.innerText = "✅ " + data.message;
                statusSpan.className = "text-success";
            } else {
                // Tratamento de erro vindo da API (ex: erro de login)
                const errorMsg = data.message || "Erro desconhecido";
                const details = data.details ? ` (${data.details})` : "";
                statusSpan.innerText = "❌ " + errorMsg + details;
                statusSpan.className = "text-danger";
            }

        } catch (error) {
            console.error('RPA Error:', error);
            statusSpan.innerText = "❌ Erro de comunicação com o servidor RPA.";
            statusSpan.className = "text-danger";
        } finally {
            // Reabilita o botão para permitir nova tentativa
            document.getElementById('btnRunRPA').disabled = false;
        }
    }

    // --- 9. Botão "Nova Conversão" ---
    newConversionBtn.addEventListener('click', () => {
        uploadForm.reset();
        fileNamePreview.textContent = '';
        fileLabel.textContent = "Clique ou arraste o arquivo (.csv ou .xlsx) aqui";
        convertBtn.disabled = true;
        currentTaskId = null;
        
        // Reseta UI do RPA
        rpaSection.style.display = 'none';
        rpaLogs.style.display = 'none';
        
        resetProgress();
        showStep(1);
    });

    function resetProgress() {
        statusMessage.textContent = 'Iniciando conversão...';
        progressFill.style.width = '0%';
        progressText.textContent = '0%';
        progressDetails.textContent = '';
    }
});