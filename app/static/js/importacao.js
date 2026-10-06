(() => {
    const form =
        document.getElementById(
            "import-form"
        );

    if (!form) {
        return;
    }

    const input =
        document.getElementById(
            "arquivo"
        );

    const fileName =
        document.getElementById(
            "arquivo-nome"
        );

    const submit =
        document.getElementById(
            "import-submit"
        );

    const statusBox =
        document.getElementById(
            "import-status"
        );

    const statusTitle =
        document.getElementById(
            "import-status-title"
        );

    const statusMessage =
        document.getElementById(
            "import-status-message"
        );

    const resultBox =
        document.getElementById(
            "import-result"
        );

    const cancelButton =
        document.getElementById(
            "cancel-import"
        );

    const confirmation =
        document.getElementById(
            "cancel-confirmation"
        );

    const continueButton =
        document.getElementById(
            "continue-import"
        );

    const confirmCancel =
        document.getElementById(
            "confirm-cancel"
        );

    const dropzone = form.querySelector('.upload-dropzone');
    const feedback = document.getElementById('arquivo-feedback');
    function validFile() {
        return input.files.length === 1 && /\.csv$/i.test(input.files[0].name);
    }
    function updateFileState(message = '') {
        const file = input.files[0];
        const valid = validFile();
        fileName.textContent = file ? file.name : 'Nenhum arquivo selecionado.';
        feedback.textContent = message || (file && !valid
            ? 'Arquivo inválido. Selecione um arquivo com extensão .csv.'
            : file ? 'Arquivo CSV selecionado. Pronto para iniciar a importação.' : '');
        input.setAttribute('aria-invalid', String(Boolean(message || (file && !valid))));
        dropzone.classList.toggle('has-file', valid);
        dropzone.classList.toggle('is-invalid', Boolean(message || (file && !valid)));
        submit.disabled = running || !valid || Boolean(message);
    }
    let pollingTimer = null;
    let running = false;

    let currentImportId = null;
    let currentStatusUrl = null;
    let currentCancelUrl = null;


    function br(value) {
        return new Intl.NumberFormat(
            "pt-BR"
        ).format(
            Number(value || 0)
        );
    }


    function setBusy(busy) {
        running = busy;

        submit.disabled =
            busy
            || !validFile();
        submit.textContent = busy ? 'Importando...' : 'Iniciar importação';
        form.setAttribute('aria-busy', String(busy));
        dropzone.classList.toggle('is-busy', busy);

        input.disabled =
            busy;
    }


    function showStatus(
        title,
        message
    ) {
        statusTitle.textContent =
            title;

        statusMessage.textContent =
            message;

        statusBox.hidden =
            false;
    }


    function hideStatus() {
        statusBox.hidden =
            true;
    }


    function showResult(data) {
        document.getElementById(
            "result-processadas"
        ).textContent = br(
            data.linhas_processadas
        );

        document.getElementById(
            "result-importados"
        ).textContent = br(
            data.registros_importados
        );

        document.getElementById(
            "result-duplicados"
        ).textContent = br(
            data.duplicados
        );

        document.getElementById(
            "result-conflitos"
        ).textContent = br(
            data.conflitos
        );

        document.getElementById(
            "result-erros"
        ).textContent = br(
            data.erros
        );

        document.getElementById(
            "result-lotes"
        ).textContent = br(
            data.lotes_processados
        );

        document.getElementById(
            "result-removidos"
        ).textContent = br(
            data.registros_removidos
        );

        resultBox.hidden =
            false;
    }


    function stopPolling() {
        if (pollingTimer) {
            window.clearTimeout(
                pollingTimer
            );

            pollingTimer = null;
        }
    }


    function showCancelButton(
        visible
    ) {
        cancelButton.hidden =
            !visible;
    }


    function finalState(data) {
        return ![
            "Aguardando",
            "Processando",
            "Cancelamento solicitado",
            "Removendo dados importados"
        ].includes(
            data.status
        );
    }


    async function poll(url) {
        try {
            const response =
                await fetch(
                    url,
                    {
                        headers: {
                            "Accept":
                                "application/json"
                        }
                    }
                );

            const payload =
                await response.json();

            if (
                !response.ok
                || !payload.ok
            ) {
                throw new Error(
                    payload.error
                    || "Não foi possível consultar o andamento."
                );
            }

            const data =
                payload.importacao;

            showResult(
                data
            );

            showCancelButton(
                Boolean(
                    data.cancelavel
                )
            );

            if (
                data.status
                === "Aguardando"
            ) {
                showStatus(
                    "Preparando importação...",
                    data.mensagem
                    || "Aguardando processamento."
                );
            }

            else if (
                data.status
                === "Processando"
            ) {
                showStatus(
                    "Importando registros para o banco de dados...",
                    data.mensagem
                    || (
                        "Processando lote "
                        + br(
                            data.lotes_processados
                        )
                        + "..."
                    )
                );
            }

            else if (
                data.status
                === "Cancelamento solicitado"
            ) {
                showCancelButton(
                    false
                );

                showStatus(
                    "Cancelamento solicitado.",
                    data.mensagem
                    || "Interrompendo a importação..."
                );
            }

            else if (
                data.status
                === "Removendo dados importados"
            ) {
                showCancelButton(
                    false
                );

                showStatus(
                    "Removendo dados importados...",
                    data.mensagem
                    || "Aguarde enquanto os registros são removidos."
                );
            }

            if (
                finalState(data)
            ) {
                stopPolling();

                setBusy(false);

                showCancelButton(
                    false
                );

                confirmation.hidden =
                    true;

                const erro = [
                    "Erro",
                    "Erro durante o cancelamento"
                ].includes(
                    data.status
                );

                statusBox.classList.toggle(
                    "is-error",
                    erro
                );

                let titulo =
                    "Importação finalizada.";

                if (
                    data.status
                    === "Cancelada"
                ) {
                    titulo =
                        "Importação cancelada.";
                }

                else if (erro) {
                    titulo =
                        "Não foi possível concluir a operação.";
                }

                showStatus(
                    titulo,
                    data.mensagem
                    || data.status
                );

                const spinner =
                    statusBox.querySelector(
                        ".loading-spinner"
                    );

                if (spinner) {
                    spinner.hidden =
                        true;
                }

                return;
            }

            pollingTimer =
                window.setTimeout(
                    () => poll(url),
                    1200
                );
        }

        catch (error) {
            stopPolling();

            setBusy(false);

            showCancelButton(
                false
            );

            showStatus(
                "Não foi possível acompanhar a importação.",
                error.message
                || "Tente atualizar a página."
            );

            statusBox.classList.add(
                "is-error"
            );
        }
    }


    cancelButton.addEventListener(
        "click",
        () => {
            if (!currentImportId) {
                return;
            }

            confirmation.hidden =
                false;
        }
    );


    continueButton.addEventListener(
        "click",
        () => {
            confirmation.hidden =
                true;
        }
    );


    confirmCancel.addEventListener(
        "click",
        async () => {
            if (
                !currentCancelUrl
                || confirmCancel.disabled
            ) {
                return;
            }

            confirmCancel.disabled =
                true;

            cancelButton.disabled =
                true;

            showCancelButton(
                false
            );

            confirmation.hidden =
                true;

            showStatus(
                "Cancelamento solicitado.",
                "Interrompendo a importação..."
            );

            try {
                const formData =
                    new FormData();

                formData.append(
                    "_csrf",
                    window.CSRF
                );

                const response =
                    await fetch(
                        currentCancelUrl,
                        {
                            method: "POST",
                            body: formData,
                            headers: {
                                "Accept":
                                    "application/json"
                            }
                        }
                    );

                const payload =
                    await response.json();

                if (
                    !response.ok
                    || !payload.ok
                ) {
                    throw new Error(
                        payload.error
                        || "Não foi possível solicitar o cancelamento."
                    );
                }

                if (
                    currentStatusUrl
                ) {
                    poll(
                        currentStatusUrl
                    );
                }
            }

            catch (error) {
                confirmCancel.disabled =
                    false;

                cancelButton.disabled =
                    false;

                showStatus(
                    "Não foi possível cancelar.",
                    error.message
                );

                statusBox.classList.add(
                    "is-error"
                );
            }
        }
    );


    input.addEventListener('change', () => {
        if (!running) updateFileState();
    });
    function isFileDrag(event) {
        return event.dataTransfer && Array.from(event.dataTransfer.types).includes('Files');
    }
    document.addEventListener('dragover', (event) => {
        if (isFileDrag(event)) event.preventDefault();
    });
    document.addEventListener('drop', (event) => {
        if (isFileDrag(event)) event.preventDefault();
        dropzone.classList.remove('is-dragging');
    });
    dropzone.addEventListener('dragover', (event) => {
        if (!isFileDrag(event)) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = running ? 'none' : 'copy';
        if (!running) dropzone.classList.add('is-dragging');
    });
    dropzone.addEventListener('dragleave', (event) => {
        if (!dropzone.contains(event.relatedTarget)) dropzone.classList.remove('is-dragging');
    });
    dropzone.addEventListener('drop', (event) => {
        event.preventDefault();
        dropzone.classList.remove('is-dragging');
        if (running) return;
        const files = event.dataTransfer.files;
        if (files.length !== 1) {
            input.value = '';
            updateFileState('Solte apenas um arquivo CSV por vez.');
            return;
        }
        try {
            const transfer = new DataTransfer();
            transfer.items.add(files[0]);
            input.files = transfer.files;
            if (!input.files[0] || input.files[0].name !== files[0].name) {
                throw new Error('File assignment unavailable');
            }
            updateFileState();
        } catch {
            input.value = '';
            updateFileState('Não foi possível selecionar por arraste. Clique na área para escolher o CSV.');
        }
    });
    input.addEventListener('focus', () => dropzone.classList.add('is-focused'));
    input.addEventListener('blur', () => dropzone.classList.remove('is-focused'));
    updateFileState();

    form.addEventListener(
        "submit",
        async (event) => {
            event.preventDefault();

            if (
                running
                || !validFile()
                || submit.disabled
            ) {
                return;
            }

            const formData =
                new FormData(
                    form
                );

            setBusy(true);

            resultBox.hidden =
                true;

            confirmation.hidden =
                true;

            confirmCancel.disabled =
                false;

            cancelButton.disabled =
                false;

            statusBox.classList.remove(
                "is-error"
            );

            const spinner =
                statusBox.querySelector(
                    ".loading-spinner"
                );

            if (spinner) {
                spinner.hidden =
                    false;
            }

            showStatus(
                "Verificando se o arquivo já foi importado...",
                "Validando arquivo e calculando sua identificação SHA-256."
            );

            try {
                const response =
                    await fetch(
                        "/importacao/iniciar",
                        {
                            method:
                                "POST",

                            body:
                                formData,

                            headers: {
                                "Accept":
                                    "application/json"
                            }
                        }
                    );

                const payload =
                    await response.json();

                if (
                    !response.ok
                    || !payload.ok
                ) {
                    throw new Error(
                        payload.error
                        || "Não foi possível iniciar a importação."
                    );
                }

                currentImportId =
                    payload.id;

                currentStatusUrl =
                    payload.status_url;

                currentCancelUrl =
                    payload.cancel_url;

                showCancelButton(
                    true
                );

                showStatus(
                    "Verificando registros existentes no banco de dados...",
                    payload.message
                    || "Importando apenas os registros novos..."
                );

                poll(
                    currentStatusUrl
                );
            }

            catch (error) {
                setBusy(false);

                showCancelButton(
                    false
                );

                showStatus(
                    "Importação não iniciada.",
                    error.message
                    || "Não foi possível concluir a solicitação."
                );

                statusBox.classList.add(
                    "is-error"
                );

                if (spinner) {
                    spinner.hidden =
                        true;
                }
            }
        }
    );
})();