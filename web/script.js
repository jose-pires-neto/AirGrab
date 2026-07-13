const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const statusZone = document.getElementById('statusZone');
const cancelBtn = document.getElementById('cancelBtn');

uploadZone.addEventListener('click', () => {
    fileInput.click();
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        uploadFile(e.target.files[0]);
    }
});

async function uploadFile(file) {
    // UI Loading state
    uploadZone.querySelector('p').innerText = "Enviando arquivo...";
    uploadZone.style.pointerEvents = 'none';

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: file,
            headers: {
                'X-File-Name': encodeURIComponent(file.name),
                'Content-Type': 'application/octet-stream'
            }
        });

        if (response.ok) {
            // Show Status Zone
            uploadZone.classList.add('hidden');
            statusZone.classList.remove('hidden');
        } else {
            alert("Erro ao enviar o arquivo. Tente novamente.");
            resetUI();
        }
    } catch (error) {
        console.error("Upload failed", error);
        alert("Falha de conexão com o PC.");
        resetUI();
    }
}

cancelBtn.addEventListener('click', async () => {
    try {
        await fetch('/cancel', { method: 'POST' });
    } catch(e) {}
    resetUI();
});

function resetUI() {
    fileInput.value = '';
    uploadZone.classList.remove('hidden');
    statusZone.classList.add('hidden');
    uploadZone.querySelector('p').innerText = "Toque para Selecionar Arquivo";
    uploadZone.style.pointerEvents = 'auto';
}
