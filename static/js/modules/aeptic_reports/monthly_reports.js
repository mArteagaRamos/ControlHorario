// static/aeptic_reports/monthly_reports.js

class MonthlyReportsManager {
    constructor() {
        this.currentMonth = new Date();
        this.currentMonth.setDate(1);
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.updateMonthButtons();
        this.loadReport(this.currentMonth);
    }

    setupEventListeners() {
        // Cambiar entre meses
        document.getElementById('prev-month-btn')?.addEventListener('click', () => {
            this.currentMonth = new Date(
                this.currentMonth.getFullYear(),
                this.currentMonth.getMonth() - 1,
                1
            );
            this.updateMonthButtons();
            this.loadReport(this.currentMonth);
        });

        document.getElementById('current-month-btn')?.addEventListener('click', () => {
            const today = new Date();
            this.currentMonth = new Date(today.getFullYear(), today.getMonth(), 1);
            this.updateMonthButtons();
            this.loadReport(this.currentMonth);
        });

        // Descargar Excel
        document.getElementById('download-xlsx-btn')?.addEventListener('click', () => {
            this.downloadReport('xlsx');
        });

        // Descargar CSV
        document.getElementById('download-csv-btn')?.addEventListener('click', () => {
            this.downloadReport('csv');
        });

        // Subir documentos
        document.getElementById('prev-month-file')?.addEventListener('change', (e) => {
            this.uploadReport(e, this.getPreviousMonth());
        });

        document.getElementById('current-month-file')?.addEventListener('change', (e) => {
            this.uploadReport(e, this.currentMonth);
        });
    }

    updateMonthButtons() {
        const prevBtn = document.getElementById('prev-month-btn');
        const currBtn = document.getElementById('current-month-btn');
        const prevGroup = document.getElementById('prev-month-group');
        const currGroup = document.getElementById('current-month-group');

        // Obtener los meses del HTML (data-month)
        const prevBtnMonth = prevBtn?.dataset.month;  // "2026-04-01"
        const currBtnMonth = currBtn?.dataset.month;  // "2026-05-01"

        const currMonthStr = this.dateToString(this.currentMonth);

        // Determinar cuál está activo comparando con el mes seleccionado actualmente
        const isPrevMonthActive = currMonthStr === prevBtnMonth;
        const isCurrMonthActive = currMonthStr === currBtnMonth;

        prevGroup?.classList.toggle('active', isPrevMonthActive);
        currGroup?.classList.toggle('active', isCurrMonthActive);

        // Actualizar los file inputs con el mes activo
        const prevFileInput = document.getElementById('prev-month-file');
        const currFileInput = document.getElementById('current-month-file');
        if (prevFileInput) prevFileInput.dataset.month = prevBtnMonth;
        if (currFileInput) currFileInput.dataset.month = currBtnMonth;
    }

    loadReport(date) {
        const monthStr = this.dateToString(date);
        fetch(`/monthly-reports/data/?month=${monthStr}`)
            .then(r => r.json())
            .then(data => {
                if (data.status === 'success') {
                    this.populateTable(data.data);
                } else {
                    this.showError(data.message || 'Error cargando reporte');
                }
            })
            .catch(err => {
                console.error('Error:', err);
                this.showError('Error de red');
            });
    }

    downloadReport(format) {
        const monthStr = this.dateToString(this.currentMonth);
        const btn = format === 'xlsx'
            ? document.getElementById('download-xlsx-btn')
            : document.getElementById('download-csv-btn');

        if (btn) {
            btn.disabled = true;
            const originalText = btn.innerHTML;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Descargando...';
        }

        setTimeout(() => {
            window.location.href = `/monthly-reports/download/?month=${monthStr}&format=${format}`;

            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        }, 500);
    }

