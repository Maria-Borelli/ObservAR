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
            || !input.files.length;

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


    input.addEventListener(
        "change",
        () => {
            const file =
                input.files[0];

            if (!file) {
                fileName.textContent =
                    "Nenhum arquivo selecionado.";

                submit.disabled =
                    true;

                return;
            }

            fileName.textContent =
                file.name;

            const valid =
                file.name
                .toLowerCase()
                .endsWith(
                    ".csv"
                );

            submit.disabled =
                !valid;

            if (!valid) {
                showStatus(
                    "Arquivo inválido.",
                    "Selecione um arquivo com extensão .csv."
                );
            }

            else {
                hideStatus();

                statusBox.classList.remove(
                    "is-error"
                );
            }
        }
    );


    form.addEventListener(
        "submit",
        async (event) => {
            event.preventDefault();

            if (
                running
                || !input.files.length
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