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
        // Esta função verifica TODOS os inputs com 'required'
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
        // Pega a <option> que foi selecionada
        const selectedOption = configSelector.options[configSelector.selectedIndex];

        // Lê os dados de Inscrição e Razão Social do CSV
        const razao = selectedOption.getAttribute('data-razao') || '';
        const inscricao = selectedOption.getAttribute('data-inscricao') || '';

        // Preenche os campos de Inscrição e Razão
        razaoInput.value = razao;
        inscricaoInput.value = inscricao;

        // --- Nova Lógica de Data/Hora ---
        // Calcula o mês anterior e o ano corrente
        const now = new Date();
        now.setMonth(now.getMonth() - 1);

        const targetYear = now.getFullYear();
        const targetMonth = now.getMonth() + 1;

        // Preenche os campos de Mês e Ano (permitindo edição)
        mesInput.value = targetMonth;
        anoInput.value = targetYear;

        // Limpa o Código de Serviço para preenchimento manual
        codigoServicoInput.value = '';

        validateForm();
    });
    // --- FIM DA LÓGICA DO DROPDOWN ---


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
                if (!response.ok) {
                    throw new Error('Servidor não respondeu ao status.');
                }

                const data = await response.json();

                // Atualiza a barra de progresso
                progressFill.style.width = data.progress + '%';
                progressText.textContent = data.progress + '%';
                statusMessage.textContent = data.message;
                progressDetails.textContent = data.details || '';

                if (data.status === 'completed') {
                    clearInterval(interval);
                    showResults(data);
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

    // --- 7. Exibição de Resultados (Etapa 3) ---
    function showResults(data) {
        
        // --- INÍCIO DA CORREÇÃO ---
        // O backend (Python) envia 'total', 'success' e 'errors'.
        // O JS estava esperando 'total_records', 'success_records', etc.
        totalRecords.textContent = data.total || 0;
        successRecords.textContent = data.success || 0;
        errorRecords.textContent = data.errors || 0;

        // --- MELHORIA NA EXIBIÇÃO DE ERROS ---
        // O 'error_details' é um Array de objetos. Precisamos formatá-lo
        // para exibição, em vez de mostrar [object Object].
        if (data.errors > 0 && data.error_details && Array.isArray(data.error_details)) {
            let errorString = "";
            // Itera sobre cada item de erro retornado pelo backend
            data.error_details.forEach(item => {
                // Formata: "Linha X: [Erro 1, Erro 2]"
                errorString += `Linha ${item.line}: ${item.errors.join(', ')}\n`;
            });
            errorsContent.textContent = errorString;
            errorsList.classList.remove('hide');
        } else {
            errorsList.classList.add('hide');
            errorsContent.textContent = '';
        }
        // --- FIM DA CORREÇÃO E MELHORIA ---

        if (data.filename) {
            downloadBtn.disabled = false;
            downloadBtn.onclick = () => {
                window.location.href = `/download/${data.filename}`;
            };
        } else {
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
    newConversionBtn.addEventListener('click', () => {
        uploadForm.reset();
        fileNamePreview.textContent = '';
        fileLabel.textContent = "Clique ou arraste o arquivo (.csv ou .xlsx) aqui";
        convertBtn.disabled = true;
        currentTaskId = null;
        resetProgress();
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