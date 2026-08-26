async function camera() {
    const video = document.getElementById("video");

    const stream = await navigator.mediaDevices.getUserMedia({
        video: {
            facingMode: "user"
        },
        audio: false
    });

    video.srcObject = stream;

    return video;
}


function shot(video) {
    const canvas = document.getElementById("canvas");

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const context = canvas.getContext("2d");

    context.drawImage(
        video,
        0,
        0,
        canvas.width,
        canvas.height
    );

    return canvas.toDataURL(
        "image/jpeg",
        0.86
    );
}


async function send(url, img) {
    const form = new FormData();

    form.append(
        "_csrf",
        window.CSRF
    );

    form.append(
        "image",
        img
    );

    const response = await fetch(
        url,
        {
            method: "POST",
            body: form
        }
    );

    const contentType =
        response.headers.get(
            "content-type"
        ) || "";

    if (
        contentType.includes(
            "application/json"
        )
    ) {
        const json =
            await response.json();

        if (!response.ok) {
            throw new Error(
                json.error ||
                "Falha biométrica."
            );
        }

        return json;
    }

    const text =
        await response.text();

    console.error(
        "Resposta não JSON:",
        response.status,
        text
    );

    throw new Error(
        "O servidor retornou erro HTTP "
        + response.status
        + ". Veja o terminal do Flask."
    );
}


function setLoading(visible, text) {
    const overlay = document.getElementById("loading-overlay");
    const loadingMessage = document.getElementById("loading-message");
    if (!overlay) return;
    if (loadingMessage && text) loadingMessage.textContent = text;
    overlay.hidden = !visible;
    overlay.setAttribute("aria-hidden", visible ? "false" : "true");
}

async function run(button, url) {
    const message = document.getElementById("bio-msg");
    const isLoginVerification = button.id === "verify";
    let stream = null;
    let redirecting = false;
    let slowTimer = null;

    try {
        button.disabled = true;
        message.textContent = "Solicitando acesso à câmera...";

        const video = await camera();
        stream = video.srcObject;

        await new Promise(resolve => setTimeout(resolve, 1000));

        message.textContent = "Capturando o rosto...";
        const image = shot(video);

        if (isLoginVerification) {
            setLoading(true, "Validando sua identidade...");
            slowTimer = setTimeout(() => {
                setLoading(
                    true,
                    "A validação está levando mais tempo que o esperado. Aguarde."
                );
            }, 8000);
        } else {
            message.textContent = "Processando biometria...";
        }

        const result = await send(url, image);
        if (slowTimer) clearTimeout(slowTimer);

        if (result.redirect) {
            redirecting = true;
            if (isLoginVerification) {
                setLoading(true, "Acesso autorizado. Preparando o sistema...");
            } else {
                message.textContent = "Biometria processada com sucesso.";
            }
            window.location.assign(result.redirect);
            return;
        }

        message.textContent = "Biometria processada com sucesso.";
        setLoading(false);

    } catch (error) {
        if (slowTimer) clearTimeout(slowTimer);
        setLoading(false);

        if (error.name === "NotAllowedError") {
            message.textContent = "Acesso à câmera negado.";
        } else if (error instanceof TypeError) {
            message.textContent = "Não foi possível concluir a autenticação. Verifique a conexão e tente novamente.";
        } else {
            message.textContent = error.message || "Não foi possível confirmar sua identidade.";
        }
    } finally {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
        if (!redirecting) button.disabled = false;
    }
}

//Login e verificação biometrica 

const verify =
    document.getElementById(
        "verify"
    );

if (verify) {
    verify.onclick = () =>
        run(
            verify,
            "/api/biometria/verificar"
        );
}

//Cadastro de biometria pelo próprio usuário

const enroll =
    document.getElementById(
        "enroll"
    );

if (enroll) {
    enroll.onclick = () =>
        run(
            enroll,
            enroll.dataset.url
        );
}

//Primeiro cadastro para o admin

const setupEnroll =
    document.getElementById(
        "setup-enroll"
    );

if (setupEnroll) {
    setupEnroll.onclick = () =>
        run(
            setupEnroll,
            "/api/setup-biometria/cadastrar"
        );
}