    uploadReport(event, date) {
        const file = event.target.files[0];
        if (!file) return;

        const label = event.target.nextElementSibling;
        if (label) {
            label.classList.add('loading');
            label.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Subiendo...';
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('month', this.dateToString(date));

        fetch('/monthly-reports/upload/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            body: formData
        })
        .then(r => r.json())
        .then(data => {
            if (label) {
                label.classList.remove('loading');
                label.innerHTML = '<i class="bi bi-cloud-upload"></i> Subir firmado';
            }

            if (data.status === 'success') {
                this.showSuccess('Documento subido correctamente');
                this.loadReport(date);
                // Reset file input
                event.target.value = '';
            } else {
                this.showError(data.message || 'Error al subir');
            }
        })
        .catch(err => {
            if (label) {
                label.classList.remove('loading');
                label.innerHTML = '<i class="bi bi-cloud-upload"></i> Subir firmado';
            }
            console.error('Error:', err);
            this.showError('Error de red');
        });
    }

    populateTable(reportData) {
        const table = document.getElementById('report-table');
        if (!table) return;

        const thead = table.querySelector('thead');
        const tbody = table.querySelector('tbody');

        // Limpiar tabla
        if (thead) thead.innerHTML = '';
        if (tbody) tbody.innerHTML = '';

        // Headers
        const headers = [
            'Fecha', 'Día Semana', 'Entrada', 'Salida', 'Ausencia',
            'Vacaciones', 'Baja', 'Festivo', 'Ordinarias', 'Extras', 'Firma'
        ];

        if (thead) {
            const headerRow = document.createElement('tr');
            headers.forEach(h => {
                const th = document.createElement('th');
                th.textContent = h;
                th.style.textAlign = 'center';
                headerRow.appendChild(th);
            });
            thead.appendChild(headerRow);
        }

        // Body - Poblar con datos del mes
        if (!reportData || reportData.length === 0) {
            if (tbody) {
                const row = document.createElement('tr');
                row.innerHTML = `<td colspan="${headers.length}" class="text-center text-muted py-4">
                    No hay datos disponibles para este mes.
                </td>`;
                tbody.appendChild(row);
            }
            return;
        }

        // Mostrar filas de datos
        if (tbody) {
            reportData.forEach(dayData => {
                const row = document.createElement('tr');

                // Aplicar estilos para fin de semana
                if (dayData.es_fin_semana) {
                    row.classList.add('weekend');
                }

                row.innerHTML = `
                    <td>${dayData.fecha}</td>
                    <td>${dayData.dia_semana}</td>
                    <td>${dayData.entrada}</td>
                    <td>${dayData.salida}</td>
                    <td>${dayData.ausencia}</td>
                    <td>${dayData.vacaciones}</td>
                    <td>${dayData.baja}</td>
                    <td>${dayData.festivo}</td>
                    <td>${dayData.ordinarias}</td>
                    <td>${dayData.extras}</td>
                    <td>${dayData.firma}</td>
                `;
                tbody.appendChild(row);
            });
        }
    }

    getStatusBadge(status) {
        const statusMap = {
            'draft': '<span class="badge bg-secondary">Borrador</span>',
            'generated': '<span class="badge bg-info">Generado</span>',
            'signed': '<span class="badge bg-success">Firmado</span>',
            'archived': '<span class="badge bg-dark">Archivado</span>'
        };
        return statusMap[status] || `<span class="badge bg-light text-dark">${status}</span>`;
    }

    getPreviousMonth() {
        const prev = new Date(this.currentMonth);
        prev.setMonth(prev.getMonth() - 1);
        return prev;
    }

    dateToString(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    getMonthName(date) {
        const months = [
            'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
        ];
        return months[date.getMonth()];
    }

    showError(msg) {
        const statusDiv = document.getElementById('status-message');
        if (statusDiv) {
            statusDiv.className = 'alert alert-danger';
            statusDiv.textContent = msg;
            statusDiv.style.display = 'block';
            setTimeout(() => {
                statusDiv.style.display = 'none';
            }, 5000);
        }
    }

    showSuccess(msg) {
        const statusDiv = document.getElementById('status-message');
        if (statusDiv) {
            statusDiv.className = 'alert alert-success';
            statusDiv.textContent = msg;
            statusDiv.style.display = 'block';
            setTimeout(() => {
                statusDiv.style.display = 'none';
            }, 5000);
        }
    }
}

// Inicializar cuando el DOM está listo
document.addEventListener('DOMContentLoaded', () => {
    new MonthlyReportsManager();
});
