/**
 * Result Display Module
 * Maneja la visualización de resultados de búsqueda (empresas y trabajadores)
 *
 * FASE 3: Extraer funciones de display
 */

/**
 * Muestra los resultados de empresas en la tabla
 */
export function displayCompanyResults(companies) {
    const tabla = document.getElementById('resultadoTabla');
    const tbody = document.getElementById('tabla-cuerpo');
    const encabezadoEmpresa = document.getElementById('tabla-encabezado-empresa');
    const encabezadoTrabajador = document.getElementById('tabla-encabezado-trabajador');
    const sectionResultados = document.getElementById('section-resultados');

    // Show empresa header, hide trabajador header
    encabezadoEmpresa.classList.remove('d-none');
    encabezadoTrabajador.classList.add('d-none');

    tbody.innerHTML = '';

    companies.forEach(company => {
        const tr = document.createElement('tr');
        tr.className = 'data-row';
        tr.innerHTML = `
            <td data-label="Empresa">${company.name}</td>
            <td data-label="CIF / NIF">${company.tax_id || '--'}</td>
            <td data-label="Razón Social">${company.legal_name || '--'}</td>
            <td data-label="Creada">${company.created_at || '--'}</td>
            <td data-label="Acciones" >
                <div class="d-flex gap-2 acciones-movil">
                    <a href="/company-info/?company_id=${company.id}" class="btn btn-sm btn-outline-dark-custom">
                        Información
                    </a>
                    <a href="/staff/?company_id=${company.id}" class="btn btn-sm btn-outline-dark-custom">
                        Personal
                    </a>
                    <button type="button" class="btn btn-sm btn-outline-danger"
                            data-company-id="${company.id}"
                            data-company-name="${company.name}"
                            data-company-legal-name="${company.legal_name}"
                            data-bs-toggle="modal"
                            data-bs-target="#modalEliminarEmpresa">
                        <i class="bi bi-trash"></i> Eliminar
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });

    sectionResultados.classList.remove('d-none');
    document.getElementById('resultados-titulo').textContent = `Resultados: Empresas (${companies.length})`;
}

/**
 * Muestra los resultados de trabajadores en la tabla
 */
export function displayWorkerResults(workers) {
    const tabla = document.getElementById('resultadoTabla');
    const tbody = document.getElementById('tabla-cuerpo');
    const encabezadoEmpresa = document.getElementById('tabla-encabezado-empresa');
    const encabezadoTrabajador = document.getElementById('tabla-encabezado-trabajador');
    const sectionResultados = document.getElementById('section-resultados');

    // Show trabajador header, hide empresa header
    encabezadoEmpresa.classList.add('d-none');
    encabezadoTrabajador.classList.remove('d-none');

    tbody.innerHTML = '';

    workers.forEach(worker => {
        const tr = document.createElement('tr');
        tr.className = 'data-row';

        // Get status badge
        const statusBadge = worker.status === 'active'
            ? '<span class="badge bg-success">Activo</span>'
            : worker.status === 'suspended'
            ? '<span class="badge bg-danger">Suspendido</span>'
            : '<span class="badge bg-warning text-dark">Inactivo</span>';

        // Get companies badges
        const companies = worker.companies || [];
        const companiesBadges = companies.length > 0
            ? companies.map(c => `<span class="badge bg-secondary me-1">${c.name || c}</span>`).join('')
            : '<span class="badge bg-secondary">--</span>';

        // Determinar si el botón debe estar deshabilitado
        const isDisabledSelect = companies.length === 0;
        const selectButtonClass = isDisabledSelect ? 'btn-outline-secondary disabled' : 'btn-outline-success btn-select-worker';
        const selectButtonText = isDisabledSelect ? 'Sin empresas' : 'Seleccionar';
        const selectButtonDataAttrs = isDisabledSelect
            ? ''
            : `data-worker-id="${worker.id}" data-companies='${JSON.stringify(companies)}'`;
        const selectButtonDisabled = isDisabledSelect ? 'disabled' : '';

        tr.innerHTML = `
            <td data-label="Nombre">${worker.username} ${worker.surname}</td>
            <td data-label="Email">${worker.email}</td>
            <td data-label="DNI">${worker.dni || '--'}</td>
            <td data-label="Estado">${statusBadge}</td>
            <td data-label="Empresas">${companiesBadges}</td>
            <td data-label="Acciones">
                <div class="d-flex gap-2 acciones-movil">
                    <button type="button" class="btn btn-sm btn-outline-dark-custom"
                            data-bs-toggle="modal" data-bs-target="#modalEditarTrabajador"
                            data-id="${worker.id}"
                            data-nombre="${worker.username}"
                            data-apellidos="${worker.surname}"
                            data-email="${worker.email}"
                            data-dni="${worker.dni}"
                            data-estado="${worker.status}">
                        <i class="bi bi-pencil"></i> Editar
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-danger"
                            data-bs-toggle="modal" data-bs-target="#modalEliminarTrabajador"
                            data-id="${worker.id}"
                            data-companies='${JSON.stringify(companies)}'
                            data-nombrecompleto="${worker.username} ${worker.surname}">
                        <i class="bi bi-trash"></i>
                    </button>
                    <button type="button" class="btn btn-sm ${selectButtonClass}"
                            ${selectButtonDataAttrs} ${selectButtonDisabled}>
                        <i class="bi bi-check-lg"></i> ${selectButtonText}
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });

    sectionResultados.classList.remove('d-none');
    document.getElementById('resultados-titulo').textContent = `Resultados: Trabajadores (${workers.length})`;
}

/**
 * Limpia la tabla de resultados
 */
export function clearResults() {
    const sectionResultados = document.getElementById('section-resultados');
    if (sectionResultados) {
        sectionResultados.classList.add('d-none');
    }
}
