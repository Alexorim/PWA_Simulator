/**
 * updater.js - Sistema de actualizaciones OTA para PWA Simulator
 * 
 * Flujo:
 * 1. Al iniciar la app, consulta version.json en Vercel
 * 2. Compara con la versión instalada del APK
 * 3. Si hay actualización, descarga el APK silenciosamente
 * 4. Muestra modal para que el usuario instale
 */

// URL del archivo de versiones en Vercel
// IMPORTANTE: Reemplazar con tu dominio real de Vercel si es diferente
const UPDATE_CHECK_URL = 'https://pwa-simulator-alexorim.vercel.app/version.json';

/**
 * Comparar dos cadenas de versión (ej: "0.1" vs "0.2")
 * Retorna: -1 si a < b, 0 si igual, 1 si a > b
 */
function compareVersions(a, b) {
    const partsA = a.split('.').map(Number);
    const partsB = b.split('.').map(Number);
    const maxLen = Math.max(partsA.length, partsB.length);

    for (let i = 0; i < maxLen; i++) {
        const numA = partsA[i] || 0;
        const numB = partsB[i] || 0;
        if (numA < numB) return -1;
        if (numA > numB) return 1;
    }
    return 0;
}

/**
 * Obtener la versión instalada actual usando @capacitor/app
 */
async function getInstalledVersion() {
    try {
        if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.App) {
            const info = await window.Capacitor.Plugins.App.getInfo();
            return info.version; // versionName del build.gradle (ej: "0.1")
        }
    } catch (e) {
        console.warn('[Updater] No se pudo obtener versión instalada:', e);
    }
    return null;
}

/**
 * Consultar version.json remoto
 */
async function fetchRemoteVersion() {
    try {
        // Añadir timestamp para evitar caché
        const url = UPDATE_CHECK_URL + '?t=' + Date.now();
        const response = await fetch(url, { cache: 'no-store' });
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return await response.json();
    } catch (e) {
        console.warn('[Updater] No se pudo consultar version.json:', e);
        return null;
    }
}

/**
 * Descargar APK usando @capacitor/filesystem y mostrando progreso
 */
async function downloadApk(apkUrl, onProgress) {
    const Filesystem = window.Capacitor.Plugins.Filesystem;

    // Descargar como blob usando fetch nativo
    const response = await fetch(apkUrl);
    if (!response.ok) throw new Error('Error descargando APK: HTTP ' + response.status);

    const contentLength = response.headers.get('content-length');
    const totalBytes = contentLength ? parseInt(contentLength, 10) : 0;
    let receivedBytes = 0;

    const reader = response.body.getReader();
    const chunks = [];

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
        receivedBytes += value.length;
        if (totalBytes > 0 && onProgress) {
            onProgress(Math.round((receivedBytes / totalBytes) * 100));
        }
    }

    // Concatenar chunks en un solo Uint8Array
    const fullArray = new Uint8Array(receivedBytes);
    let offset = 0;
    for (const chunk of chunks) {
        fullArray.set(chunk, offset);
        offset += chunk.length;
    }

    // Convertir a base64 para Capacitor Filesystem
    const base64Data = uint8ArrayToBase64(fullArray);

    // Guardar en el directorio de caché de la app
    const fileName = 'PWASimulator-update.apk';
    const result = await Filesystem.writeFile({
        path: fileName,
        data: base64Data,
        directory: 'CACHE'
    });

    return result.uri;
}

/**
 * Convertir Uint8Array a base64
 */
function uint8ArrayToBase64(uint8Array) {
    let binary = '';
    const len = uint8Array.byteLength;
    for (let i = 0; i < len; i++) {
        binary += String.fromCharCode(uint8Array[i]);
    }
    return btoa(binary);
}

/**
 * Abrir el APK descargado para instalación usando @capawesome-team/capacitor-file-opener
 */
async function openApkForInstall(fileUri) {
    try {
        const FileOpener = window.Capacitor.Plugins.FileOpener;
        await FileOpener.openFile({
            path: fileUri,
            mimeType: 'application/vnd.android.package-archive'
        });
    } catch (e) {
        console.error('[Updater] Error al abrir APK para instalación:', e);
        throw e;
    }
}

/**
 * Crear y mostrar el modal de actualización en el DOM
 */
