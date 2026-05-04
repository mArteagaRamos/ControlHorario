/**
 * Select Worker Module - Admin Dashboard
 * Maneja la selección de trabajadores delegados en la tabla de "Todos los Trabajadores"
 */

/**
 * Obtiene el CSRF token del documento
 */
function getCsrfToken() {
    return (
        document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
        window.AEPTIC_ADMIN?.CSRF_TOKEN ||
        document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
        ''
    );
}

/**
 * Inicializa el event listener para los botones "Seleccionar"
 */
export function initializeSelectWorker() {
    // Event listener para botones con clase "btn-select-worker"
    document.addEventListener('click', function(e) {
        // Buscar el botón más cercano con la clase btn-select-worker
        const btn = e.target.closest('.btn-select-worker');
        if (!btn) return;

        // Obtener datos del botón
        const workerId = btn.getAttribute('data-worker-id');
        const companiesJson = btn.getAttribute('data-companies');
        const selectUrl = btn.getAttribute('data-select-url');

        if (!workerId || !companiesJson) {
            alert('Error: Datos del trabajador incompletos');
            return;
        }

        if (!selectUrl) {
            alert('Error: URL de selección no configurada');
            return;
        }

        // Parsear JSON de empresas
        let companies = [];
        try {
            companies = JSON.parse(companiesJson);
        } catch (e) {
            alert('Error al procesar empresas');
            return;
        }

        // Llamar a la función de selección
        handleSelectWorker(workerId, companies, selectUrl);
    });
}

/**
 * Maneja la selección inteligente de empresa:
 * - 0 empresas: error
 * - 1 empresa: selecciona automáticamente
 * - N empresas: muestra modal para que elija
 */
async function handleSelectWorker(workerId, companies, selectUrl) {
    if (!companies || companies.length === 0) {
        alert('Este trabajador no pertenece a ninguna empresa.');
        return;
    }

    if (companies.length === 1) {
        // Auto-select the only company
        selectWorker(workerId, companies[0].id, selectUrl);
    } else {
        // Show modal for selection
        const companiesList = document.getElementById('companiesList');
        if (!companiesList) {
            alert('Error: Modal no encontrado en la página');
            return;
        }

        companiesList.innerHTML = '';

        companies.forEach(company => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
            button.innerHTML = `
                <div>
                    <strong>${company.name ? company.name.charAt(0).toUpperCase() + company.name.slice(1).toLowerCase() : 'N/A'}</strong>
                    <small class="text-muted d-block">${company.tax_id || '--'}</small>
                </div>
                <i class="bi bi-chevron-right text-secondary"></i>
            `;
            button.onclick = (e) => {
                e.preventDefault();
                const modal = bootstrap.Modal.getInstance(document.getElementById('modalSeleccionarEmpresa'));
                if (modal) modal.hide();
                selectWorker(workerId, company.id, selectUrl);
            };
            companiesList.appendChild(button);
        });

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('modalSeleccionarEmpresa'));
        modal.show();
    }
}

/**
 * Envía la selección de trabajador y empresa al backend
 */
async function selectWorker(workerId, companyId, selectUrl) {
    const formData = new FormData();
    formData.append('worker_id', workerId);
    formData.append('company_id', companyId);

    const csrfToken = getCsrfToken();

    try {
        const response = await fetch(selectUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken },
            body: formData
        });

        const data = await response.json();

        if (response.ok && data.success) {
            window.location.href = '/home/';
        } else {
            alert('Error: ' + (data.error || 'No se pudo seleccionar el trabajador.'));
        }
    } catch (err) {
        alert('Error al seleccionar trabajador: ' + err);
    }
}
