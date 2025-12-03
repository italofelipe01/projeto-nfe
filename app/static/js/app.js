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
    const downloadErrorsBtn = document.getElementById('download-errors-btn'); // NOVO
    const newConversionBtn = document.getElementById('new-conversion-btn');

    // --- NOVOS SELETORES DO RPA ---
    const rpaSection = document.getElementById('rpa-section');
    const btnRunRPA = document.getElementById('btnRunRPA');
    const rpaStatusText = document.getElementById('rpa-status-text');
    const rpaLogs = document.getElementById('rpa-logs');
    const rpaModeSelector = document.getElementById('rpaModeSelector'); // NOVO

    // Seletores dos campos do formulário
    const configSelector = document.getElementById('config-selector');
    const inscricaoInput = document.getElementById('inscricao_municipal');
    const cnpjInput = document.getElementById('cnpj_tomador');
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
        const cnpj = selectedOption.getAttribute('data-cnpj') || '';

        razaoInput.value = razao;
        inscricaoInput.value = inscricao;
        cnpjInput.value = cnpj;

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

        // Configura botão de download de SUCESSO
        if (data.filename) {
            downloadBtn.disabled = false;
            downloadBtn.onclick = () => {
                window.location.href = `/download/${data.filename}`;
            };
        } else {
            downloadBtn.disabled = true;
        }

        // Configura botão de download de ERROS (NOVO)
        if (data.error_filename) {
            downloadErrorsBtn.style.display = 'block';
            downloadErrorsBtn.onclick = () => {
                window.location.href = `/download/${data.error_filename}`;
            };
        } else {
            downloadErrorsBtn.style.display = 'none';
        }

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
        const selectedMode = rpaModeSelector.value; // Pega valor do Select
        const isDev = selectedMode === 'dev';
        const statusSpan = rpaStatusText;
        const logsDiv = rpaLogs;
        const btn = document.getElementById('btnRunRPA');

        // UI Feedback inicial
        logsDiv.style.display = 'block';
        statusSpan.innerText = "⏳ Solicitando execução...";
        statusSpan.className = "text-info";
        
        // Desabilita botão
        btn.disabled = true;

        try {
            const response = await fetch('/rpa/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    filename: filename,
                    inscricao_municipal: inscricao,
                    mode: isDev ? 'dev' : 'prod'
                }),
            });

            const data = await response.json();

            if (response.ok && data.success && data.task_id) {
                statusSpan.innerText = "🚀 " + data.message;
                // Inicia polling do RPA
                pollRPAStatus(data.task_id);
            } else {
                const errorMsg = data.message || "Erro desconhecido";
                statusSpan.innerText = "❌ " + errorMsg;
                statusSpan.className = "text-danger";
                btn.disabled = false;
            }

        } catch (error) {
            console.error('RPA Error:', error);
            statusSpan.innerText = "❌ Erro de comunicação.";
            statusSpan.className = "text-danger";
            btn.disabled = false;
        }
    }

    function pollRPAStatus(taskId) {
        const statusSpan = rpaStatusText;
        const btn = document.getElementById('btnRunRPA');

        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/rpa/status/${taskId}`);
                if (!res.ok) throw new Error("Erro ao consultar status RPA");

                const statusData = await res.json();

                // Atualiza mensagem na tela
                statusSpan.innerText = `🤖 ${statusData.message}`;

                // Verifica conclusão
                if (statusData.success !== null) { // true ou false (não null)
                    clearInterval(interval);
                    btn.disabled = false;

                    if (statusData.success) {
                        statusSpan.className = "text-success";
                        statusSpan.innerText = "✅ " + statusData.message;
                    } else {
                        statusSpan.className = "text-danger";
                        statusSpan.innerText = "❌ " + statusData.message + (statusData.details ? ` (${statusData.details})` : "");
                    }
                }

            } catch (err) {
                console.error(err);
                statusSpan.innerText = "⚠️ Erro ao atualizar status.";
                // Não para o polling imediatamente, pois pode ser intermitência
            }
        }, 2000); // Consulta a cada 2 segundos
    }

    // --- 9. Botão "Nova Conversão" ---
    newConversionBtn.addEventListener('click', () => {
        // Reseta o formulário HTML
        uploadForm.reset();

        // Reseta estados visuais manuais
        fileNamePreview.textContent = '';
        fileLabel.textContent = "Clique ou arraste o arquivo (.csv ou .xlsx) aqui";

        // Limpa o valor do input de arquivo para permitir o re-upload do mesmo arquivo
        fileInput.value = '';

        // Reseta variáveis de controle
        convertBtn.disabled = true;
        currentTaskId = null;
        
        // Reseta UI do RPA e Erros
        rpaSection.style.display = 'none';
        rpaLogs.style.display = 'none';
        downloadErrorsBtn.style.display = 'none'; // Esconde botão de erros
        
        resetProgress();
        showStep(1);

        // Garante que o estado do botão "Converter" está sincronizado com o form vazio
        validateForm();
    });

    function resetProgress() {
        statusMessage.textContent = 'Iniciando conversão...';
        progressFill.style.width = '0%';
        progressText.textContent = '0%';
        progressDetails.textContent = '';
    }
});