function showUpdateModal(remoteInfo, onAccept, onDismiss) {
    // Eliminar modal previo si existe
    const existing = document.getElementById('updateModal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'updateModal';
    modal.innerHTML = `
        <div class="update-overlay">
            <div class="update-card">
                <div class="update-icon">🚀</div>
                <h2 class="update-title">¡Nueva versión disponible!</h2>
                <p class="update-version">v${remoteInfo.latest_version}</p>
                <p class="update-notes">${remoteInfo.release_notes || 'Mejoras y correcciones.'}</p>
                <div id="updateProgress" class="update-progress hidden">
                    <div class="progress-bar">
                        <div id="progressFill" class="progress-fill" style="width: 0%"></div>
                    </div>
                    <span id="progressText" class="progress-text">Descargando... 0%</span>
                </div>
                <div id="updateButtons" class="update-buttons">
                    <button id="updateAcceptBtn" class="btn btn-primary update-btn">
                        ⬇ Actualizar ahora
                    </button>
                    <button id="updateDismissBtn" class="btn-text update-dismiss">
                        Más tarde
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    document.getElementById('updateAcceptBtn').addEventListener('click', () => {
        onAccept();
    });

    document.getElementById('updateDismissBtn').addEventListener('click', () => {
        modal.remove();
        if (onDismiss) onDismiss();
    });
}

/**
 * Actualizar la barra de progreso en el modal
 */
function updateProgressUI(percent) {
    const progressSection = document.getElementById('updateProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const buttons = document.getElementById('updateButtons');

    if (progressSection) progressSection.classList.remove('hidden');
    if (buttons) buttons.classList.add('hidden');
    if (progressFill) progressFill.style.width = percent + '%';
    if (progressText) progressText.textContent = 'Descargando... ' + percent + '%';
}

/**
 * Mostrar estado de "instalando" en el modal
 */
function showInstallingUI() {
    const progressText = document.getElementById('progressText');
    if (progressText) progressText.textContent = '✅ Descarga completa. Abriendo instalador...';
}

/**
 * Mostrar error en el modal
 */
function showUpdateError(message) {
    const progressText = document.getElementById('progressText');
    const buttons = document.getElementById('updateButtons');

    if (progressText) {
        progressText.textContent = '❌ ' + message;
        progressText.style.color = '#EF4444';
    }
    if (buttons) buttons.classList.remove('hidden');
}

/**
 * Función principal: verificar actualizaciones al inicio
 */
async function checkForUpdates() {
    // Solo ejecutar en plataforma nativa (Android)
    if (!window.Capacitor || !window.Capacitor.isNativePlatform || !window.Capacitor.isNativePlatform()) {
        console.log('[Updater] No estamos en plataforma nativa, omitiendo verificación.');
        return;
    }

    console.log('[Updater] Verificando actualizaciones...');

    // 1. Obtener versión instalada
    const installedVersion = await getInstalledVersion();
    if (!installedVersion) {
        console.warn('[Updater] No se pudo determinar la versión instalada.');
        return;
    }
    console.log('[Updater] Versión instalada:', installedVersion);

    // 2. Consultar versión remota
    const remoteInfo = await fetchRemoteVersion();
    if (!remoteInfo || !remoteInfo.latest_version) {
        console.warn('[Updater] No se pudo obtener información remota.');
        return;
    }
    console.log('[Updater] Versión remota:', remoteInfo.latest_version);

    // 3. Comparar versiones
    if (compareVersions(installedVersion, remoteInfo.latest_version) >= 0) {
        console.log('[Updater] La app está actualizada.');
        return;
    }

    console.log('[Updater] ¡Actualización disponible! ' + installedVersion + ' → ' + remoteInfo.latest_version);

    // 4. Mostrar modal de actualización
    showUpdateModal(remoteInfo, async () => {
        // Usuario aceptó actualizar
        try {
            const fileUri = await downloadApk(remoteInfo.apk_url, (percent) => {
                updateProgressUI(percent);
            });

            showInstallingUI();

            // Pequeña pausa para que el usuario vea el mensaje
            await new Promise(resolve => setTimeout(resolve, 800));

            // Abrir instalador
            await openApkForInstall(fileUri);
        } catch (error) {
            console.error('[Updater] Error durante actualización:', error);
            showUpdateError('Error al descargar. Verifica tu conexión.');
        }
    });
}

// Exportar para uso externo
window.PWAUpdater = {
    checkForUpdates,
    compareVersions,
    getInstalledVersion,
    fetchRemoteVersion
};
